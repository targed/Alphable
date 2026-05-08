import pytest
import torch
from alphable.core.inference import board_to_tensor
from alphable.core.simulator import PREMIUM_SQUARES

def create_empty_board():
    return [['.' for _ in range(15)] for _ in range(15)]

def test_board_to_tensor_shape_and_type():
    board = create_empty_board()
    tensor = board_to_tensor(board)
    assert tensor.shape == (31, 15, 15)
    assert tensor.dtype == torch.float32

def test_board_to_tensor_empty_board():
    board = create_empty_board()
    tensor = board_to_tensor(board)

    # Check that channels 0-26 (letters and blanks) are all zeros
    assert torch.all(tensor[0:27, :, :] == 0.0)

    # Check that premium squares are populated correctly
    # 27: DL, 28: TL, 29: DW, 30: TW
    for (r, c), prem in PREMIUM_SQUARES.items():
        if prem == 'DL':
            assert tensor[27, r, c] == 1.0
        elif prem == 'TL':
            assert tensor[28, r, c] == 1.0
        elif prem == 'DW':
            assert tensor[29, r, c] == 1.0
        elif prem == 'TW':
            assert tensor[30, r, c] == 1.0

    # Check that non-premium squares are 0.0 in premium channels
    for r in range(15):
        for c in range(15):
            if (r, c) not in PREMIUM_SQUARES:
                assert tensor[27, r, c] == 0.0
                assert tensor[28, r, c] == 0.0
                assert tensor[29, r, c] == 0.0
                assert tensor[30, r, c] == 0.0

def test_board_to_tensor_regular_letters():
    board = create_empty_board()
    # Place 'A' at (0, 0) and 'Z' at (14, 14)
    board[0][0] = 'A'
    board[14][14] = 'Z'

    tensor = board_to_tensor(board)

    # 'A' is index 0
    assert tensor[0, 0, 0] == 1.0
    # No blank indicator for regular letter
    assert tensor[26, 0, 0] == 0.0

    # 'Z' is index 25
    assert tensor[25, 14, 14] == 1.0
    assert tensor[26, 14, 14] == 0.0

    # Check that other positions in channel 0 are 0
    assert torch.sum(tensor[0, :, :]) == 1.0
    assert torch.sum(tensor[25, :, :]) == 1.0

def test_board_to_tensor_blank_tiles():
    board = create_empty_board()
    # Place blank 'a' at (7, 7) and blank 'z' at (8, 8)
    board[7][7] = 'a'
    board[8][8] = 'z'

    tensor = board_to_tensor(board)

    # Blank 'a' acts as 'A' (index 0) but sets blank channel (26)
    assert tensor[0, 7, 7] == 1.0
    assert tensor[26, 7, 7] == 1.0

    # Blank 'z' acts as 'Z' (index 25) and sets blank channel (26)
    assert tensor[25, 8, 8] == 1.0
    assert tensor[26, 8, 8] == 1.0

    # Check sums to ensure they were only set once
    assert torch.sum(tensor[0, :, :]) == 1.0
    assert torch.sum(tensor[25, :, :]) == 1.0
    assert torch.sum(tensor[26, :, :]) == 2.0
