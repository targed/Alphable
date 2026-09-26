import pytest
from alphable.core import simulator, inference
from alphable.core.search import AlphableSearch

def test_crn_sampling_consistency():
    engine = inference.AlphableInference(
        dict_path="resources/CSW24.txt",
        value_weight=25.0,
        state_vector_size=36
    )
    search = AlphableSearch(
        engine,
        num_simulations=10,
        top_k_candidates=5,
        mode="lookahead",
        enable_2ply=False,
    )
    board = simulator.create_empty_board()
    
    # Test that find_best_move runs with CRN sampled racks without errors
    # and consistently evaluates candidate moves against the sampled distribution
    rack = list("??AEINO")
    best_move, best_val = search.find_best_move(board, rack, 0, 86)
    
    assert best_move is not None
    # With duplicate blank diminishing returns, opening move should be a 7-letter bingo
    assert len(best_move["word"]) == 7
    _, pts, nr = simulator.simulate_move(board, best_move, rack)
    assert pts >= 50
    assert len(nr) == 0
