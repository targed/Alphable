import pytest
from alphable.core.simulator import create_empty_board

def test_create_empty_board_dimensions_and_content():
    board = create_empty_board()

    # Check it's a list
    assert isinstance(board, list)

    # Check it has 15 rows
    assert len(board) == 15

    # Check each row is a list of 15 elements, and all elements are '.'
    for row in board:
        assert isinstance(row, list)
        assert len(row) == 15
        for cell in row:
            assert cell == '.'

def test_create_empty_board_no_reference_aliasing():
    # Ensure that modifying one row doesn't modify others
    # which would happen if board was created like [['.'] * 15] * 15
    board = create_empty_board()
    board[0][0] = 'A'

    assert board[0][0] == 'A'

    # Check that the rest of the first column is still '.'
    for i in range(1, 15):
        assert board[i][0] == '.'
