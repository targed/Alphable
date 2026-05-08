import pytest
from collections import Counter
from alphable.core.search import get_unseen_distribution

def create_empty_board():
    return [['.' for _ in range(15)] for _ in range(15)]

def test_get_unseen_distribution_empty_game():
    board = create_empty_board()
    my_rack = []

    unseen = get_unseen_distribution(board, my_rack)

    assert len(unseen) == 100

    counts = Counter(unseen)
    assert counts['A'] == 9
    assert counts['E'] == 12
    assert counts['?'] == 2
    assert counts['Z'] == 1

def test_get_unseen_distribution_with_rack():
    board = create_empty_board()
    my_rack = ['A', 'B', 'C', '?', 'E', 'Z', 'Q']

    unseen = get_unseen_distribution(board, my_rack)

    assert len(unseen) == 100 - 7

    counts = Counter(unseen)
    assert counts['A'] == 8 # 9 - 1
    assert counts['B'] == 1 # 2 - 1
    assert counts['C'] == 1 # 2 - 1
    assert counts['?'] == 1 # 2 - 1
    assert counts['E'] == 11 # 12 - 1
    assert counts['Z'] == 0 # 1 - 1
    assert counts['Q'] == 0 # 1 - 1

def test_get_unseen_distribution_with_board():
    board = create_empty_board()
    board[7][7] = 'A'
    board[7][8] = 'P'
    board[7][9] = 'P'
    board[7][10] = 'L'
    board[7][11] = 'E'
    my_rack = []

    unseen = get_unseen_distribution(board, my_rack)

    assert len(unseen) == 100 - 5

    counts = Counter(unseen)
    assert counts['A'] == 8
    assert counts['P'] == 0
    assert counts['L'] == 3
    assert counts['E'] == 11

def test_get_unseen_distribution_with_blanks_on_board():
    board = create_empty_board()
    board[7][7] = 'A'
    board[7][8] = 'p' # lowercase p represents a blank tile used as P
    board[7][9] = 'P'
    board[7][10] = 'L'
    board[7][11] = 'e' # lowercase e represents a blank tile used as E
    my_rack = []

    unseen = get_unseen_distribution(board, my_rack)

    assert len(unseen) == 100 - 5

    counts = Counter(unseen)
    assert counts['A'] == 8 # Used A
    assert counts['P'] == 1 # Used one P
    assert counts['L'] == 3 # Used one L
    assert counts['E'] == 12 # Did not use E, used a blank
    assert counts['?'] == 0 # Used 2 blanks (lowercase 'p' and 'e')

def test_get_unseen_distribution_mixed_board_and_rack():
    board = create_empty_board()
    board[0][0] = 'H'
    board[0][1] = 'E'
    board[0][2] = 'L'
    board[0][3] = 'L'
    board[0][4] = 'O'
    my_rack = ['W', 'O', 'R', 'L', 'D']

    unseen = get_unseen_distribution(board, my_rack)

    assert len(unseen) == 100 - 5 - 5

    counts = Counter(unseen)
    assert counts['H'] == 1
    assert counts['E'] == 11
    assert counts['L'] == 1 # 4 - 3
    assert counts['O'] == 6 # 8 - 2
    assert counts['W'] == 1 # 2 - 1
    assert counts['R'] == 5 # 6 - 1
    assert counts['D'] == 3 # 4 - 1

def test_get_unseen_distribution_over_limit():
    board = create_empty_board()
    # 10 'A's on board (limit is 9)
    for i in range(10):
        board[0][i] = 'A'
    my_rack = ['A'] # 1 'A' in rack

    unseen = get_unseen_distribution(board, my_rack)

    # Standard bag has 9 'A's. The function subtracts 11 'A's.
    # The count becomes -2. The list construction only adds characters with count > 0.
    # This means all 9 original 'A's are effectively removed, and 0 'A's are added to the list.
    # The resulting length should be 100 - 9 (all 'A's are gone) = 91.
    assert len(unseen) == 91

    counts = Counter(unseen)
    # Since total 'A' is 9, 9 - 11 = -2. The function should only include items with count > 0.
    assert counts['A'] == 0
    # Make sure we didn't add negative elements
    assert 'A' not in unseen
