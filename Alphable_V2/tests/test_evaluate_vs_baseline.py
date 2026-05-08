import pytest
import random
from unittest.mock import patch, MagicMock
from Alphable_V2.evaluate_vs_baseline import choose_baseline_move

def test_choose_baseline_move_no_legal_moves():
    """Test that None is returned when there are no legal moves."""
    assert choose_baseline_move('random', [], None, None) is None
    assert choose_baseline_move('greedy', [], None, None) is None

def test_choose_baseline_move_invalid_opponent():
    """Test that ValueError is raised for an unknown opponent type."""
    legal_moves = [{'word': 'HELLO', 'row': 7, 'col': 7, 'dir': 'Across'}]
    with pytest.raises(ValueError, match="Unknown opponent type: invalid"):
        choose_baseline_move('invalid', legal_moves, None, None)

def test_choose_baseline_move_random():
    """Test that 'random' opponent picks a move from legal_moves."""
    legal_moves = [
        {'word': 'MOVE1', 'row': 0, 'col': 0, 'dir': 'Across'},
        {'word': 'MOVE2', 'row': 1, 'col': 1, 'dir': 'Across'},
        {'word': 'MOVE3', 'row': 2, 'col': 2, 'dir': 'Across'},
    ]

    # Use a fixed seed for reproducibility or mock random.choice
    with patch('random.choice', side_effect=lambda x: x[0]) as mock_choice:
        move = choose_baseline_move('random', legal_moves, None, None)
        assert move == legal_moves[0]
        mock_choice.assert_called_once_with(legal_moves)

def test_choose_baseline_move_greedy():
    """Test that 'greedy' opponent picks the highest scoring move."""
    board = MagicMock()
    rack = MagicMock()
    legal_moves = [
        {'word': 'LOW', 'row': 0, 'col': 0, 'dir': 'Across'},
        {'word': 'HIGH', 'row': 1, 'col': 1, 'dir': 'Across'},
        {'word': 'MED', 'row': 2, 'col': 2, 'dir': 'Across'},
    ]

    # Mock simulator.simulate_move to return different points for each move
    # Returns (new_board, points, new_rack)
    mock_responses = [
        (None, 10, None), # for LOW
        (None, 50, None), # for HIGH
        (None, 30, None), # for MED
    ]

    # Need to patch where simulator is used in evaluate_vs_baseline.py
    with patch('simulator.simulate_move', side_effect=mock_responses) as mock_sim:
        move = choose_baseline_move('greedy', legal_moves, board, rack)

        assert move == legal_moves[1] # HIGH should be chosen
        assert mock_sim.call_count == 3
        # Verify it was called with correct arguments for each move
        mock_sim.assert_any_call(board, legal_moves[0], rack)
        mock_sim.assert_any_call(board, legal_moves[1], rack)
        mock_sim.assert_any_call(board, legal_moves[2], rack)

def test_choose_baseline_move_greedy_all_same_score():
    """Test greedy behavior when all moves have the same score."""
    board = MagicMock()
    rack = MagicMock()
    legal_moves = [
        {'word': 'MOVE1', 'row': 0, 'col': 0, 'dir': 'Across'},
        {'word': 'MOVE2', 'row': 1, 'col': 1, 'dir': 'Across'},
    ]

    mock_responses = [
        (None, 10, None),
        (None, 10, None),
    ]

    with patch('simulator.simulate_move', side_effect=mock_responses):
        move = choose_baseline_move('greedy', legal_moves, board, rack)
        # Should return the first one encountered if scores are tied and it's the first one > -1
        assert move == legal_moves[0]
