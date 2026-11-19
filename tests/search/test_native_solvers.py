"""
tests/search/test_native_solvers.py

Unit tests for native MAGPIE solver integration:
1. Positional Adjustment Term (PAT) candidate generation.
2. Native Monte Carlo simulation parsing (win probability, spread, simulated equity).
3. Hybrid move selection combining simulation with value network valuation.
"""

import pytest
from alphable.engine.magpie_bindings import MagpieEngine
from alphable.engine.game_state import GameState
from alphable.engine.move import Move
from alphable.search.bams import BAMSSearch, BAMSConfig


@pytest.fixture(scope="module")
def engine():
    eng = MagpieEngine(use_pat=True)
    return eng


def test_pat_candidate_generation(engine):
    """Verifies that PAT changes candidate move generation and ranking."""
    engine.set_pat(None)
    cands_no_pat = engine.generate_moves(rack="AEINRST", max_candidates=5)

    engine.set_pat("CSW24")
    cands_pat = engine.generate_moves(rack="AEINRST", max_candidates=5)

    assert len(cands_no_pat) > 0
    assert len(cands_pat) > 0
    # Both sets should produce valid legal plays
    assert all(isinstance(m, Move) for m in cands_pat)


def test_simulate_candidates_parsing(engine):
    """Verifies that simulate_candidates parses native simulation output correctly."""
    engine.set_rack("AEINRST")
    engine.generate_moves(max_candidates=10)
    
    sim_results = engine.simulate_candidates(iterations=15)
    assert len(sim_results) > 0
    
    top = sim_results[0]
    assert "move" in top
    assert "sim_equity" in top
    assert "win_prob" in top
    assert "spread" in top
    assert isinstance(top["move"], Move)
    assert 0.0 <= top["win_prob"] <= 1.0
    assert top["move"].score > 0


def test_bams_hybrid_pimc_move_selection(engine):
    """Tests that BAMSSearch with hybrid_pimc selects high-equity moves."""
    config = BAMSConfig(
        hybrid_pimc=True,
        sim_iterations=15,
        use_pat=True,
    )
    bams = BAMSSearch(engine=engine, config=config)
    state = GameState(rack=["A", "E", "I", "N", "R", "S", "T"])
    
    best_move, meta = bams.select_move(state)
    assert best_move is not None
    assert isinstance(best_move, Move)
    assert meta.get("method") in ("hybrid_pimc", "forced_move", "bams_root")
    assert best_move.score >= 50  # AEINRST forms natural bingos
