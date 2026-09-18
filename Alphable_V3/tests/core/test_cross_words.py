import pytest
from alphable.core import simulator

def test_cross_word_single_hook():
    """
    Test that placing a word Across that hooks vertically to an existing tile
    calculates points for both the primary word and the formed cross-word.
    """
    board = simulator.create_empty_board()
    # Place 'C' at (6, 7)
    board[6][7] = 'C'

    # Play 'AT' at (7, 7) Across -> Primary word 'AT' (A at (7,7), T at (7,8))
    # (7,7) is center square DW.
    # Primary word: A=1 (on DW -> letter=1), T=1 (no prem -> letter=1).
    # Primary word multiplier: 2 (from (7,7) DW) -> (1 + 1) * 2 = 4 points.
    #
    # Cross word formed: 'CA' Down from (6,7) to (7,7).
    # 'C' at (6,7) is existing -> letter value 3.
    # 'A' at (7,7) is placed on DW -> letter value 1, word multiplier 2.
    # Cross word score: (C=3 + A=1) * 2 = 8 points.
    #
    # Total move points = 4 (primary) + 8 (cross) = 12 points.
    move = {'row': 7, 'col': 7, 'dir': 'Across', 'word': 'AT'}
    new_board, points, new_rack = simulator.simulate_move(board, move, ['A', 'T', 'Z'])

    assert new_board[7][7] == 'A'
    assert new_board[7][8] == 'T'
    assert new_rack == ['Z']
    assert points == 12

def test_cross_word_multiple_hooks():
    """
    Test placing a 3-letter word Across that hooks into two existing letters above it.
    """
    board = simulator.create_empty_board()
    # Row 4, cols 4, 5, 6
    # Place 'N' at (3, 4) and 'P' at (3, 6)
    board[3][4] = 'N'
    board[3][6] = 'P'

    # Play 'ORE' Across at row 4, cols 4, 5, 6
    # (4,4) is DW, (4,5) is empty/no premium, (4,6) is no premium
    #
    # Primary word 'ORE':
    # O at (4,4): letter 1, DW
    # R at (4,5): letter 1
    # E at (4,6): letter 1
    # Primary word score: (1 + 1 + 1) * 2 = 6 points.
    #
    # Cross word 1 at col 4: 'N' + 'O' -> 'NO' (Down from (3,4) to (4,4))
    # N=1 (existing), O=1 (new on DW) -> (1 + 1) * 2 = 4 points.
    #
    # Cross word 2 at col 6: 'P' + 'E' -> 'PE' (Down from (3,6) to (4,6))
    # P=3 (existing), E=1 (new, no premium) -> 3 + 1 = 4 points.
    #
    # Col 5: no adjacent tile, no cross word.
    # Total points = 6 + 4 + 4 = 14 points.
    move = {'row': 4, 'col': 4, 'dir': 'Across', 'word': 'ORE'}
    new_board, points, new_rack = simulator.simulate_move(board, move, ['O', 'R', 'E'])

    assert points == 14

def test_cross_word_down_direction():
    """
    Test placing a word Down that hooks horizontally into an existing tile.
    """
    board = simulator.create_empty_board()
    # Place 'B' at (7, 6)
    board[7][6] = 'B'

    # Play 'AN' Down at (7, 7)
    # (7,7) is center DW.
    # Primary word 'AN' Down: A at (7,7) [DW], N at (8,7) [no prem].
    # Primary word score: (A=1 + N=1) * 2 = 4 points.
    #
    # Cross word formed Across: 'BA' from (7,6) to (7,7).
    # B=3 (existing), A=1 (new on DW).
    # Cross word score: (B=3 + A=1) * 2 = 8 points.
    #
    # Total move points = 4 + 8 = 12 points.
    move = {'row': 7, 'col': 7, 'dir': 'Down', 'word': 'AN'}
    new_board, points, new_rack = simulator.simulate_move(board, move, ['A', 'N', 'K'])

    assert points == 12

def test_cross_word_with_blanks():
    """
    Test cross words where placed or existing tiles are blanks.
    """
    board = simulator.create_empty_board()
    # Lowercase 'c' at (6, 7) represents an existing blank
    board[6][7] = 'c'

    # Play 'AT' Across at (7, 7) using a blank for 'A' ('?')
    # (7,7) is DW.
    # Primary: blank A=0, T=1 -> (0 + 1) * 2 = 2 points.
    # Cross word 'cA': blank c=0, blank A=0 -> (0 + 0) * 2 = 0 points.
    # Total points = 2 + 0 = 2 points.
    move = {'row': 7, 'col': 7, 'dir': 'Across', 'word': 'AT'}
    new_board, points, new_rack = simulator.simulate_move(board, move, ['?', 'T'])

    assert new_board[7][7] == 'a' # placed as blank (lowercase)
    assert points == 2

def test_apply_endgame_adjustments_consecutive_passes():
    scores = [200, 200]
    racks = [['Q', 'Z'], ['A']] # Q=10, Z=10 -> 20 pts. A=1 -> 1 pt.
    from alphable.training.self_play import apply_endgame_adjustments
    apply_endgame_adjustments(scores, racks)
    # When both players have tiles left, each subtracts their own rack penalty
    assert scores[0] == 180
    assert scores[1] == 199

def test_apply_endgame_adjustments_one_empty():
    scores = [200, 200]
    racks = [[], ['A', 'B']] # A=1, B=3 -> 4 pts.
    from alphable.training.self_play import apply_endgame_adjustments
    apply_endgame_adjustments(scores, racks)
    # Winner gets +4, loser loses 4
    assert scores[0] == 204
    assert scores[1] == 196
