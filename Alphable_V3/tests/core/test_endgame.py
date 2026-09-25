import pytest
from unittest.mock import MagicMock
import torch
from alphable.core.endgame import ExactEndgameSolver, TILE_VALUES


def test_terminal_player_out_evaluation():
    # If our move uses all tiles, terminal value is points + 2 * sum(opp_rack)
    opp_rack = ['Q', 'Z']  # 10 + 10 = 20 pts
    bonus = 2 * sum(TILE_VALUES[t] for t in opp_rack)
    assert bonus == 40


def test_endgame_solver_selects_out_move():
    mock_engine = MagicMock()
    solver = ExactEndgameSolver(mock_engine)

    board = [['.' for _ in range(15)] for _ in range(15)]
    board[7][7] = 'C'
    board[7][8] = 'A'
    board[7][9] = 'T'

    # Move 1: 'S' plays CATS for 6 points and EMPTIES our rack!
    # Opponent holds ['Z', 'Q'] (worth 20 pts).
    # Total net swing = 6 + 2 * (20) = 46 pts!
    move_out = {'row': 7, 'col': 10, 'dir': 'Across', 'word': 'CATS'}

    # Move 2: 'A' plays AT for 8 points, but leaves 'S' on our rack (not going out).
    move_not_out = {'row': 7, 'col': 9, 'dir': 'Down', 'word': 'TO'}

    def mock_generate(b, rack):
        if 'S' in rack and len(rack) == 1:
            return [move_out]
        return [move_not_out]

    mock_engine.move_gen.generate.side_effect = mock_generate

    my_rack = ['S']
    opp_rack = ['Z', 'Q']

    best_move, best_margin = solver.solve(board, my_rack, opp_rack, score_diff=0, max_depth=2)
    assert best_move is not None
    assert best_move['word'] == 'CATS'
    # Score diff was 0. CATS scores 6 + (2 * 20) bonus = 46.
    assert best_margin >= 40.0


def test_search_delegates_to_endgame_when_bag_empty():
    from alphable.core.search import AlphableSearch

    mock_engine = MagicMock()
    mock_engine.device = 'cpu'
    mock_engine.model.return_value = torch.zeros((10, 1))

    endgame_move = {'row': 7, 'col': 10, 'dir': 'Across', 'word': 'WIN'}
    mock_engine.move_gen.generate.return_value = [endgame_move]

    searcher = AlphableSearch(
        inference_engine=mock_engine,
        mode='lookahead',
    )

    board = [['.' for _ in range(15)] for _ in range(15)]
    rack = ['W', 'I', 'N']

    # When bag_remaining == 0, searcher must delegate to endgame solver
    best_move, value = searcher.find_best_move(board, rack, score_diff=5, bag_remaining=0)
    assert best_move is not None
    assert best_move['word'] == 'WIN'


def test_endgame_7_tile_fast_solve():
    import time
    mock_engine = MagicMock()
    solver = ExactEndgameSolver(mock_engine, branch_limit=5)

    board = [['.' for _ in range(15)] for _ in range(15)]
    my_rack = list("CDEELSU")
    opp_rack = list("AENORTT")

    # Generate 500 simulated moves to stress test branch bounding
    fake_moves = [
        {'row': (i % 15), 'col': (i % 12), 'dir': 'Across', 'word': 'AT'}
        for i in range(500)
    ]
    mock_engine.move_gen.generate.return_value = fake_moves

    t0 = time.time()
    best_move, best_margin = solver.solve(board, my_rack, opp_rack, score_diff=0, max_depth=4)
    dt = time.time() - t0

    assert best_move is not None
    # Must solve in under 1.0 second even with 500 generated moves per ply
    assert dt < 1.0, f"Endgame solver was too slow: {dt:.3f}s"
