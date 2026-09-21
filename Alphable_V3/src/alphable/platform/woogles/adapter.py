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

    def start(self, headless: bool = False, user_data_dir: Optional[str] = None) -> None:
        """
        Launch Chromium browser with a persistent user profile to retain logins.
        """
        if user_data_dir is None:
            user_data_dir = os.path.expanduser("~/.alphable/woogles_profile")
        self.user_data_dir = user_data_dir
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)

        self.playwright = sync_playwright().start()

        # Launch persistent context
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            viewport={"width": 1280, "height": 850},
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

    def create_game(self, config: PlatformGameConfig) -> str:
        """
        Automates creating a match against a computer bot or player.
        """
        if not self.page:
            raise RuntimeError("Browser not started.")

        # 1. Check if already inside an active ongoing game
        if "/game/" in self.page.url:
            time.sleep(0.5)
            if self.page.locator("#board-spaces").count() > 0 and self.page.locator("#rack").count() > 0:
                if not self.is_game_over():
                    print(f"✓ Detected ongoing match at {self.page.url}. Resuming play...")
                    self.current_game_url = self.page.url
                    self.opponent_username = config.bot_name or "Opponent"
                    return self.current_game_url

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
                self.page.wait_for_selector("#board-spaces", timeout=15000)
                try:
                    self.page.wait_for_selector("#rack .tile", timeout=5000)
                except Exception:
                    pass
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
            bot_elem = self.page.locator(f"text={config.bot_name}").first
            if not bot_elem.is_visible(timeout=1000):
                # Click bot selector card to expand options
                bot_card = self.page.locator("text=/\\b(HastyBot|BestBot|BeginnerBot)\\b/").first
                if bot_card.is_visible():
                    bot_card.click()
                    time.sleep(0.3)
                    # Click target bot option
                    self.page.locator(f"text={config.bot_name}").first.click()
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

        # 6. Wait for game board to render
        print("Waiting for game board to load...")
        self.page.wait_for_url("**/game/**", timeout=20000)
        self.page.wait_for_selector("#board-spaces", timeout=15000)
        time.sleep(1.0)

        self.current_game_url = self.page.url
        print(f"✓ Game successfully loaded: {self.current_game_url}")
        return self.current_game_url

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

        # 2. Parse Rack Tiles via #rack .tile (including blank tiles with no letter or point value)
        rack = self.page.evaluate("""() => {
            const tiles = [];
            const rackTiles = document.querySelectorAll("#rack .tile, .rack .tile, .rack-container .tile");
            rackTiles.forEach(t => {
                const rune = t.querySelector(".rune span, .rune");
                const txt = rune ? rune.innerText.trim() : "";
                const pts = t.querySelector(".point-value")?.innerText.trim();

                // On Woogles, blank tiles have no point-value element or empty rune text
                if (!pts || pts === "0" || !txt || t.className.includes("blank")) {
                    tiles.push("?");
                } else {
                    const first = txt[0].toUpperCase();
                    if (first >= "A" && first <= "Z") {
                        tiles.push(first);
                    } else {
                        tiles.push("?");
                    }
                }
            });
            return tiles;
        }""")

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

            // Player Cards & Scores
            const visibleCards = Array.from(document.querySelectorAll(".player-card")).filter(c => 
                c.offsetWidth > 0 && c.offsetHeight > 0
            );

            let myName = "Alphable";
            let oppName = oppNameParam || "Opponent";
            let myScore = 0;
            let oppScore = 0;
            let myOnTurn = false;
            let oppOnTurn = false;

            visibleCards.forEach(c => {
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

            // End message / Game Over
            const endMsgEl = document.querySelector(".end-message");
            let isGameOver = !!endMsgEl;
            let winner = null;
            if (endMsgEl) {
                const txt = endMsgEl.innerText.trim();
                const mWin = txt.match(/([A-Za-z0-9_]+)\\s+wins/);
                if (mWin) {
                    winner = mWin[1];
                } else {
                    winner = myScore > oppScore ? myName : (oppScore > myScore ? oppName : "Draw");
                }
            } else {
                const controls = document.querySelector(".game-controls");
                if (controls && controls.innerText.includes("Analyze")) {
                    isGameOver = true;
                    winner = myScore > oppScore ? myName : (oppScore > myScore ? oppName : "Draw");
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

    def wait_for_my_turn(self, poll_interval: float = 0.5, timeout: float = 300.0) -> OnlineGameState:
        """
        Polls until it is Alphable's turn to play.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            state = self.get_game_state()
            if state.is_game_over:
                return state
            if state.bag_remaining == 0 and len(state.rack) == 0:
                state.is_game_over = True
                return state
            if state.is_my_turn and len(state.rack) > 0:
                return state
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
            btn_exch = self.page.locator(SELECTORS["btn_exchange"]).first
            btn_exch.click()
            time.sleep(0.5)
            # Select rack tiles to exchange
            if move.tiles_to_exchange:
                for letter in move.tiles_to_exchange:
                    tile_el = self.page.locator(f".rack .tile:has-text('{letter}')").first
                    if tile_el.is_visible():
                        tile_el.click()
            # Submit exchange
            submit_btn = self.page.locator("button:has-text('Submit'), button:has-text('Exchange')").first
            submit_btn.click()
            return True

        # Action == PLAY
        if move.row is None or move.col is None or not move.word:
            raise ValueError(f"Incomplete move coordinates: {move}")

        coord_str = to_woogles_coords(move.row, move.col)
        dir_str = move.direction or "Across"
        desc = format_move_description(move.word, move.row, move.col, dir_str)
        print(f"Submitting move to Woogles: {desc}")

        # 0. Recall any uncommitted tiles
        self.page.keyboard.press("Escape")
        time.sleep(0.15)

        # 1. Determine the first EMPTY square along the word's path
        # In Scrabble, a word may connect through existing tiles on the board.
        # Woogles only allows selecting an EMPTY square; clicking an occupied tile fails to focus.
        is_down = dir_str.lower() in ("down", "d")
        dr = 1 if is_down else 0
        dc = 0 if is_down else 1

        first_empty_k, letters_to_type = self.page.evaluate("""({row, col, isDown, word}) => {
            const tilesContainer = document.querySelector(".board-spaces-container .tiles");
            const tiles = tilesContainer ? Array.from(tilesContainer.children) : [];
            const dr = isDown ? 1 : 0;
            const dc = isDown ? 0 : 1;
            
            let firstEmpty = -1;
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
                if (!hasLetter && firstEmpty === -1) {
                    firstEmpty = k;
                }
            }
            if (firstEmpty === -1) firstEmpty = 0;
            return [firstEmpty, word.slice(firstEmpty)];
        }""", {"row": move.row, "col": move.col, "isDown": is_down, "word": move.word})

        target_row = move.row + first_empty_k * dr
        target_col = move.col + first_empty_k * dc
        target_idx = target_row * 15 + target_col

        # 2. Click the target empty starting square on the board
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

        # Verify that the cell is actually selected
        try:
            is_selected = cell.evaluate("el => el.classList.contains('selected')")
            if not is_selected:
                cell.click(force=True)
                time.sleep(0.15)
        except Exception:
            pass

        # 3. Verify direction arrow directly on the selected cell (Across vs Down)
        has_down = cell.locator(".anticon-arrow-down").count() > 0
        has_right = cell.locator(".anticon-arrow-right").count() > 0

        if is_down and not has_down:
            cell.click(force=True)
            time.sleep(0.1)
            if cell.locator(".anticon-arrow-down").count() == 0:
                self.page.keyboard.press("Space")
                time.sleep(0.1)
        elif not is_down and not has_right:
            cell.click(force=True)
            time.sleep(0.1)
            if cell.locator(".anticon-arrow-right").count() == 0:
                self.page.keyboard.press("Space")
                time.sleep(0.1)

        # 4. Type remaining letters sequentially
        for char in letters_to_type:
            self.page.keyboard.press(char.upper())
            time.sleep(0.06)

        time.sleep(0.2)

        # 5. Click Play button or press Enter
        btn_play = self.page.locator("button.play, button:has-text('Play')").first
        try:
            if btn_play.is_visible(timeout=500) and btn_play.is_enabled():
                btn_play.click()
            else:
                self.page.keyboard.press("Enter")
        except Exception:
            self.page.keyboard.press("Enter")

        # 6. Fast polling verification (wait up to 6.0 seconds for move acceptance)
        start_wait = time.time()
        move_accepted = False
        while time.time() - start_wait < 6.0:
            status = self.page.evaluate("""(oppName) => {
                const uncommitted = document.querySelectorAll(
                    ".board-spaces-container .tiles > div.second-color, .board-spaces-container .tiles > div.uncommitted"
                ).length;
                const visibleCards = Array.from(document.querySelectorAll(".player-card")).filter(c => 
                    c.offsetWidth > 0 && c.offsetHeight > 0
                );
                let oppOnTurn = false;
                let myOnTurn = false;
                visibleCards.forEach(c => {
                    const name = c.querySelector(".player-name")?.innerText.trim().toLowerCase() || "";
                    const onTurn = c.classList.contains("on-turn");
                    if (name === (oppName || "").toLowerCase() || name.includes("bot")) {
                        oppOnTurn = onTurn;
                    } else {
                        myOnTurn = onTurn;
                    }
                });
                const isGameOver = !!document.querySelector(".end-message");
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
                    ".board-spaces-container .tiles > div.second-color, .board-spaces-container .tiles > div.uncommitted"
                ).length;
            }""")
            if uncommitted_count > 0:
                print("⚠ Move was not accepted by Woogles. Recalling uncommitted tiles with Escape...")
                self.page.keyboard.press("Escape")
                time.sleep(0.3)
                return False

        return True

    def is_my_turn_active(self) -> bool:
        """Checks if Alphable is currently active on its turn."""
        if not self.page:
            return False
        try:
            return self.page.evaluate("""(oppName) => {
                if (document.querySelector(".end-message")) return false;
                const visibleCards = Array.from(document.querySelectorAll(".player-card")).filter(c => 
                    c.offsetWidth > 0 && c.offsetHeight > 0
                );
                let myOnTurn = false;
                let oppOnTurn = false;
                visibleCards.forEach(c => {
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
                if (document.querySelector(".end-message")) return true;
                const controls = document.querySelector(".game-controls");
                if (controls && controls.innerText.includes("Analyze")) return true;
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
