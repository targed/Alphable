import torch
import pytest
from alphable.core import simulator, inference

def test_open_vs_consumed_premium_squares():
    board = simulator.create_empty_board()
    # Center square (7,7) is DW (channel 29)
    t1 = inference.board_to_tensor(board)
    assert t1[29, 7, 7] == 1.0

    # Place a tile on (7,7)
    board[7][7] = 'A'
    t2 = inference.board_to_tensor(board)
    # Letter A is on channel 0
    assert t2[0, 7, 7] == 1.0
    # Consumed premium square must now be 0.0
    assert t2[29, 7, 7] == 0.0

def test_expanded_state_vector_features():
    # Rack with 'S', '?', vowels, consonants, and duplicate 'E's
    rack = ['S', '?', 'E', 'E', 'R', 'T']
    score_diff = 25
    bag = 40
    vec = inference.state_to_tensor(rack, score_diff, bag)
    assert vec.shape == (36,)
    # Rack length at index 29: 6 / 7.0
    assert abs(vec[29].item() - 6.0 / 7.0) < 1e-4
    # Has blank at index 32: 1.0
    assert vec[32].item() == 1.0
    # Has S at index 33: 1.0
    assert vec[33].item() == 1.0
    # Duplicate penalty at index 34 (one extra 'E'): 1.0 / 7.0
    assert abs(vec[34].item() - 1.0 / 7.0) < 1e-4
