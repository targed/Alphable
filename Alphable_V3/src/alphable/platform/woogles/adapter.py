"""
Woogles.io Platform Adapter.
Implements AbstractPlatformAdapter using Playwright with persistent user profiles.
Handles automated matchmaking against bots (HastyBot, BestBot, etc.),
DOM board/rack parsing, coordinate conversion, and keyboard/mouse move execution.
"""

import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from playwright.sync_api import sync_playwright, Page, BrowserContext, Playwright

from alphable.platform.base import (
    AbstractPlatformAdapter,
    OnlineGameState,
    PlatformGameConfig,
    PlatformMove,
)
from alphable.platform.woogles.selectors import (
    WOOGLES_BASE_URL,
    SELECTORS,
    BOARD_ROWS,
    BOARD_COLS,
    to_woogles_coords,
    from_woogles_coords,
    format_move_description,
)


class WooglesAdapter(AbstractPlatformAdapter):
    """
    Playwright-based adapter for playing Scrabble on Woogles.io.
    """

    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.user_data_dir: Optional[str] = None
        self.current_game_url: Optional[str] = None
        self.my_username: str = "Alphable"
        self.opponent_username: str = "Opponent"
        self._last_headless: bool = False
        self._last_user_data_dir: Optional[str] = None

    def start(self, headless: bool = False, user_data_dir: Optional[str] = None) -> None:
        """
        Launch Chromium browser with a persistent user profile to retain logins.
        """
        if user_data_dir is None:
            user_data_dir = os.path.expanduser("~/.alphable/woogles_profile")
        self.user_data_dir = user_data_dir
        self._last_headless = headless
        self._last_user_data_dir = user_data_dir
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)

        self.playwright = sync_playwright().start()

        # Launch persistent context
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            viewport={"width": 1280, "height": 850},
            accept_downloads=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ]
        )

        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = self.context.new_page()

        self.page.set_default_timeout(15000)
        self.page.goto(WOOGLES_BASE_URL, wait_until="domcontentloaded")
        time.sleep(1.0)

    def is_browser_alive(self) -> bool:
        """Check if browser, context, and page are alive and responsive."""
        if not self.page:
            return False
        try:
            if self.page.is_closed():
                return False
            self.page.evaluate("() => true")
            return True
        except Exception:
            return False

    def ensure_browser_active(self, headless: Optional[bool] = None, user_data_dir: Optional[str] = None) -> None:
        """
        Ensures the browser and active page are open and healthy.
        If closed or crashed, cleanly relaunches and re-establishes session.
        """
        if self.is_browser_alive():
            return

        print("Browser or page is closed/unresponsive. Re-establishing browser session...")
        try:
            self.close()
        except Exception:
            pass

        hl = headless if headless is not None else getattr(self, "_last_headless", False)
        udd = user_data_dir if user_data_dir is not None else getattr(self, "_last_user_data_dir", None)
        self.start(headless=hl, user_data_dir=udd)
        self.ensure_logged_in()

    def ensure_logged_in(self) -> str:
        """
        Verify that a user profile or guest account is active on Woogles.
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")

        # Woogles shows the user's handle in the top navigation
        # Let's extract whatever username or guest ID is active
        try:
            # Look for top right user handle
            nav_user = self.page.locator("header, nav").locator("text=/[A-Z0-9_]{3,}/").first
            if nav_user.is_visible(timeout=3000):
                text = nav_user.inner_text().strip().split()[0]
                if text and text not in ("PLAY", "STUDY", "DONATE", "MORE", "LOGIN", "SIGN UP"):
                    self.my_username = text
                    return text
        except Exception:
            pass

        self.my_username = "AlphableUser"
        return self.my_username

    def reset_to_lobby(self) -> None:
        """Navigates back to the Woogles home lobby, clearing any completed game state."""
        self.current_game_url = None
        if not self.is_browser_alive():
            self.ensure_browser_active()
            return
        try:
            print("Resetting navigation back to Woogles lobby...")
            self.page.goto(WOOGLES_BASE_URL, wait_until="domcontentloaded")
            time.sleep(1.0)
        except Exception:
            pass

    def create_game(self, config: PlatformGameConfig) -> str:
        """
        Automates creating a match against a computer bot or player.
        """
        self.ensure_browser_active()
        if not self.page:
            raise RuntimeError("Browser not started.")

        # 1. Check if already inside an active ongoing game (only in takeover mode)
        if config.match_mode == "takeover":
            try:
                if "/game/" in self.page.url and "?turn=" not in self.page.url:
                    time.sleep(0.5)
                    if self.page.locator("#board-spaces").count() > 0 and self.page.locator("#rack").count() > 0:
                        if not self.is_game_over():
                            print(f"✓ Detected ongoing match at {self.page.url}. Resuming play...")
                            self.current_game_url = self.page.url
                            self.opponent_username = config.bot_name or "Opponent"
                            return self.current_game_url
            except Exception:
                pass

        # If currently on a completed game or replay URL, navigate to lobby to create the new match
        if "/game/" in self.page.url and not config.game_url:
            self.reset_to_lobby()

        # Direct Game URL attachment
        if config.game_url:
            print(f"Attaching directly to game URL: {config.game_url}...")
            self.page.goto(config.game_url, wait_until="domcontentloaded")
            self._wait_for_game_ready()
            self.current_game_url = self.page.url
            print(f"✓ Game successfully loaded: {self.current_game_url}")
            return self.current_game_url

        # Human Takeover Mode
        if config.match_mode == "takeover" or (config.opponent_type == "human" and config.match_mode != "auto-seek"):
            self.page.goto(f"{WOOGLES_BASE_URL}/", wait_until="domcontentloaded")
            print("\n" + "=" * 65)
            print("🕹️  ALPHABLE INTERACTIVE TAKEOVER MODE ACTIVE")
            print("Please challenge a friend or join a match with a human player in the browser.")
            print("Alphable is monitoring the session and will take over automatically once the game starts...")
            print("=" * 65 + "\n")
            self.page.wait_for_url("**/game/**", timeout=300000)
            self._wait_for_game_ready()
            self.current_game_url = self.page.url
            print(f"✓ Match detected and loaded: {self.current_game_url}")
            return self.current_game_url

        # Human Auto-Seek Mode (Public lobby challenge)
        if config.match_mode == "auto-seek":
            self.page.goto(f"{WOOGLES_BASE_URL}/", wait_until="domcontentloaded")
            time.sleep(1.0)
            print(f"Seeking public match with a human player in the Woogles lobby ({config.dictionary}, {config.game_mode})...")
            btn_create_game = self.page.locator(".ant-card-actions li:has-text('Create a game')").first
            btn_create_game.wait_for(state="visible", timeout=10000)
            btn_create_game.click()
            time.sleep(0.5)

            modal = self.page.locator(".ant-modal-content, [role='dialog']").first
            modal.wait_for(state="visible", timeout=10000)

            # Configure dictionary
            try:
                dict_dropdown = modal.locator("select[name='dictionary'], [role='combobox']").first
                if dict_dropdown.is_visible(timeout=1000):
                    dict_dropdown.select_option(label=re.compile(config.dictionary, re.IGNORECASE))
            except Exception:
                pass

            # Configure game mode
            try:
                if config.game_mode.lower() == "correspondence":
                    modal.locator("button:has-text('Correspondence')").first.click()
                else:
                    modal.locator("button:has-text('Real-time')").first.click()
            except Exception:
                pass

            # Click Create game in modal
            modal.locator("button:has-text('Create game')").first.click()
            print("✓ Open seek posted to lobby! Waiting for a human opponent to accept...")
            self.page.wait_for_url("**/game/**", timeout=180000)
            self._wait_for_game_ready()
            self.current_game_url = self.page.url
            print(f"✓ Match started: {self.current_game_url}")
            return self.current_game_url

        # Bot Mode
        # 2. Navigate to lobby to create fresh game or resume
        self.page.goto(f"{WOOGLES_BASE_URL}/", wait_until="domcontentloaded")
        time.sleep(1.0)

        # Check for "Resume your game" banner in lobby
        resume_btn = self.page.locator("text=/Resume your game/i").first
        try:
            if resume_btn.is_visible():
                banner_txt = resume_btn.inner_text().strip().replace("\n", " ")
                print(f"✓ Found ongoing match banner ({banner_txt}). Resuming...")
                resume_btn.click()
                self.page.wait_for_url("**/game/**", timeout=10000)
                self._wait_for_game_ready()
                self.current_game_url = self.page.url
                self.opponent_username = config.bot_name or "Opponent"
                return self.current_game_url
        except Exception:
            pass

        print(f"Creating Woogles match vs {config.bot_name} ({config.dictionary}, {config.game_mode})...")

        # 3. Click "Play a computer" button
        btn_play_comp = self.page.locator(".bot").first
        try:
            btn_play_comp.wait_for(state="visible", timeout=10000)
        except Exception:
            btn_play_comp = self.page.locator("text=Play a computer").first
            btn_play_comp.wait_for(state="visible", timeout=10000)

        btn_play_comp.click()
        time.sleep(0.5)

        # 4. Configure bot modal
        modal = self.page.locator(".ant-modal-content, .seek-modal, [role='dialog']").first
        modal.wait_for(state="visible", timeout=10000)

        # 4a. Select bot level if requested
        if config.bot_name:
            bot_selector = self.page.locator(".bot-selector, #seekForm_botType").first
            try:
                bot_selector.wait_for(state="visible", timeout=3000)
                current_text = bot_selector.inner_text()
                if config.bot_name.lower() not in current_text.lower():
                    bot_selector.click()
                    time.sleep(0.3)
                    # Click target bot option in dropdown
                    target_option = self.page.locator(
                        f".ant-select-dropdown .ant-select-item-option:has-text('{config.bot_name}')"
                    ).first
                    if target_option.is_visible(timeout=2000):
                        target_option.click()
                        time.sleep(0.3)
                    else:
                        # Fallback case-insensitive match
                        opt = self.page.locator(".ant-select-dropdown .ant-select-item-option").filter(
                            has_text=re.compile(config.bot_name, re.IGNORECASE)
                        ).first
                        if opt.is_visible(timeout=1000):
                            opt.click()
                            time.sleep(0.3)
            except Exception as e:
                print(f"Warning: Failed to select bot '{config.bot_name}': {e}")
            self.opponent_username = config.bot_name

        # 4b. Select dictionary if dropdown available
        try:
            dict_dropdown = self.page.locator("select[name='dictionary'], [role='combobox']").first
            if dict_dropdown.is_visible(timeout=1000):
                dict_dropdown.select_option(label=re.compile(config.dictionary, re.IGNORECASE))
        except Exception:
            pass

        # 4c. Select game mode (Real-time vs Correspondence)
        try:
            if config.game_mode.lower() == "correspondence":
                self.page.locator("button:has-text('Correspondence')").first.click()
            else:
                self.page.locator("button:has-text('Real-time')").first.click()
            time.sleep(0.3)
        except Exception:
            pass

        # 5. Click "Create game"
        btn_create = self.page.locator(".ant-modal-content button:has-text('Create game'), button:has-text('Create game')").first
        btn_create.click()

        # 6. Wait for game board to render and session to hydrate
        print("Waiting for game board to load...")
        self.page.wait_for_url("**/game/**", timeout=20000)
        self._wait_for_game_ready()

        self.current_game_url = self.page.url
        print(f"✓ Game successfully loaded: {self.current_game_url}")
        return self.current_game_url

    def _wait_for_game_ready(self, timeout: float = 20.0) -> None:
        """Waits for game board, rack, action buttons, or on-turn indicator to hydrate."""
        self.page.wait_for_selector("#board-spaces", timeout=int(timeout * 1000))
        try:
            self.page.wait_for_function("""() => {
                const rackTiles = document.querySelectorAll("#rack .tile, .rack .tile, .rack-container .tile");
                const hasActionBtns = Array.from(document.querySelectorAll(".game-controls button, button")).some(
                    b => b.innerText && (b.innerText.includes("Play") || b.innerText.includes("Pass") || b.innerText.includes("Exchange"))
                );
                const hasOnTurn = document.querySelector(".player-card.on-turn");
                return (rackTiles.length > 0) || hasActionBtns || !!hasOnTurn;
            }""", timeout=int(timeout * 1000))
        except Exception:
            pass
        time.sleep(0.5)

    def get_game_state(self) -> OnlineGameState:
        """
        Scrape active board grid, rack tiles, turn indicator, bag count, and scores from DOM.
        """
        if not self.page:
            raise RuntimeError("Browser not started.")

        # Initialize empty 15x15 board
        board = [["." for _ in range(BOARD_COLS)] for _ in range(BOARD_ROWS)]

        # 1. Parse Board Squares via .board-spaces-container .tiles (225 cells in row-major order)
        board_data = self.page.evaluate("""() => {
            const matrix = Array(15).fill(null).map(() => Array(15).fill("."));
            const tilesContainer = document.querySelector(".board-spaces-container .tiles");
            if (!tilesContainer) return matrix;
            const children = Array.from(tilesContainer.children);
            children.forEach((c, idx) => {
                const letterSpan = c.querySelector(".rune span, .rune");
                if (letterSpan) {
                    const txt = letterSpan.innerText.trim();
                    if (txt && txt.length > 0) {
                        const r = Math.floor(idx / 15);
                        const col = idx % 15;
                        if (r >= 0 && r < 15 && col >= 0 && col < 15) {
                            const pts = c.querySelector(".point-value")?.innerText.trim();
                            const isBlank = !pts || pts === "0" || c.querySelector(".tile")?.className.includes("blank");
                            matrix[r][col] = isBlank ? txt[0].toLowerCase() : txt[0].toUpperCase();
                        }
                    }
                }
            });
            return matrix;
        }""")
        if board_data:
            board = board_data

        # 2. Parse Rack Tiles via #rack .tile (excluding dummy/hidden 128 tiles and validating blanks)
        rack = self.page.evaluate("""() => {
            const tiles = [];
            const rackTiles = document.querySelectorAll("#rack .tile, .rack .tile, .rack-container .tile");
            rackTiles.forEach(t => {
                // If tile has explicit data-letter attribute
                const dlAttr = t.getAttribute("data-letter");
                if (dlAttr !== null && dlAttr !== undefined) {
                    const dl = parseInt(dlAttr, 10);
                    // 128 is hidden / empty rack slot placeholder in Woogles
                    if (dl === 128 || t.style.visibility === "hidden") {
                        return;
                    }
                    // 0 is blank tile
                    if (dl === 0) {
                        tiles.push("?");
                        return;
                    }
                    // 1 to 26 are A to Z
                    if (dl >= 1 && dl <= 26) {
                        tiles.push(String.fromCharCode(64 + dl));
                        return;
                    }
                }

                // Fallback to DOM runes and point-values
                const rune = t.querySelector(".rune span, .rune");
                const txt = rune ? rune.innerText.trim() : "";
                const isBlankClass = t.className.includes("blank");

                if (txt.length === 1 && txt.toUpperCase() >= "A" && txt.toUpperCase() <= "Z") {
                    tiles.push(txt.toUpperCase());
                } else if (isBlankClass) {
                    tiles.push("?");
                }
            });
            return tiles;
        }""")

        # Scrabble rule: English Scrabble has at most 2 blanks in the entire bag.
        # If rack has > 2 blanks or > 7 tiles, it indicates unhydrated / phantom DOM state.
        if rack and (rack.count("?") > 2 or len(rack) > 7):
            rack = []

        # 3. Parse Metadata, Scores, Bag, Turn, and Status via in-page JavaScript
        meta = self.page.evaluate("""(oppNameParam) => {
            // Pool / Bag
            const pool = document.querySelector(".pool");
            let bagRemaining = 0;
            if (pool) {
                const txt = pool.innerText || pool.textContent || "";
                const m = txt.match(/(\\d+)\\s+tiles in bag/i);
                if (m) bagRemaining = parseInt(m[1], 10);
            }

            // Player Cards & Scores (fallback to allCards if hidden by Chat/Notepad tab)
            const allCards = Array.from(document.querySelectorAll(".player-card"));
            const visibleCards = allCards.filter(c => 
                c.offsetWidth > 0 && c.offsetHeight > 0
            );
            const cards = visibleCards.length >= 2 ? visibleCards : allCards;

            let myName = "Alphable";
            let oppName = oppNameParam || "Opponent";
            let myScore = 0;
            let oppScore = 0;
            let myOnTurn = false;
            let oppOnTurn = false;

            cards.forEach(c => {
                const name = c.querySelector(".player-name")?.innerText.trim() || "";
                const scoreText = c.querySelector(".score")?.innerText.trim() || "0";
                const score = parseInt(scoreText.replace(/[^0-9-]/g, "") || "0", 10);
                const onTurn = c.classList.contains("on-turn");

                if (name.toLowerCase() === (oppNameParam || "").toLowerCase() || name.toLowerCase().includes("bot")) {
                    oppName = name;
                    oppScore = score;
                    oppOnTurn = onTurn;
                } else {
                    myName = name;
                    myScore = score;
                    myOnTurn = onTurn;
                }
            });

            // End message / Game Over detection
            let isGameOver = false;
            let winner = null;

            const endMsgEl = document.querySelector(".end-message");
            if (endMsgEl && endMsgEl.offsetWidth > 0 && endMsgEl.offsetHeight > 0) {
                const txt = endMsgEl.innerText.trim();
                // Ignore transient "Waiting for game to start..." or connecting messages
                if (!txt.toLowerCase().includes("waiting for game to start") && 
                    /wins|won|final score|draw|resigned|forfeited|timed out|game over/i.test(txt)) {
                    isGameOver = true;
                    const mWin = txt.match(/([A-Za-z0-9_]+)\\s+wins/i);
                    if (mWin) {
                        winner = mWin[1];
                    } else if (/draw/i.test(txt)) {
                        winner = "Draw";
                    } else {
                        winner = myScore > oppScore ? myName : (oppScore > myScore ? oppName : "Draw");
                    }
                }
            }

            if (!isGameOver) {
                const rackTiles = document.querySelectorAll("#rack .tile, .rack .tile, .rack-container .tile");
                const hasActionBtns = Array.from(document.querySelectorAll(".game-controls button, button")).some(
                    b => b.offsetWidth > 0 && /^(play|pass|exchange)$/i.test((b.innerText || "").trim())
                );
                
                // Active gameplay cannot be game over if player holds rack tiles or action buttons are visible
                if (rackTiles.length === 0 && !hasActionBtns) {
                    const controls = document.querySelector(".game-controls");
                    if (controls && controls.offsetWidth > 0) {
                        const cText = controls.innerText || "";
                        if (cText.includes("Analyze") && (cText.includes("Export") || cText.includes("Rematch") || cText.includes("Exit"))) {
                            isGameOver = true;
                            winner = myScore > oppScore ? myName : (oppScore > myScore ? oppName : "Draw");
                        }
                    }
                }
            }

            // If game is over, turn is not active
            const isMyTurn = myOnTurn && !oppOnTurn && !isGameOver;

            return {
                myName,
                oppName,
                myScore,
                oppScore,
                isMyTurn,
                bagRemaining,
                isGameOver,
                winner
            };
        }""", self.opponent_username)

        self.my_username = meta["myName"]
        if meta["oppName"]:
            self.opponent_username = meta["oppName"]

        return OnlineGameState(
            board=board,
            rack=rack,
            my_score=meta["myScore"],
            opponent_score=meta["oppScore"],
            my_name=self.my_username,
            opponent_name=self.opponent_username,
            is_my_turn=meta["isMyTurn"],
            bag_remaining=meta["bagRemaining"],
            turn_number=1,
            is_game_over=meta["isGameOver"],
            winner=meta["winner"],
            raw_metadata={"url": self.current_game_url}
        )

    def recall_tiles(self) -> None:
        """
        Recalls uncommitted tiles from the board back to the rack and resets cursor.
        On Woogles:
        1. Clicks the dedicated Reset Rack button (.ant-btn-circle with ArrowDown / title="Reset Rack ↓").
        2. Presses "ArrowDown" key focused on #board-container.
        3. Clears board square selection / placement arrow.
        4. Presses Escape to close any lingering dialogs / overlays.
        """
        if not self.page:
            return

        try:
            # 1. Click dedicated Reset Rack button if present
            recall_btn = self.page.locator(
                "button[title*='Reset Rack'], .rack-container button.ant-btn-circle, button:has(.anticon-arrow-down), button:has([data-icon='arrow-down'])"
            ).first
            if recall_btn.is_visible(timeout=500):
                recall_btn.click(force=True)
                time.sleep(0.15)
        except Exception:
            pass

        try:
            # 2. Focus board container and press ArrowDown (Woogles shortcut for recallTiles())
            board = self.page.locator("#board-container")
            if board.is_visible():
                board.focus()
            self.page.keyboard.press("ArrowDown")
            time.sleep(0.15)
        except Exception:
            pass

        try:
            # 3. Clear board square selection / direction arrow
            self.page.evaluate("""() => {
                const selected = document.querySelectorAll("#board-spaces > div.selected");
                selected.forEach(s => s.classList.remove("selected"));
            }""")
            # Also send Escape to dismiss any popovers
            self.page.keyboard.press("Escape")
            time.sleep(0.1)
        except Exception:
            pass

    def wait_for_my_turn(self, poll_interval: float = 0.5, timeout: float = 300.0) -> OnlineGameState:
        """
        Polls until it is Alphable's turn to play.
        """
        # Recall any lingering uncommitted tiles before polling
        if self.page:
            try:
                uncommitted = self.page.evaluate("""() => {
                    return document.querySelectorAll(
                        ".board-spaces-container .tiles .tile.tentative, .board-spaces-container .tiles .tentative, .board-spaces-container [class*='tentative']"
                    ).length;
                }""")
                if uncommitted > 0:
                    self.recall_tiles()
            except Exception:
                pass

        start_time = time.time()
        while time.time() - start_time < timeout:
            state = self.get_game_state()
            if state.is_game_over:
                return state
            if state.bag_remaining == 0 and len(state.rack) == 0:
                state.is_game_over = True
                return state

            # Rack must be valid: non-empty and at most 2 blanks
            rack_valid = len(state.rack) > 0 and state.rack.count("?") <= 2
            if state.is_my_turn:
                if rack_valid:
                    return state
                else:
                    # Unhydrated or tiles in limbo - recall and retry
                    self.recall_tiles()

            time.sleep(poll_interval)

        raise TimeoutError("Timed out waiting for opponent turn to complete.")

    def play_move(self, move: PlatformMove) -> bool:
        """
        Submits an action (PLAY, PASS, or EXCHANGE) on Woogles.
        """
        if not self.page:
            raise RuntimeError("Browser not started.")

        if move.action == "PASS":
            print("Executing PASS on Woogles...")
            btn_pass = self.page.locator(SELECTORS["btn_pass"]).first
            btn_pass.click()
            time.sleep(0.5)
            # Handle confirmation dialog if any
            confirm_btn = self.page.locator("button:has-text('Yes'), button:has-text('Confirm')").first
            if confirm_btn.is_visible(timeout=1000):
                confirm_btn.click()
            return True

        if move.action == "EXCHANGE":
            print(f"Executing EXCHANGE of {move.tiles_to_exchange} on Woogles...")
            try:
                # 1. Open the Exchange modal
                btn_exch = self.page.locator(SELECTORS["btn_exchange"]).first
                if btn_exch.is_visible(timeout=2000):
                    btn_exch.click()
                else:
                    self.page.keyboard.press("4")

                # 2. Wait for exchange modal dialog
                modal_sel = SELECTORS["modal_exchange"]
                modal = self.page.locator(modal_sel).first
                try:
                    modal.wait_for(state="visible", timeout=3000)
                except Exception:
                    self.page.keyboard.press("4")
                    modal.wait_for(state="visible", timeout=3000)

                time.sleep(0.3)

                # 3. Select tiles to exchange
                # Woogles's exchange modal listens for letter keypresses on window keydown
                if move.tiles_to_exchange:
                    for letter in move.tiles_to_exchange:
                        self.page.keyboard.press(letter)
                        time.sleep(0.1)

                    time.sleep(0.2)
                    selected_count = modal.locator(".tile.selected").count()
                    target_count = len(move.tiles_to_exchange)

                    # Fallback: if keyboard did not select all tiles, click unselected tiles inside modal
                    if selected_count < target_count:
                        print(f"Modal selection ({selected_count}/{target_count}); clicking unselected modal tiles...")
                        for letter in move.tiles_to_exchange:
                            unselected = modal.locator(f".tile:not(.selected)").filter(has_text=letter).first
                            if unselected.is_visible(timeout=500):
                                unselected.click()
                                time.sleep(0.1)

                # 4. Submit exchange
                time.sleep(0.2)
                submit_btn = modal.locator(SELECTORS["modal_exchange_submit"]).first
                if submit_btn.is_visible(timeout=1000) and submit_btn.is_enabled():
                    submit_btn.click()
                else:
                    self.page.keyboard.press("Enter")

                # 5. Wait for exchange modal to close
                try:
                    modal.wait_for(state="hidden", timeout=3000)
                except Exception:
                    self.page.keyboard.press("Escape")

                return True
            except Exception as e:
                print(f"⚠ Exchange execution failed on Woogles: {e}")
                try:
                    self.page.keyboard.press("Escape")
                except Exception:
                    pass
                return False

        # Action == PLAY
        if move.row is None or move.col is None or not move.word:
            raise ValueError(f"Incomplete move coordinates: {move}")

        coord_str = to_woogles_coords(move.row, move.col)
        dir_str = move.direction or "Across"
        desc = format_move_description(move.word, move.row, move.col, dir_str)
        print(f"Submitting move to Woogles: {desc}")

        # 0. Recall any uncommitted tiles to ensure a clean slate
        self.recall_tiles()
        time.sleep(0.15)

        # 1. Determine the first EMPTY square along the word's path and exact letters to type
        # In Scrabble, a word connects through existing tiles on the board.
        # Woogles automatically skips any square that already has an existing tile.
        # Typing a letter that is already on the board pushes the cursor forward and inserts an extra duplicate tile (e.g. "LEETS" instead of "LETS").
        # Therefore, we ONLY type characters for EMPTY squares!
        is_down = dir_str.lower() in ("down", "d")
        dr = 1 if is_down else 0
        dc = 0 if is_down else 1

        placement_plan = self.page.evaluate("""({row, col, isDown, word}) => {
            const tilesContainer = document.querySelector(".board-spaces-container .tiles");
            const tiles = tilesContainer ? Array.from(tilesContainer.children) : [];
            const dr = isDown ? 1 : 0;
            const dc = isDown ? 0 : 1;
            
            let firstEmpty = -1;
            const lettersToType = [];
            
            for (let k = 0; k < word.length; k++) {
                const r = row + k * dr;
                const c = col + k * dc;
                const idx = r * 15 + c;
                let hasLetter = false;
                if (tiles[idx]) {
                    const rune = tiles[idx].querySelector(".rune span, .rune");
                    if (rune && rune.innerText.trim().length > 0) {
                        hasLetter = true;
                    }
                }
                
                if (hasLetter) {
                    // Occupied square: Woogles automatically skips this when typing!
                } else {
                    // Empty square: will receive typed letter
                    if (firstEmpty === -1) {
                        firstEmpty = k;
                    }
                    lettersToType.push(word[k].toUpperCase());
                }
            }
            if (firstEmpty === -1) firstEmpty = 0;
            return { firstEmpty, lettersToType };
        }""", {"row": move.row, "col": move.col, "isDown": is_down, "word": move.word})

        first_empty_k = placement_plan["firstEmpty"]
        letters_to_type = placement_plan["lettersToType"]

        target_row = move.row + first_empty_k * dr
        target_col = move.col + first_empty_k * dc
        target_idx = target_row * 15 + target_col

        # 2. Click target empty starting square on the board
        spaces = self.page.locator("#board-spaces > div")
        if spaces.count() > target_idx:
            cell = spaces.nth(target_idx)
            cell.scroll_into_view_if_needed()
            cell.click(force=True)
        else:
            coord_str = to_woogles_coords(target_row, target_col)
            square = self.page.locator(f"[data-coord='{coord_str}'], #{coord_str}").first
            square.click(force=True)
            cell = square
        time.sleep(0.15)

        # 3. Ensure direction arrow points in the required direction (Across vs Down)
        arrow_ok = False
        for _ in range(5):
            arrow_state = self.page.evaluate("""(idx) => {
                const cell = document.querySelectorAll("#board-spaces > div")[idx];
                if (!cell) return { isSelected: false, hasRight: false, hasDown: false };
                const isSelected = cell.classList.contains("selected");
                const hasRight = !!cell.querySelector(".anticon-arrow-right, [data-icon='arrow-right']");
                const hasDown = !!cell.querySelector(".anticon-arrow-down, [data-icon='arrow-down']");
                return { isSelected, hasRight, hasDown };
            }""", target_idx)

            if not arrow_state["isSelected"]:
                cell.click(force=True)
                time.sleep(0.1)
                continue

            if is_down and arrow_state["hasDown"]:
                arrow_ok = True
                break
            if not is_down and arrow_state["hasRight"]:
                arrow_ok = True
                break

            # Toggle direction by clicking the selected cell again
            cell.click(force=True)
            time.sleep(0.15)

        if not arrow_ok:
            print(f"⚠ Failed to orient direction arrow to {'Down' if is_down else 'Across'}. Recalling...")
            self.recall_tiles()
            time.sleep(0.2)
            return False

        # Focus board container so keystrokes register reliably
        try:
            self.page.locator("#board-container").focus()
        except Exception:
            pass

        # 4. Type ONLY the letters needed for empty squares
        for char in letters_to_type:
            self.page.keyboard.press(char.upper())
            time.sleep(0.08)

        time.sleep(0.25)

        # 5. Pre-submission verification: Check that tentatively placed tiles match move.word
        tentative_matches = self.page.evaluate("""({row, col, isDown, word}) => {
            const tilesContainer = document.querySelector(".board-spaces-container .tiles");
            if (!tilesContainer) return false;
            const tiles = Array.from(tilesContainer.children);
            const dr = isDown ? 1 : 0;
            const dc = isDown ? 0 : 1;
            
            for (let k = 0; k < word.length; k++) {
                const r = row + k * dr;
                const c = col + k * dc;
                const idx = r * 15 + c;
                if (!tiles[idx]) return false;
                const rune = tiles[idx].querySelector(".rune span, .rune");
                const placedChar = rune ? rune.innerText.trim().toUpperCase() : "";
                const expectedChar = word[k].toUpperCase();
                if (placedChar !== expectedChar) {
                    return false;
                }
            }
            return true;
        }""", {"row": move.row, "col": move.col, "isDown": is_down, "word": move.word})

        if not tentative_matches:
            print(f"⚠ Placed tiles on board do not match target word '{move.word}'. Recalling uncommitted tiles...")
            self.recall_tiles()
            time.sleep(0.3)
            return False

        # 6. Click Play button or press Enter
        btn_play = self.page.locator("button.play, button:has-text('Play')").first
        try:
            if btn_play.is_visible(timeout=500) and btn_play.is_enabled():
                btn_play.click()
            else:
                self.page.keyboard.press("Enter")
        except Exception:
            self.page.keyboard.press("Enter")

        # 7. Fast polling verification (wait up to 6.0 seconds for move acceptance)
        start_wait = time.time()
        move_accepted = False
        while time.time() - start_wait < 6.0:
            status = self.page.evaluate("""(oppName) => {
                const uncommitted = document.querySelectorAll(
                    ".board-spaces-container .tiles .tile.tentative, .board-spaces-container .tiles .tentative, .board-spaces-container [class*='tentative']"
                ).length;
                const allCards = Array.from(document.querySelectorAll(".player-card"));
                const visibleCards = allCards.filter(c => 
                    c.offsetWidth > 0 && c.offsetHeight > 0
                );
                const cards = visibleCards.length >= 2 ? visibleCards : allCards;

                let oppOnTurn = false;
                let myOnTurn = false;
                cards.forEach(c => {
                    const name = c.querySelector(".player-name")?.innerText.trim().toLowerCase() || "";
                    const onTurn = c.classList.contains("on-turn");
                    if (name === (oppName || "").toLowerCase() || name.includes("bot")) {
                        oppOnTurn = onTurn;
                    } else {
                        myOnTurn = onTurn;
                    }
                });
                const endEl = document.querySelector(".end-message");
                const isGameOver = !!(endEl && endEl.offsetWidth > 0 && 
                    !endEl.innerText.toLowerCase().includes("waiting for game to start") &&
                    /wins|won|final score|draw|resigned|forfeited|timed out|game over/i.test(endEl.innerText));
                return { uncommitted, oppOnTurn, myOnTurn, isGameOver };
            }""", self.opponent_username)

            if status["isGameOver"]:
                return True

            # If uncommitted tiles are gone and it switched to opponent's turn:
            if status["uncommitted"] == 0 and (status["oppOnTurn"] or not status["myOnTurn"]):
                move_accepted = True
                break

            time.sleep(0.2)

        if not move_accepted:
            # Check if uncommitted tiles remain
            uncommitted_count = self.page.evaluate("""() => {
                return document.querySelectorAll(
                    ".board-spaces-container .tiles .tile.tentative, .board-spaces-container .tiles .tentative, .board-spaces-container [class*='tentative']"
                ).length;
            }""")
            if uncommitted_count > 0:
                print("⚠ Move was not accepted by Woogles. Recalling uncommitted tiles...")
                self.recall_tiles()
                time.sleep(0.3)
                return False

        return True

    def is_my_turn_active(self) -> bool:
        """Checks if Alphable is currently active on its turn."""
        if not self.page:
            return False
        try:
            return self.page.evaluate("""(oppName) => {
                const endEl = document.querySelector(".end-message");
                if (endEl && endEl.offsetWidth > 0 && 
                    !endEl.innerText.toLowerCase().includes("waiting for game to start") &&
                    /wins|won|final score|draw|resigned|forfeited|timed out|game over/i.test(endEl.innerText)) {
                    return false;
                }
                const allCards = Array.from(document.querySelectorAll(".player-card"));
                const visibleCards = allCards.filter(c => 
                    c.offsetWidth > 0 && c.offsetHeight > 0
                );
                const cards = visibleCards.length >= 2 ? visibleCards : allCards;

                let myOnTurn = false;
                let oppOnTurn = false;
                cards.forEach(c => {
                    const name = c.querySelector(".player-name")?.innerText.trim().toLowerCase() || "";
                    const onTurn = c.classList.contains("on-turn");
                    if (name === (oppName || "").toLowerCase() || name.includes("bot")) {
                        oppOnTurn = onTurn;
                    } else {
                        myOnTurn = onTurn;
                    }
                });
                return myOnTurn && !oppOnTurn;
            }""", self.opponent_username)
        except Exception:
            return False

    def is_game_over(self) -> bool:
        """Checks if the active match has completed."""
        if not self.page:
            return True
        try:
            return self.page.evaluate("""() => {
                const endMsgEl = document.querySelector(".end-message");
                if (endMsgEl && endMsgEl.offsetWidth > 0 && endMsgEl.offsetHeight > 0) {
                    const txt = endMsgEl.innerText.trim();
                    if (!txt.toLowerCase().includes("waiting for game to start") && 
                        /wins|won|final score|draw|resigned|forfeited|timed out|game over/i.test(txt)) {
                        return true;
                    }
                }

                const rackTiles = document.querySelectorAll("#rack .tile, .rack .tile, .rack-container .tile");
                const hasActionBtns = Array.from(document.querySelectorAll(".game-controls button, button")).some(
                    b => b.offsetWidth > 0 && /^(play|pass|exchange)$/i.test((b.innerText || "").trim())
                );
                if (rackTiles.length > 0 || hasActionBtns) {
                    return false;
                }

                const controls = document.querySelector(".game-controls");
                if (controls && controls.offsetWidth > 0) {
                    const cText = controls.innerText || "";
                    if (cText.includes("Analyze") && (cText.includes("Export") || cText.includes("Rematch") || cText.includes("Exit"))) {
                        return true;
                    }
                }

                return false;
            }""")
        except Exception:
            return False

    def get_final_result(self) -> Dict[str, Any]:
        """Fetch final scores, winner, and metadata."""
        state = self.get_game_state()
        return {
            "my_name": state.my_name,
            "opponent_name": state.opponent_name,
            "my_score": state.my_score,
            "opponent_score": state.opponent_score,
            "winner": state.winner or "Completed",
            "url": self.current_game_url,
        }

    def export_gcg(self, destination_path: str) -> Optional[str]:
        """
        Export official GCG file for the completed match.
        """
        if not self.is_browser_alive():
            return None
        try:
            # 1. Look for Export button
            export_btn = self.page.locator(".game-controls button:has-text('Export'), button:has-text('Export')").first
            try:
                export_btn.wait_for(state="visible", timeout=3000)
            except Exception:
                return None

            export_btn.click()
            time.sleep(0.5)

            # 2. Locate GCG menu item and wait until enabled
            gcg_item = self.page.locator(".ant-dropdown-menu-item:has-text('GCG'), [role='menuitem']:has-text('GCG')").first
            gcg_item.wait_for(state="visible", timeout=4000)

            # Wait for disabled class to disappear (up to 5s)
            start_w = time.time()
            while time.time() - start_w < 5.0:
                is_disabled = gcg_item.evaluate("el => el.classList.contains('ant-dropdown-menu-item-disabled')")
                if not is_disabled:
                    break
                time.sleep(0.3)

            dest = Path(destination_path)
            dest.parent.mkdir(parents=True, exist_ok=True)

            # 3. Trigger download and save
            with self.page.expect_download(timeout=6000) as download_info:
                gcg_item.click()
            download = download_info.value
            download.save_as(str(dest))
            print(f"✓ Official GCG file exported: {dest}")
            return str(dest)
        except Exception as e:
            print(f"Note: Could not export GCG file ({e})")
            return None

    def extract_analysis(self) -> List[Dict[str, Any]]:
        """
        Extract optimal move suggestions, scores, and equities from Woogles post-game Analyzer.
        """
        if not self.is_browser_alive():
            return []
        try:
            analyze_btn = self.page.locator(".game-controls button:has-text('Analyze'), button:has-text('Analyze')").first
            try:
                analyze_btn.wait_for(state="visible", timeout=3000)
            except Exception:
                return []

            print("Extracting post-game Analyzer data (Macondo WASM)...")
            analyze_btn.click()
            time.sleep(1.0)

            # Wait for analyzer card and suggestions
            self.page.wait_for_selector(".analyzer-card, .analyzer-container, .suggestions", timeout=12000)
            time.sleep(1.5)

            # Jump to the beginning of the game using << if enabled
            jump_start = self.page.locator(".game-controls .anticon-double-left, .game-controls button:has(.anticon-double-left)").first
            try:
                if jump_start.is_visible(timeout=2000) and jump_start.is_enabled():
                    jump_start.click()
                    time.sleep(0.5)
            except Exception:
                pass

            analysis_turns: List[Dict[str, Any]] = []
            max_turns = 80

            for _ in range(max_turns):
                turn_data = self.page.evaluate("""() => {
                    const header = document.querySelector(".score-card .ant-card-head-title, .score-card .ant-card-head, [class*=turn-title]");
                    const titleText = header ? header.innerText.trim() : "";
                    
                    const rows = Array.from(document.querySelectorAll(".suggestions table tbody tr"));
                    const suggestions = rows.map(r => {
                        const coords = r.querySelector(".move-coords")?.innerText.trim() || "";
                        const move = r.querySelector(".move")?.innerText.trim() || "";
                        const scoreText = r.querySelector(".move-score")?.innerText.trim() || "0";
                        const leave = r.querySelector(".move-leave")?.innerText.trim() || "";
                        const equityText = r.querySelector(".move-equity")?.innerText.trim() || "0";
                        return {
                            coords,
                            word: move,
                            points: parseInt(scoreText, 10) || 0,
                            leave,
                            equity: parseFloat(equityText) || 0.0
                        };
                    });

                    const rackTiles = Array.from(document.querySelectorAll("#rack .tile, .rack .tile")).map(t => {
                        return t.querySelector(".rune span, .rune")?.innerText.trim() || "?";
                    });

                    return {
                        turn_title: titleText,
                        rack: rackTiles,
                        suggestions: suggestions.slice(0, 10)
                    };
                }""")

                if analysis_turns and turn_data == analysis_turns[-1]:
                    # Reached end of game navigation
                    break

                if turn_data["suggestions"]:
                    analysis_turns.append(turn_data)

                # Click step forward >
                step_fwd = self.page.locator(".game-controls .anticon-right, .game-controls button:has(.anticon-right)").first
                if not step_fwd.is_visible(timeout=1000):
                    break
                is_disabled = step_fwd.evaluate("el => el.closest('button')?.disabled || el.classList.contains('disabled')")
                if is_disabled:
                    break

                step_fwd.click()
                time.sleep(0.3)

            # Close analyzer by clicking Done
            done_btn = self.page.locator(".game-controls button:has-text('Done'), button:has-text('Done')").first
            if done_btn.is_visible(timeout=2000):
                done_btn.click()
                time.sleep(0.3)

            # Jump back to game end using >> so game controls (Rematch, final scores, etc.) are restored
            jump_end = self.page.locator(".game-controls .anticon-double-right, .game-controls button:has(.anticon-double-right)").first
            try:
                if jump_end.is_visible(timeout=2000) and jump_end.is_enabled():
                    jump_end.click()
                    time.sleep(0.5)
            except Exception:
                pass

            print(f"✓ Extracted analysis for {len(analysis_turns)} turns.")
            return analysis_turns
        except Exception as e:
            print(f"Note: Could not extract Analyzer data ({e})")
            return []

    def trigger_rematch(self) -> bool:
        """
        Request or accept a rematch after game conclusion.
        Supports both new game URL redirects and in-place board state resets.
        """
        if not self.is_browser_alive():
            return False
        try:
            # If currently in replay or prior turn view (e.g. ?turn=1), jump to the end first
            jump_end = self.page.locator(".game-controls .anticon-double-right, .game-controls button:has(.anticon-double-right)").first
            try:
                if jump_end.is_visible(timeout=1500) and jump_end.is_enabled():
                    jump_end.click()
                    time.sleep(0.5)
            except Exception:
                pass

            rematch_btn = self.page.locator(".game-controls button:has-text('Rematch'), button:has-text('Rematch')").first
            try:
                rematch_btn.wait_for(state="visible", timeout=4000)
            except Exception:
                return False

            if not rematch_btn.is_enabled():
                return False

            print("Initiating rematch on Woogles...")
            old_url = self.current_game_url or self.page.url
            rematch_btn.click()

            start_w = time.time()
            while time.time() - start_w < 15.0:
                if not self.is_browser_alive():
                    return False

                status = self.page.evaluate("""(oldUrl) => {
                    const currentUrl = window.location.href;
                    const urlChanged = currentUrl !== oldUrl && currentUrl.includes("/game/");
                    
                    const endEl = document.querySelector(".end-message");
                    const hasEndMsg = !!(endEl && endEl.offsetWidth > 0 && 
                        !endEl.innerText.toLowerCase().includes("waiting for game to start") &&
                        /wins|won|final score|draw|resigned|forfeited|timed out|game over/i.test(endEl.innerText));
                    
                    const hasBoard = !!document.querySelector("#board-spaces");
                    const hasRack = !!document.querySelector("#rack");
                    
                    const actionBtns = Array.from(document.querySelectorAll(".game-controls button, button")).some(
                        b => b.offsetWidth > 0 && /^(play|pass|exchange)$/i.test((b.innerText || "").trim())
                    );
                    
                    return {
                        ready: (urlChanged || (!hasEndMsg && actionBtns)) && hasBoard && hasRack,
                        currentUrl
                    };
                }""", old_url)

                if status["ready"]:
                    self.current_game_url = status["currentUrl"]
                    self._wait_for_game_ready()
                    print(f"✓ Rematch started: {self.current_game_url}")
                    return True

                time.sleep(0.5)

            return False
        except Exception as e:
            print(f"Rematch trigger failed: {e}")
            return False

    def close(self) -> None:
        """Cleanly close browser context and Playwright instance."""
        try:
            if self.context:
                self.context.close()
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass
        finally:
            self.context = None
            self.playwright = None
            self.page = None
