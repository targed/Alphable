import pytest
from alphable.core.defense import compute_board_defense_adjustment, TRIPLE_WORD_SQUARES, DOUBLE_WORD_SQUARES


def create_empty_board():
    return [['.' for _ in range(15)] for _ in range(15)]


def test_triple_word_occupancy_bonus():
    old_board = create_empty_board()
    new_board = create_empty_board()
    # Move occupies (0, 0) which is a Triple Word Score
    new_board[0][0] = 'Z'
    new_board[0][1] = 'O'
    new_board[0][2] = 'O'

    move = {'row': 0, 'col': 0, 'dir': 'Across', 'word': 'ZOO'}
    adj = compute_board_defense_adjustment(old_board, new_board, move, score_diff=0)

    # Should give +6.0 bonus for occupying open TWS
    assert adj >= 6.0


def test_triple_word_exposure_penalty():
    old_board = create_empty_board()
    new_board = create_empty_board()
    # Place a tile at (0, 1), which is 1 square away from (0, 0) TWS!
    new_board[0][1] = 'A'
    new_board[0][2] = 'T'

    move = {'row': 0, 'col': 1, 'dir': 'Across', 'word': 'AT'}
    adj = compute_board_defense_adjustment(old_board, new_board, move, score_diff=0)

    # Should heavily penalize (-5.5) for exposing open lane to (0, 0)
    assert adj <= -5.0


def test_lead_dependent_weighting():
    old_board = create_empty_board()
    new_board = create_empty_board()
    new_board[0][0] = 'Z'

    move = {'row': 0, 'col': 0, 'dir': 'Across', 'word': 'Z'}

    # Ahead by 50 points -> defense multiplier is 1.4
    adj_ahead = compute_board_defense_adjustment(old_board, new_board, move, score_diff=50)

    # Trailing by 50 points -> defense multiplier is 0.6
    adj_behind = compute_board_defense_adjustment(old_board, new_board, move, score_diff=-50)

    assert adj_ahead > adj_behind
    assert adj_ahead == pytest.approx(6.0 * 1.4)
    assert adj_behind == pytest.approx(6.0 * 0.6)
