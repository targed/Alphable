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


def test_search_penalizes_moves_conceding_high_opponent_equity():
    from unittest.mock import MagicMock
    import torch
    from alphable.core.search import AlphableSearch

    mock_engine = MagicMock()
    mock_engine.device = 'cpu'
    # Mock model outputs constant 0.0 value
    mock_engine.model.return_value = torch.zeros((10, 1))

    # Candidate 1 gives us 30 points, but opens board so opponent replies with 50 points
    # Candidate 2 gives us 25 points, and keeps board closed so opponent replies with 5 points
    cand1 = {'row': 7, 'col': 7, 'dir': 'Across', 'word': 'OPEN'}
    cand2 = {'row': 7, 'col': 7, 'dir': 'Across', 'word': 'SAFE'}

    opp_reply_to_open = {'row': 7, 'col': 11, 'dir': 'Down', 'word': 'ZOO'} # 50 pts
    opp_reply_to_safe = {'row': 7, 'col': 11, 'dir': 'Down', 'word': 'IT'}  # 5 pts

    def mock_generate(board, rack):
        # Initial turn: return the two candidates
        if board[7][7] == '.':
            return [cand1, cand2]
        # Opponent replies
        if 'O' in [board[7][7], board[7][8], board[7][9], board[7][10]]:
            return [opp_reply_to_open]
        return [opp_reply_to_safe]

    mock_engine.move_gen.generate.side_effect = mock_generate

    searcher = AlphableSearch(
        inference_engine=mock_engine,
        num_simulations=2,
        top_k_candidates=2,
        opp_reply_top_k=1,
        mode='lookahead',
    )

    board = create_empty_board()
    rack = ['O', 'P', 'E', 'N', 'S', 'A', 'F']
    best_move, _ = searcher.find_best_move(board, rack, score_diff=0, bag_remaining=86)

    # Safe move should be chosen because it doesn't concede a 50-point play!
    assert best_move['word'] == 'SAFE'
