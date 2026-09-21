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
