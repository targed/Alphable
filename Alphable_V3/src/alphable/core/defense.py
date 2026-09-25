"""
Defensive Board Vulnerability and Hot-Spot Modeling for Alphable.

Analyzes the Scrabble board for open high-multiplier squares (Triple Word Scores, Double Word Scores)
and evaluates how candidate moves either secure, block, or dangerously expose these hot spots to opponent counterplay.
"""

from typing import List, Dict, Tuple, Set

TRIPLE_WORD_SQUARES: Set[Tuple[int, int]] = {
    (0, 0), (0, 7), (0, 14),
    (7, 0),         (7, 14),
    (14, 0), (14, 7), (14, 14),
}

DOUBLE_WORD_SQUARES: Set[Tuple[int, int]] = {
    (1, 1), (2, 2), (3, 3), (4, 4),
    (1, 13), (2, 12), (3, 11), (4, 10),
    (13, 1), (12, 2), (11, 3), (10, 4),
    (13, 13), (12, 12), (11, 11), (10, 10),
    (7, 7),
}


def compute_board_defense_adjustment(
    old_board: List[List[str]],
    new_board: List[List[str]],
    move: Dict[str, any],
    score_diff: int = 0,
) -> float:
    """
    Computes an equity bonus (or penalty) for the defensive qualities of a move.

    Positive values indicate good defense (e.g. claiming or blocking a Triple Word Score).
    Negative values indicate dangerous exposure (e.g. opening a lane directly to a TWS).

    Args:
        old_board: 15x15 board before the move.
        new_board: 15x15 board after the move.
        move: Move dict with 'row', 'col', 'dir', 'word'.
        score_diff: Current score differential (my_score - opp_score).

    Returns:
        float: Defensive equity adjustment in points.
    """
    adjustment = 0.0

    # Dynamic game situation multiplier:
    # When comfortably ahead (+40 or more), defense is paramount.
    # When trailing (-40 or worse), opening the board is necessary for comeback bingos.
    if score_diff >= 40:
        def_weight = 1.4
    elif score_diff <= -40:
        def_weight = 0.6
    else:
        def_weight = 1.0

    m_row = move["row"]
    m_col = move["col"]
    is_down = move["dir"].lower() in ("down", "d")
    w_len = len(move["word"])

    # 1. Did the move directly OCCUPY an open Triple Word Score square?
    for k in range(w_len):
        r = m_row + (k if is_down else 0)
        c = m_col + (0 if is_down else k)
        if (r, c) in TRIPLE_WORD_SQUARES:
            if old_board[r][c] == ".":
                # Successfully seized an open TWS square!
                adjustment += 6.0 * def_weight
        elif (r, c) in DOUBLE_WORD_SQUARES:
            if old_board[r][c] == ".":
                adjustment += 2.0 * def_weight

    # 2. Check for dangerous TWS exposure created by newly placed tiles
    # A tile is dangerously exposed if it creates an anchor 1 or 2 squares away
    # from an unoccupied TWS in the same row or column without a blocking tile.
    for (tws_r, tws_c) in TRIPLE_WORD_SQUARES:
        if new_board[tws_r][tws_c] != ".":
            continue  # Already occupied, not a threat

        # Check horizontal lane to this TWS
        # If any newly placed tile is in the same row within distance 1..4
        for k in range(w_len):
            r = m_row + (k if is_down else 0)
            c = m_col + (0 if is_down else k)
            if old_board[r][c] != ".":
                continue  # Tile was already on the board

            # Same row as TWS
            if r == tws_r:
                dist = abs(c - tws_c)
                if 1 <= dist <= 3:
                    # Check if line of sight is clear
                    min_c, max_c = min(c, tws_c), max(c, tws_c)
                    clear_path = all(new_board[r][step] == "." for step in range(min_c + 1, max_c))
                    if clear_path:
                        # Direct open lane to TWS!
                        # Penalty is severe if distance is 1 (immediate hook)
                        if dist == 1:
                            adjustment -= 5.5 * def_weight
                        elif dist == 2:
                            adjustment -= 3.5 * def_weight
                        else:
                            adjustment -= 2.0 * def_weight

            # Same column as TWS
            if c == tws_c:
                dist = abs(r - tws_r)
                if 1 <= dist <= 3:
                    min_r, max_r = min(r, tws_r), max(r, tws_r)
                    clear_path = all(new_board[step][c] == "." for step in range(min_r + 1, max_r))
                    if clear_path:
                        if dist == 1:
                            adjustment -= 5.5 * def_weight
                        elif dist == 2:
                            adjustment -= 3.5 * def_weight
                        else:
                            adjustment -= 2.0 * def_weight

    return round(adjustment, 2)
