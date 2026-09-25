import pytest
from playwright.sync_api import sync_playwright
from alphable.platform.woogles.adapter import WooglesAdapter
from alphable.platform.base import PlatformMove


SAMPLE_WOOGLES_HTML = """
<!DOCTYPE html>
<html>
<head><title>Woogles Match</title></head>
<body>
  <div class="board-spaces-container">
    <div class="tiles">
      <div class="tile"><span class="rune"><span>C</span></span><span class="point-value">3</span></div>
      <div class="tile"><span class="rune"><span>A</span></span><span class="point-value">1</span></div>
      <div class="tile"><span class="rune"><span>T</span></span><span class="point-value">1</span></div>
    </div>
  </div>
  <div id="rack">
    <div class="tile"><span class="rune"><span>D</span></span><span class="point-value">2</span></div>
    <div class="tile"><span class="rune"><span>O</span></span><span class="point-value">1</span></div>
    <div class="tile"><span class="rune"><span>G</span></span><span class="point-value">2</span></div>
    <div class="tile blank"><span class="rune"><span></span></span></div>
  </div>
  <div class="pool">
    <div>12 tiles in bag</div>
  </div>
  <div class="player-card on-turn" style="width: 200px; height: 50px;">
    <div class="player-info"><p class="player-name"><span>AlphableUser</span></p></div>
    <button class="score">145</button>
  </div>
  <div class="player-card" style="width: 200px; height: 50px;">
    <div class="player-info"><p class="player-name"><span>HastyBot</span></p></div>
    <button class="score">130</button>
  </div>
</body>
</html>
"""

SAMPLE_EMPTY_BAG_OPPONENT_TURN_HTML = """
<!DOCTYPE html>
<html>
<head><title>Woogles Match</title></head>
<body>
  <div class="board-spaces-container">
    <div class="tiles"></div>
  </div>
  <div id="rack">
    <div class="tile"><span class="rune"><span>E</span></span><span class="point-value">1</span></div>
    <div class="tile"><span class="rune"><span>W</span></span><span class="point-value">4</span></div>
  </div>
  <div class="pool">
    <div>Opponent has 2 tiles</div>
  </div>
  <div class="player-card" style="width: 200px; height: 50px;">
    <div class="player-info"><p class="player-name"><span>AlphableUser</span></p></div>
    <button class="score">322</button>
  </div>
  <div class="player-card on-turn" style="width: 200px; height: 50px;">
    <div class="player-info"><p class="player-name"><span>HastyBot</span></p></div>
    <button class="score">374</button>
  </div>
</body>
</html>
"""

SAMPLE_GAME_OVER_HTML = """
<!DOCTYPE html>
<html>
<head><title>Woogles Match</title></head>
<body>
  <div class="end-message">
    HastyBot wins (AlphableUser timed out!).
  </div>
  <div class="game-controls">
    <button>Export</button>
    <button>Analyze</button>
  </div>
  <div class="player-card" style="width: 200px; height: 50px;">
    <div class="player-info"><p class="player-name"><span>AlphableUser</span></p></div>
    <button class="score">360</button>
  </div>
  <div class="player-card" style="width: 200px; height: 50px;">
    <div class="player-info"><p class="player-name"><span>HastyBot</span></p></div>
    <button class="score">389</button>
  </div>
</body>
</html>
"""

SAMPLE_WAITING_FOR_GAME_HTML = """
<!DOCTYPE html>
<html>
<head><title>Woogles Match</title></head>
<body>
  <div class="end-message" style="width: 300px; height: 30px;">
    Waiting for game to start...
  </div>
  <div id="rack">
    <div class="tile"><span class="rune"><span>I</span></span><span class="point-value">1</span></div>
    <div class="tile"><span class="rune"><span>I</span></span><span class="point-value">1</span></div>
    <div class="tile"><span class="rune"><span>N</span></span><span class="point-value">1</span></div>
  </div>
  <div class="player-card on-turn" style="width: 200px; height: 50px;">
    <div class="player-info"><p class="player-name"><span>AlphableUser</span></p></div>
    <button class="score">0</button>
  </div>
  <div class="player-card" style="width: 200px; height: 50px;">
    <div class="player-info"><p class="player-name"><span>STEEBot</span></p></div>
    <button class="score">0</button>
  </div>
</body>
</html>
"""

SAMPLE_SPECTATOR_LOADING_HTML = """
<!DOCTYPE html>
<html>
<head><title>Woogles Match</title></head>
<body>
  <div class="game-controls" style="width: 300px; height: 40px;">
    <button>Analyze</button>
    <button>Exit</button>
  </div>
  <div id="rack">
    <div class="tile"><span class="rune"><span>A</span></span><span class="point-value">1</span></div>
    <div class="tile"><span class="rune"><span>B</span></span><span class="point-value">3</span></div>
  </div>
  <div class="player-card on-turn" style="width: 200px; height: 50px;">
    <div class="player-info"><p class="player-name"><span>AlphableUser</span></p></div>
    <button class="score">0</button>
  </div>
  <div class="player-card" style="width: 200px; height: 50px;">
    <div class="player-info"><p class="player-name"><span>STEEBot</span></p></div>
    <button class="score">0</button>
  </div>
</body>
</html>
"""


@pytest.fixture(scope="module")
def browser_context():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        yield context
        browser.close()


def test_woogles_adapter_state_parsing(browser_context):
    page = browser_context.new_page()
    page.set_content(SAMPLE_WOOGLES_HTML)

    adapter = WooglesAdapter()
    adapter.page = page
    adapter.opponent_username = "HastyBot"

    state = adapter.get_game_state()

    assert state.my_name == "AlphableUser"
    assert state.opponent_name == "HastyBot"
    assert state.my_score == 145
    assert state.opponent_score == 130
    assert state.bag_remaining == 12
    assert state.is_my_turn is True
    assert state.is_game_over is False
    assert state.rack == ["D", "O", "G", "?"]
    assert adapter.is_my_turn_active() is True
    assert adapter.is_game_over() is False
    page.close()


def test_woogles_adapter_empty_bag_and_opponent_turn(browser_context):
    page = browser_context.new_page()
    page.set_content(SAMPLE_EMPTY_BAG_OPPONENT_TURN_HTML)

    adapter = WooglesAdapter()
    adapter.page = page
    adapter.opponent_username = "HastyBot"

    # Must complete instantly (< 50ms) and NOT block on missing bag count
    state = adapter.get_game_state()

    assert state.bag_remaining == 0
    assert state.is_my_turn is False
    assert state.my_score == 322
    assert state.opponent_score == 374
    assert state.rack == ["E", "W"]
    assert adapter.is_my_turn_active() is False
    assert adapter.is_game_over() is False
    page.close()


def test_woogles_adapter_game_over_parsing(browser_context):
    page = browser_context.new_page()
    page.set_content(SAMPLE_GAME_OVER_HTML)

    adapter = WooglesAdapter()
    adapter.page = page
    adapter.opponent_username = "HastyBot"

    state = adapter.get_game_state()

    assert state.is_game_over is True
    assert state.winner == "HastyBot"
    assert state.is_my_turn is False
    assert adapter.is_game_over() is True

    result = adapter.get_final_result()
    assert result["winner"] == "HastyBot"
    assert result["my_score"] == 360
    assert result["opponent_score"] == 389
    page.close()


def test_woogles_adapter_waiting_for_game_start_not_game_over(browser_context):
    page = browser_context.new_page()
    page.set_content(SAMPLE_WAITING_FOR_GAME_HTML)

    adapter = WooglesAdapter()
    adapter.page = page
    adapter.opponent_username = "STEEBot"

    state = adapter.get_game_state()

    assert state.is_game_over is False
    assert adapter.is_game_over() is False
    assert state.winner is None
    assert state.rack == ["I", "I", "N"]
    assert adapter.is_my_turn_active() is True
    page.close()


def test_woogles_adapter_spectator_loading_with_rack_not_game_over(browser_context):
    page = browser_context.new_page()
    page.set_content(SAMPLE_SPECTATOR_LOADING_HTML)

    adapter = WooglesAdapter()
    adapter.page = page
    adapter.opponent_username = "STEEBot"

    state = adapter.get_game_state()

    assert state.is_game_over is False
    assert adapter.is_game_over() is False
    assert state.winner is None
    assert state.rack == ["A", "B"]
    page.close()


def test_placement_plan_skips_existing_letters(browser_context):
    page = browser_context.new_page()
    # Build a 225-tile container with 'E' at index 8*15 + 7 = 127
    tiles_html = "".join(
        f'<div class="tile"><span class="rune"><span>E</span></span><span class="point-value">1</span></div>'
        if i == (8 * 15 + 7) else '<div class="tile"></div>'
        for i in range(225)
    )
    html = f"""
    <!DOCTYPE html><html><body>
      <div class="board-spaces-container"><div class="tiles">{tiles_html}</div></div>
    </body></html>
    """
    page.set_content(html)

    # Word 'LETS' starting at row 7, col 7 Down.
    # Row 7, Col 7: empty ('L')
    # Row 8, Col 7: occupied by 'E' -> MUST BE SKIPPED!
    # Row 9, Col 7: empty ('T')
    # Row 10, Col 7: empty ('S')
    plan = page.evaluate("""({row, col, isDown, word}) => {
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
            if (!hasLetter) {
                if (firstEmpty === -1) firstEmpty = k;
                lettersToType.push(word[k].toUpperCase());
            }
        }
        if (firstEmpty === -1) firstEmpty = 0;
        return { firstEmpty, lettersToType };
    }""", {"row": 7, "col": 7, "isDown": True, "word": "LETS"})

    assert plan["firstEmpty"] == 0
    # Must NOT contain the second 'E', preventing the "LEETS" bug!
    assert plan["lettersToType"] == ["L", "T", "S"]
    page.close()


def test_placement_plan_first_letter_occupied(browser_context):
    page = browser_context.new_page()
    # 'B' at row 7, col 7 = index 112
    tiles_html = "".join(
        f'<div class="tile"><span class="rune"><span>B</span></span><span class="point-value">3</span></div>'
        if i == (7 * 15 + 7) else '<div class="tile"></div>'
        for i in range(225)
    )
    html = f"""
    <!DOCTYPE html><html><body>
      <div class="board-spaces-container"><div class="tiles">{tiles_html}</div></div>
    </body></html>
    """
    page.set_content(html)

    # Word 'BEETS' at (7, 7) Down. First letter 'B' is already on board.
    plan = page.evaluate("""({row, col, isDown, word}) => {
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
            if (!hasLetter) {
                if (firstEmpty === -1) firstEmpty = k;
                lettersToType.push(word[k].toUpperCase());
            }
        }
        if (firstEmpty === -1) firstEmpty = 0;
        return { firstEmpty, lettersToType };
    }""", {"row": 7, "col": 7, "isDown": True, "word": "BEETS"})

    assert plan["firstEmpty"] == 1
    assert plan["lettersToType"] == ["E", "E", "T", "S"]
    page.close()


def test_woogles_adapter_export_gcg_missing_returns_none(browser_context):
    page = browser_context.new_page()
    page.set_content("<!DOCTYPE html><html><body><div class='game-controls'></div></body></html>")
    adapter = WooglesAdapter()
    adapter.page = page
    res = adapter.export_gcg("/tmp/nonexistent.gcg")
    assert res is None
    page.close()


def test_woogles_adapter_extract_analysis_structure(browser_context):
    html = """
    <!DOCTYPE html>
    <html><body>
      <div class="game-controls">
        <button>Analyze</button>
        <button class="ant-btn-icon"><span class="anticon anticon-double-left"></span></button>
        <button class="ant-btn-icon"><span class="anticon anticon-right"></span></button>
        <button>Done</button>
      </div>
      <div class="score-card"><div class="ant-card-head-title">Turn 1</div></div>
      <div class="analyzer-card">
        <div class="suggestions">
          <table>
            <tbody>
              <tr>
                <td class="move-coords">8E</td>
                <td class="move">HOND</td>
                <td class="move-score">16</td>
                <td class="move-leave">IMN</td>
                <td class="move-equity">18.33</td>
              </tr>
              <tr>
                <td class="move-coords">8G</td>
                <td class="move">HIND</td>
                <td class="move-score">16</td>
                <td class="move-leave">MNO</td>
                <td class="move-equity">17.65</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </body></html>
    """
    page = browser_context.new_page()
    page.set_content(html)
    adapter = WooglesAdapter()
    adapter.page = page

    data = adapter.extract_analysis()
    assert len(data) >= 1
    turn1 = data[0]
    assert turn1["turn_title"] == "Turn 1"
    assert len(turn1["suggestions"]) == 2
    assert turn1["suggestions"][0]["word"] == "HOND"
    assert turn1["suggestions"][0]["points"] == 16
    assert turn1["suggestions"][0]["leave"] == "IMN"
    assert turn1["suggestions"][0]["equity"] == 18.33
    page.close()


def test_woogles_adapter_trigger_rematch_unavailable(browser_context):
    page = browser_context.new_page()
    page.set_content("<!DOCTYPE html><html><body><div class='game-controls'></div></body></html>")
    adapter = WooglesAdapter()
    adapter.page = page
    res = adapter.trigger_rematch()
    assert res is False
    page.close()


def test_woogles_adapter_is_browser_alive_detects_closed(browser_context):
    page = browser_context.new_page()
    adapter = WooglesAdapter()
    adapter.page = page
    assert adapter.is_browser_alive() is True

    page.close()
    assert adapter.is_browser_alive() is False


def test_woogles_adapter_trigger_rematch_in_place(browser_context):
    html = """
    <!DOCTYPE html>
    <html><body>
      <div class="game-controls">
        <button class="play">Rematch</button>
      </div>
      <div id="board-spaces" style="width: 500px; height: 500px;"><div></div></div>
      <div id="rack" style="width: 200px; height: 50px;"><div class="tile"><span class="rune"><span>A</span></span></div></div>
      <div class="end-message">Winner</div>
    </body></html>
    """
    page = browser_context.new_page()
    page.set_content(html)
    adapter = WooglesAdapter()
    adapter.page = page
    adapter.current_game_url = page.url

    # Simulate button click resetting the board in place
    page.evaluate("""() => {
        const btn = document.querySelector(".game-controls button");
        btn.addEventListener("click", () => {
            const endEl = document.querySelector(".end-message");
            if (endEl) endEl.remove();
            const controls = document.querySelector(".game-controls");
            controls.innerHTML = "<button>Play</button><button>Pass</button>";
        });
    }""")

    res = adapter.trigger_rematch()
    assert res is True
    page.close()


def test_woogles_adapter_reset_to_lobby(browser_context):
    page = browser_context.new_page()
    page.set_content("<!DOCTYPE html><html><body><div id='lobby'>Lobby</div></body></html>")
    adapter = WooglesAdapter()
    adapter.page = page
    adapter.current_game_url = "https://woogles.io/game/old_completed"

    adapter.reset_to_lobby()
    assert adapter.current_game_url is None
    page.close()


def test_woogles_adapter_rack_parsing_data_letter_and_dummy(browser_context):
    html = """
    <!DOCTYPE html>
    <html><body>
      <div id="rack">
        <!-- dl 128 is empty/dummy slot -->
        <div class="tile" data-letter="128" style="visibility: hidden;"></div>
        <!-- dl 0 is blank tile -->
        <div class="tile" data-letter="0"></div>
        <!-- dl 1 is A -->
        <div class="tile" data-letter="1"><span class="rune"><span>A</span></span><span class="point-value">1</span></div>
        <!-- dl 26 is Z -->
        <div class="tile" data-letter="26"><span class="rune"><span>Z</span></span><span class="point-value">10</span></div>
      </div>
      <div class="player-card on-turn" style="width: 200px; height: 50px;">
        <div class="player-info"><p class="player-name"><span>AlphableUser</span></p></div>
        <button class="score">100</button>
      </div>
      <div class="player-card" style="width: 200px; height: 50px;">
        <div class="player-info"><p class="player-name"><span>HastyBot</span></p></div>
        <button class="score">80</button>
      </div>
    </body></html>
    """
    page = browser_context.new_page()
    page.set_content(html)
    adapter = WooglesAdapter()
    adapter.page = page

    state = adapter.get_game_state()
    # Should skip 128 dummy slot, include '?' for dl 0, 'A' for dl 1, 'Z' for dl 26
    assert state.rack == ["?", "A", "Z"]
    page.close()


def test_woogles_adapter_rack_validation_blanks_cap(browser_context):
    # Simulates phantom state where 7 blanks are mistakenly returned
    html = """
    <!DOCTYPE html>
    <html><body>
      <div id="rack">
        <div class="tile blank" data-letter="0"></div>
        <div class="tile blank" data-letter="0"></div>
        <div class="tile blank" data-letter="0"></div>
        <div class="tile blank" data-letter="0"></div>
        <div class="tile blank" data-letter="0"></div>
        <div class="tile blank" data-letter="0"></div>
        <div class="tile blank" data-letter="0"></div>
      </div>
      <div class="player-card on-turn" style="width: 200px; height: 50px;">
        <div class="player-info"><p class="player-name"><span>AlphableUser</span></p></div>
      </div>
      <div class="player-card" style="width: 200px; height: 50px;">
        <div class="player-info"><p class="player-name"><span>HastyBot</span></p></div>
      </div>
    </body></html>
    """
    page = browser_context.new_page()
    page.set_content(html)
    adapter = WooglesAdapter()
    adapter.page = page

    state = adapter.get_game_state()
    # Rack with >2 blanks is physically impossible in Scrabble, should be sanitized to []
    assert state.rack == []
    page.close()


def test_woogles_adapter_player_card_tabs_resilience(browser_context):
    # Simulates user clicking the Chat tab, causing offsetWidth/offsetHeight = 0 on player-card elements
    html = """
    <!DOCTYPE html>
    <html><body>
      <div id="rack">
        <div class="tile" data-letter="1"><span class="rune"><span>A</span></span><span class="point-value">1</span></div>
      </div>
      <!-- Cards hidden by inactive tabpane -->
      <div class="player-card on-turn" style="display: none; width: 0px; height: 0px;">
        <div class="player-info"><p class="player-name"><span>AlphableUser</span></p></div>
        <button class="score">250</button>
      </div>
      <div class="player-card" style="display: none; width: 0px; height: 0px;">
        <div class="player-info"><p class="player-name"><span>HastyBot</span></p></div>
        <button class="score">220</button>
      </div>
    </body></html>
    """
    page = browser_context.new_page()
    page.set_content(html)
    adapter = WooglesAdapter()
    adapter.page = page
    adapter.opponent_username = "HastyBot"

    state = adapter.get_game_state()
    assert state.my_name == "AlphableUser"
    assert state.opponent_name == "HastyBot"
    assert state.my_score == 250
    assert state.opponent_score == 220
    assert state.is_my_turn is True
    assert adapter.is_my_turn_active() is True
    page.close()


def test_woogles_adapter_recall_tiles(browser_context):
    html = """
    <!DOCTYPE html>
    <html><body>
      <div id="board-container" tabindex="-1">
        <div id="board-spaces">
          <div class="selected"></div>
          <div></div>
        </div>
      </div>
      <div class="rack-container">
        <button title="Reset Rack ↓" class="ant-btn-circle" id="reset-btn">Reset</button>
      </div>
    </body></html>
    """
    page = browser_context.new_page()
    page.set_content(html)
    adapter = WooglesAdapter()
    adapter.page = page

    # Track reset button click
    page.evaluate("""() => {
        window.resetClicked = false;
        document.getElementById("reset-btn").addEventListener("click", () => {
            window.resetClicked = true;
        });
    }""")

    adapter.recall_tiles()

    was_clicked = page.evaluate("() => window.resetClicked")
    selected_count = page.evaluate("() => document.querySelectorAll('#board-spaces > div.selected').length")
    assert was_clicked is True
    assert selected_count == 0
    page.close()


def test_woogles_adapter_play_move_exchange(browser_context):
    html = """
    <!DOCTYPE html><html><body>
      <button id="btn-exchange">Exchange</button>
      <div id="modal" class="ant-modal exchange" style="display:none;">
        <div class="ant-modal-title">Exchange tiles</div>
        <div class="tile">I</div>
        <div class="tile">I</div>
        <div class="tile">I</div>
        <div class="tile">G</div>
        <button class="ant-btn ant-btn-primary">Exchange</button>
      </div>
      <script>
        const btn = document.getElementById('btn-exchange');
        const modal = document.getElementById('modal');
        btn.addEventListener('click', () => { modal.style.display = 'block'; });
        modal.querySelectorAll('.tile').forEach(t => {
          t.addEventListener('click', () => { t.classList.toggle('selected'); });
        });
        window.addEventListener('keydown', (e) => {
          if (modal.style.display !== 'none') {
            const letter = e.key.toUpperCase();
            const unselected = Array.from(modal.querySelectorAll('.tile')).find(t => t.textContent.trim() === letter && !t.classList.contains('selected'));
            if (unselected) unselected.classList.add('selected');
            if (e.key === 'Enter') modal.style.display = 'none';
          }
        });
        modal.querySelector('.ant-btn-primary').addEventListener('click', () => {
          modal.style.display = 'none';
        });
      </script>
    </body></html>
    """
    page = browser_context.new_page()
    page.set_content(html)
    adapter = WooglesAdapter()
    adapter.page = page

    move = PlatformMove(action="EXCHANGE", tiles_to_exchange=["I", "I", "I"])
    success = adapter.play_move(move)

    assert success is True
    is_hidden = page.evaluate("() => document.getElementById('modal').style.display === 'none'")
    assert is_hidden is True
    page.close()





