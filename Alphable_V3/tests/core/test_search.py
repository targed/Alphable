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


def test_search_bc_0ply_mode():
    from unittest.mock import MagicMock
    import torch
    from alphable.core.search import AlphableSearch

    mock_engine = MagicMock()
    mock_engine.device = 'cpu'
    mock_engine.model.return_value = torch.zeros((5, 1))

    cand = {'row': 7, 'col': 7, 'dir': 'Across', 'word': 'TEST'}
    mock_engine.move_gen.generate.return_value = [cand]

    searcher = AlphableSearch(
        inference_engine=mock_engine,
        mode='bc_0ply',
        top_k_candidates=1,
    )
    board = create_empty_board()
    best_move, best_val = searcher.find_best_move(board, ['T', 'E', 'S', 'T'], score_diff=0, bag_remaining=86)
    assert best_move['word'] == 'TEST'


def test_search_no_legal_moves():
    from unittest.mock import MagicMock
    from alphable.core.search import AlphableSearch

    mock_engine = MagicMock()
    mock_engine.device = 'cpu'
    mock_engine.move_gen.generate.return_value = []

    searcher = AlphableSearch(inference_engine=mock_engine, mode='lookahead')
    board = create_empty_board()
    best_move, best_val = searcher.find_best_move(board, ['A', 'B'], score_diff=0, bag_remaining=50)
    assert best_move is None
    assert best_val == 0.0


def test_search_opponent_has_no_moves_passes():
    from unittest.mock import MagicMock
    import torch
    from alphable.core.search import AlphableSearch

    mock_engine = MagicMock()
    mock_engine.device = 'cpu'
    mock_engine.model.return_value = torch.ones((5, 1)) * 0.5

    cand = {'row': 7, 'col': 7, 'dir': 'Across', 'word': 'TEST'}

    def mock_generate(board, rack):
        if board[7][7] == '.':
            return [cand]
        return [] # Opponent has no replies and passes

    mock_engine.move_gen.generate.side_effect = mock_generate

    searcher = AlphableSearch(
        inference_engine=mock_engine,
        num_simulations=1,
        top_k_candidates=1,
        opp_reply_top_k=1,
        mode='lookahead',
    )
    board = create_empty_board()
    best_move, best_val = searcher.find_best_move(board, ['T', 'E', 'S', 'T'], score_diff=0, bag_remaining=86)
    assert best_move['word'] == 'TEST'
    assert best_val == pytest.approx(0.5)


def test_blank_preservation_over_low_score():
    from unittest.mock import MagicMock
    import torch
    from alphable.core.search import AlphableSearch

    mock_engine = MagicMock()
    mock_engine.device = 'cpu'
    mock_engine.model.return_value = torch.zeros((10, 1))

    # cand1 burns ? for 16 pts by playing DAWTS (S is not in rack naturally)
    cand1 = {'row': 7, 'col': 7, 'dir': 'Across', 'word': 'DAWTS'}
    # cand2 plays DINT for 10 pts and keeps ?
    cand2 = {'row': 7, 'col': 7, 'dir': 'Across', 'word': 'DINT'}

    def mock_generate(board, rack):
        if board[7][7] == '.':
            return [cand1, cand2]
        return []  # opponent passes

    mock_engine.move_gen.generate.side_effect = mock_generate

    searcher = AlphableSearch(
        inference_engine=mock_engine,
        num_simulations=1,
        top_k_candidates=2,
        opp_reply_top_k=1,
        mode='lookahead',
    )
    board = create_empty_board()
    # Rack with blank
    rack = ['D', 'A', 'W', 'T', 'I', 'N', '?']
    best_move, _ = searcher.find_best_move(board, rack, score_diff=0, bag_remaining=70)

    # DINT must be selected over DAWTS because keeping ? (+26.5 leave) far outweighs +6 raw score difference!
    assert best_move['word'] == 'DINT'


def test_exchange_generated_on_all_consonants():
    from unittest.mock import MagicMock
    from alphable.core.search import AlphableSearch

    mock_engine = MagicMock()
    searcher = AlphableSearch(inference_engine=mock_engine)
    board = create_empty_board()
    rack = ['B', 'C', 'D', 'F', 'G', 'G', 'K']

    exchanges = searcher._generate_exchange_candidates(board, rack, score_diff=0, bag_remaining=50)
    assert len(exchanges) > 0
    assert exchanges[0]['move']['action'] == 'EXCHANGE'
    assert len(exchanges[0]['move']['tiles_to_exchange']) >= 3


def test_exchange_chosen_over_terrible_board_move():
    from unittest.mock import MagicMock
    import torch
    from alphable.core.search import AlphableSearch

    mock_engine = MagicMock()
    mock_engine.device = 'cpu'
    mock_engine.model.return_value = torch.zeros((10, 1))

    board = create_empty_board()
    board[7][7] = 'E'
    rack = ['B', 'C', 'D', 'F', 'G', 'K', 'V']

    # Playing FE scores 5 points but leaves 0 vowels (BCDGKV with -24.2 leave equity)
    weak_move = {'row': 7, 'col': 6, 'dir': 'Across', 'word': 'FE'}

    def mock_generate(b, r):
        if b[7][6] == '.':
            return [weak_move]
        return []

    mock_engine.move_gen.generate.side_effect = mock_generate

    searcher = AlphableSearch(
        inference_engine=mock_engine,
        num_simulations=1,
        top_k_candidates=2,
        opp_reply_top_k=1,
        mode='lookahead',
    )
    best_move, _ = searcher.find_best_move(board, rack, score_diff=0, bag_remaining=40)

    # Exchanging clunky consonants should be chosen over playing FE and crippling the rack
    assert best_move.get('action') == 'EXCHANGE'
    assert len(best_move.get('tiles_to_exchange')) >= 3


def test_two_stage_pruning_filters_opponent_moves():
    from unittest.mock import MagicMock
    import torch
    from alphable.core.search import AlphableSearch

    mock_engine = MagicMock()
    mock_engine.device = 'cpu'
    # Return 0.0 values for batch inputs
    mock_engine.model.side_effect = lambda b, s: torch.zeros((b.shape[0], 1))

    board = create_empty_board()
    board[7][7] = 'A'

    cand = {'row': 7, 'col': 8, 'dir': 'Across', 'word': 'AT'}

    # Generate 50 opponent replies
    opp_replies = [
        {'row': 0, 'col': 0, 'dir': 'Across', 'word': f'M{i}'}
        for i in range(50)
    ]

    def mock_generate(b, r):
        if b[7][8] == '.':
            return [cand]
        return opp_replies

    mock_engine.move_gen.generate.side_effect = mock_generate

    # Set opp_reply_prune_k=5
    searcher = AlphableSearch(
        inference_engine=mock_engine,
        num_simulations=1,
        top_k_candidates=1,
        opp_reply_prune_k=5,
        mode='lookahead',
    )
    rack = ['A', 'T', 'E', 'R', 'S', 'I', 'N']
    searcher.find_best_move(board, rack, score_diff=0, bag_remaining=60)

    # In Step 4 simulation, mock_engine.model should only have been called with at most 5 opponent moves in the batch
    # instead of all 50!
    for call in mock_engine.model.call_args_list:
        b_arg, s_arg = call[0]
        # First call is 0-ply candidate eval (1 move). Subsequent calls in simulation must be <= opp_reply_prune_k (5)
        assert b_arg.shape[0] <= 5


