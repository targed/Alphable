"""
DOM Selectors and Coordinate Converters for Woogles.io.
Maps standard Scrabble matrix coordinates (0-14, 0-14) to Woogles board notation and UI elements.
"""

import re
from typing import Tuple

WOOGLES_BASE_URL = "https://woogles.io"

# Board dimensions
BOARD_ROWS = 15
BOARD_COLS = 15

# UI Action Button & Control Selectors
SELECTORS = {
    # Lobby & Matchmaking
    "btn_play_computer": "button:has-text('Play a computer'), text='Play a computer'",
    "btn_create_game_lobby": "button:has-text('Create a game'), text='Create a game'",
    "modal_play_computer": ".modal, [role='dialog']",
    "btn_create_game_submit": "button:has-text('Create game')",
    "select_bot_level": "text=Select bot level",
    "bot_card": ".bot-card, [data-bot-name]",
    "dict_select": "select[name='dictionary'], [role='combobox']",
    "mode_realtime": "button:has-text('Real-time')",
    "mode_correspondence": "button:has-text('Correspondence')",

    # In-game Board & Controls
    "board_container": "#board-container, .board-container",
    "board_spaces": "#board-spaces > div, #board-spaces .board-space",
    "board_tiles_container": ".board-spaces-container .tiles",
    "rack_container": "#rack, .rack, .rack-container",
    "rack_tile": "#rack .tile, .rack-container .tile",
    "btn_play": "button:has-text('Play')",
    "btn_pass": "button:has-text('Pass')",
    "btn_exchange": "button:has-text('Exchange')",
    "modal_exchange": ".ant-modal:has-text('Exchange tiles'), .exchange",
    "modal_exchange_tile": ".exchange .tile, .ant-modal .tile",
    "modal_exchange_submit": "button.ant-btn-primary, button:has-text('Exchange')",
    "btn_direction_toggle": "button:has(.anticon-arrow-down), button:has(.anticon-arrow-right)",
    "btn_recall": "button[title*='Reset Rack'], .rack-container button.ant-btn-circle, button:has(.anticon-arrow-down), button:has([data-icon='arrow-down'])",
    "bag_tile_count": "text=/\\d+\\s+tiles in bag/i",
    "player_card": ".player-card, .player-info, [data-player]",
    "active_player_indicator": ".active-player, .turn-indicator, .highlighted-turn",
}


def to_woogles_coords(row: int, col: int) -> str:
    """
    Converts 0-indexed matrix coordinates (row, col) to Woogles notation (e.g. 7, 7 -> 'H8').
    Columns: 0 -> A, 1 -> B, ..., 14 -> O
    Rows: 0 -> 1, 1 -> 2, ..., 14 -> 15
    """
    if not (0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS):
        raise ValueError(f"Coordinates out of bounds: row={row}, col={col}")
    col_letter = chr(ord('A') + col)
    row_number = row + 1
    return f"{col_letter}{row_number}"


def from_woogles_coords(coord_str: str) -> Tuple[int, int]:
    """
    Converts Woogles notation (e.g. 'H8' or '8H') to 0-indexed (row, col).
    """
    coord_clean = coord_str.strip().upper()
    # Match Letter followed by digits: e.g. H8
    m_col_first = re.match(r'^([A-O])(\d{1,2})$', coord_clean)
    if m_col_first:
        col = ord(m_col_first.group(1)) - ord('A')
        row = int(m_col_first.group(2)) - 1
        if 0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS:
            return row, col

    # Match Digits followed by letter: e.g. 8H
    m_row_first = re.match(r'^(\d{1,2})([A-O])$', coord_clean)
    if m_row_first:
        row = int(m_row_first.group(1)) - 1
        col = ord(m_row_first.group(2)) - ord('A')
        if 0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS:
            return row, col

    raise ValueError(f"Invalid Woogles coordinate format: '{coord_str}'")


def format_move_description(word: str, row: int, col: int, direction: str) -> str:
    """Format a move in human-readable Scrabble notation (e.g. 'H8 Across BLASTER')."""
    coord = to_woogles_coords(row, col)
    dir_str = "Across" if direction.lower() in ("across", "a") else "Down"
    return f"{coord} {dir_str} {word.upper()}"
