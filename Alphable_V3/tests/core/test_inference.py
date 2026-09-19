import pytest
import torch
from alphable.core.inference import state_to_tensor

def test_state_to_tensor_happy_path():
    rack = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    score_diff = 100
    bag_remaining = 50

    tensor = state_to_tensor(rack, score_diff, bag_remaining)

    assert tensor.shape == (36,)
    assert tensor.dtype == torch.float32

    # Check letter counts
    assert tensor[0] == 1.0  # A
    assert tensor[1] == 1.0  # B
    assert tensor[2] == 1.0  # C
    assert tensor[3] == 1.0  # D
    assert tensor[4] == 1.0  # E
    assert tensor[5] == 1.0  # F
    assert tensor[6] == 1.0  # G
    assert torch.all(tensor[7:26] == 0.0)  # H-Z
    assert tensor[26] == 0.0  # Blank

    # Check normalized values
    assert tensor[27] == pytest.approx(100 / 500.0)
    assert tensor[28] == pytest.approx(50 / 100.0)

def test_state_to_tensor_with_blanks():
    rack = ['A', '?', 'B', '?']
    score_diff = -50
    bag_remaining = 10

    tensor = state_to_tensor(rack, score_diff, bag_remaining)

    assert tensor[0] == 1.0  # A
    assert tensor[1] == 1.0  # B
    assert tensor[26] == 2.0  # Blanks
    assert torch.all(tensor[2:26] == 0.0)

    assert tensor[27] == pytest.approx(-50 / 500.0)
    assert tensor[28] == pytest.approx(10 / 100.0)

def test_state_to_tensor_all_blanks():
    rack = ['?', '?']
    score_diff = 0
    bag_remaining = 0

    tensor = state_to_tensor(rack, score_diff, bag_remaining)

    assert torch.all(tensor[0:26] == 0.0)
    assert tensor[26] == 2.0

    assert tensor[27] == 0.0
    assert tensor[28] == 0.0

def test_state_to_tensor_empty_rack():
    rack = []
    score_diff = 250
    bag_remaining = 100

    tensor = state_to_tensor(rack, score_diff, bag_remaining)

    assert torch.all(tensor[0:27] == 0.0)

    assert tensor[27] == pytest.approx(250 / 500.0)
    assert tensor[28] == pytest.approx(100 / 100.0)

def test_state_to_tensor_extreme_score():
    rack = ['Z', 'Z', 'Z'] # Not possible in real scrabble but tests the function
    score_diff = 1000
    bag_remaining = 5

    tensor = state_to_tensor(rack, score_diff, bag_remaining)

    assert tensor[25] == 3.0  # Z
    assert tensor[27] == pytest.approx(1000 / 500.0)
    assert tensor[28] == pytest.approx(5 / 100.0)

def test_state_to_tensor_negative_score_extreme():
    rack = ['Q']
    score_diff = -1000
    bag_remaining = 99

    tensor = state_to_tensor(rack, score_diff, bag_remaining)

    assert tensor[16] == 1.0  # Q
    assert tensor[27] == pytest.approx(-1000 / 500.0)
    assert tensor[28] == pytest.approx(99 / 100.0)

def test_state_to_tensor_repeated_letters():
    rack = ['A', 'A', 'A', 'A', 'A', 'A', 'A']
    score_diff = 0
    bag_remaining = 0

    tensor = state_to_tensor(rack, score_diff, bag_remaining)

    assert tensor[0] == 7.0
    assert torch.all(tensor[1:27] == 0.0)


def test_board_to_tensor_letters_and_premiums():
    from alphable.core.inference import board_to_tensor
    from alphable.core import simulator

    board = simulator.create_empty_board()
    # (0, 0) is TW
    # (7, 7) is star/center (DW)
    board[7][7] = 'C' # regular tile
    board[7][8] = 'a' # blank tile representing 'A'

    t = board_to_tensor(board)
    assert t.shape == (31, 15, 15)

    # Check 'C' at (7, 7)
    c_idx = ord('C') - 65
    assert t[c_idx, 7, 7] == 1.0
    assert t[26, 7, 7] == 0.0 # not blank

    # Check blank 'a' at (7, 8)
    a_idx = ord('A') - 65
    assert t[a_idx, 7, 8] == 1.0
    assert t[26, 7, 8] == 1.0 # blank indicator

    # Open TW at (0, 0)
    assert t[30, 0, 0] == 1.0


def test_alphable_inference_find_best_move(monkeypatch):
    from unittest.mock import MagicMock
    from alphable.core.inference import AlphableInference
    from alphable.core import simulator

    # Mock GADDAG load to be instantaneous
    monkeypatch.setattr("alphable.core.structure.Gaddag.load", lambda path: MagicMock())

    engine = AlphableInference(model_path=None, device="cpu", dict_path="dummy.txt")
    board = simulator.create_empty_board()
    rack = ["A", "B", "C"]

    # Test 1: No moves generated -> returns None, 0.0
    engine.move_gen.generate = MagicMock(return_value=[])
    best_move, best_val = engine.find_best_move(board, rack, 0, 50)
    assert best_move is None
    assert best_val == 0.0

    # Test 2: Legal moves generated -> returns top equity move
    mock_move = {"word": "AB", "row": 7, "col": 7, "dir": "across"}
    engine.move_gen.generate = MagicMock(return_value=[mock_move])
    best_move, best_val = engine.find_best_move(board, rack, 0, 50)
    assert best_move == mock_move
    assert isinstance(best_val, float)
