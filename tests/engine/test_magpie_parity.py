"""
Parity and Performance Verification Suite for MAGPIE Engine.

Verifies:
1. Legal move generation on diverse board positions
2. Static equity calculation and leave values
3. Lexicon switching (CSW24 <-> NWL23)
4. Sub-5ms move generation performance
5. Parity with Alphable V3 GADDAG on known test positions
"""

import time
import pytest
from alphable.engine.game_state import GameState
from alphable.engine.magpie_bindings import MagpieEngine
from alphable.engine.move import Move


# 10 Known Test Positions (FEN/CGP board strings + rack)
TEST_POSITIONS = [
    # 1. Standard Opening
    {
        "name": "Opening_AEINRST",
        "board": "15/15/15/15/15/15/15/15/15/15/15/15/15/15/15",
        "rack": "AEINRST",
        "min_moves": 50,
        "expect_bingo": True,
    },
    # 2. Opening with Blanks
    {
        "name": "Opening_Blank_STARE",
        "board": "15/15/15/15/15/15/15/15/15/15/15/15/15/15/15",
        "rack": "?STARED",
        "min_moves": 100,
        "expect_bingo": True,
    },
    # 3. First Turn Played (TRAIN across center)
    {
        "name": "Midgame_Center_TRAIN",
        "board": "15/15/15/15/15/15/15/7TRAIN3/15/15/15/15/15/15/15",
        "rack": "CABINET",
        "min_moves": 20,
        "expect_bingo": False,
    },
    # 4. Open Board with High Hook Potential
    {
        "name": "Midgame_QUIZ_Hook",
        "board": "15/15/15/15/15/15/15/7QUIZ4/15/15/15/15/15/15/15",
        "rack": "BEASTLY",
        "min_moves": 15,
        "expect_bingo": False,
    },
    # 5. Heavy Vowel Rack
    {
        "name": "Vowel_Heavy_AEIOUAE",
        "board": "15/15/15/15/15/15/15/7TRAIN3/15/15/15/15/15/15/15",
        "rack": "AEIOUAE",
        "min_moves": 5,
        "expect_bingo": False,
    },
    # 6. High Point Tiles (Q, Z, X, J, K)
    {
        "name": "Power_Tiles_QZXJKAE",
        "board": "15/15/15/15/15/15/15/7TRAIN3/15/15/15/15/15/15/15",
        "rack": "QZXJKAE",
        "min_moves": 10,
        "expect_bingo": False,
    },
    # 7. Clustered Multi-Word Board
    {
        "name": "Clustered_Midgame",
        "board": "15/15/15/15/15/15/7CAT5/7O7/7DOG5/15/15/15/15/15/15",
        "rack": "RETINAS",
        "min_moves": 20,
        "expect_bingo": True,
    },
    # 8. Tight Defense Board (Edge play)
    {
        "name": "Edge_Play_Defense",
        "board": "15/15/15/15/15/15/15/1B13/1A13/1T13/15/15/15/15/15",
        "rack": "WINDING",
        "min_moves": 10,
        "expect_bingo": False,
    },
    # 9. Pre-Endgame (Small unseen tile count)
    {
        "name": "Pre_Endgame",
        "board": "15/15/15/15/15/15/15/7PLAY4/15/15/15/15/15/15/15",
        "rack": "ABCDEFG",
        "min_moves": 10,
        "expect_bingo": False,
    },
    # 10. Blank on Board (Lowercase 'a')
    {
        "name": "Blank_On_Board",
        "board": "15/15/15/15/15/15/15/7aNT5/15/15/15/15/15/15/15",
        "rack": "HOUNDED",
        "min_moves": 10,
        "expect_bingo": False,
    },
]


@pytest.fixture(scope="module")
def engine():
    """Initializes a shared MagpieEngine instance for the test suite."""
    eng = MagpieEngine(lexicon="CSW24")
    yield eng
    eng.close()


def test_engine_initialization(engine):
    """Verifies that MAGPIE engine loads properly and reports no errors."""
    assert engine is not None
    assert engine._handle is not None


def test_lexicon_switching(engine):
    """Verifies that switching between CSW24 and NWL23 works seamlessly without errors."""
    # Test setting CSW24
    engine.set_lexicon("CSW24")
    assert engine.lexicon == "CSW24"

    # Test setting NWL23
    engine.set_lexicon("NWL23")
    assert engine.lexicon == "NWL23"

    # Switch back to CSW24
    engine.set_lexicon("CSW24")
    assert engine.lexicon == "CSW24"


def test_opening_move_generation(engine):
    """Verifies legal move generation on opening board with rack AQRTUYZ."""
    engine.set_lexicon("CSW24")
    moves = engine.generate_moves(
        cgp="15/15/15/15/15/15/15/15/15/15/15/15/15/15/15 AQRTUYZ/ 0/0 0"
    )
    assert len(moves) > 0, "Opening board should produce legal moves"

    top_move = moves[0]
    assert top_move.score > 0
    assert top_move.direction in ("Across", "Down")
    assert top_move.word != ""
    assert isinstance(top_move.equity, float)

    # Moves must be sorted by equity descending
    for i in range(len(moves) - 1):
        assert moves[i].equity >= moves[i + 1].equity - 1e-4


@pytest.mark.parametrize("pos", TEST_POSITIONS, ids=[p["name"] for p in TEST_POSITIONS])
def test_all_10_positions(engine, pos):
    """Tests move generation across all 10 diverse benchmark positions."""
    engine.set_lexicon("CSW24")
    cgp_str = f"{pos['board']} {pos['rack']}/ 0/0 0"

    t0 = time.perf_counter()
    moves = engine.generate_moves(cgp=cgp_str)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert len(moves) >= pos["min_moves"], (
        f"Position {pos['name']} expected at least {pos['min_moves']} moves, got {len(moves)}"
    )

    top_move = moves[0]
    assert (
        top_move.score > 0 or top_move.is_exchange
    ), f"Top move in {pos['name']} must score points or exchange"
    assert top_move.word != "", f"Top move in {pos['name']} must have a word"

    # Verify bingo detection if expected
    if pos["expect_bingo"]:
        bingos = [m for m in moves if len(m.word) == 7 and m.score >= 50]
        assert len(bingos) > 0, f"Expected bingo in {pos['name']}"


def test_performance_sub_5ms(engine):
    """
    Measures move generation latency across 20 iterations.
    Success gate: mean latency must be <= 5ms per move generation.
    """
    engine.set_lexicon("CSW24")
    cgp_str = "15/15/15/15/15/15/15/7TRAIN3/15/15/15/15/15/15/15 CABINET/ 0/0 0"

    # Warmup
    engine.generate_moves(cgp=cgp_str)

    times = []
    for _ in range(20):
        t0 = time.perf_counter()
        moves = engine.generate_moves(cgp=cgp_str)
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)

    mean_ms = sum(times) / len(times)
    min_ms = min(times)
    print(f"\n[PERFORMANCE] MAGPIE Move Generation: Mean={mean_ms:.3f}ms, Min={min_ms:.3f}ms")

    assert mean_ms <= 5.0, f"Move generation too slow: {mean_ms:.2f}ms > 5.0ms target"


def test_best_reply(engine):
    """Verifies best_reply calculates the opponent's best response."""
    state = GameState(
        rack=["A", "E", "I", "N", "R", "S", "T"],
        score=0,
        opp_score=0,
    )
    reply = engine.best_reply(state, opp_rack="CABINET")
    assert reply is not None
    assert reply.score > 0
    assert reply.word != ""


def test_direct_v3_gaddag_parity(engine):
    """
    Direct 1:1 parity test against Alphable V3 GADDAG move generator.
    Verifies that the legal word set generated by MAGPIE exactly matches V3.
    """
    import os
    import sys
    v3_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Alphable_V3/src"))
    dict_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Alphable_V3/resources/CSW24.txt"))
    if not os.path.exists(dict_path) or not os.path.exists(v3_src):
        pytest.skip("V3 source or CSW24.txt not found for parity check")

    sys.path.insert(0, v3_src)
    from alphable.core import structure

    g = structure.Gaddag.load(dict_path)
    v3_gen = structure.MoveGenerator(g)

    board = [["." for _ in range(15)] for _ in range(15)]
    rack = list("AQRTUYZ")
    v3_moves = v3_gen.generate(board, rack)
    v3_words = set(m["word"] for m in v3_moves)

    engine.set_lexicon("CSW24")
    cgp_str = "15/15/15/15/15/15/15/15/15/15/15/15/15/15/15 AQRTUYZ/ 0/0 0"
    magpie_moves = engine.generate_moves(cgp=cgp_str, max_candidates=2000)
    magpie_words = set(m.word for m in magpie_moves if m.is_placement)

    # V3 and V4 keep cuDNN disabled for Blackwell RTX 50-series stability
    try:
        import torch
        torch.backends.cudnn.enabled = False
    except ImportError:
        pass

    assert v3_words == magpie_words, (
        f"Mismatch: V3-only: {v3_words - magpie_words}, MAGPIE-only: {magpie_words - v3_words}"
    )


def test_magpie_pat_differentiation(engine):
    """Verifies that enabling PAT differentiates static equities and alters candidate ranking."""
    engine.set_lexicon("CSW24")
    engine.set_pat(None)
    cgp_opening = "15/15/15/15/15/15/15/15/15/15/15/15/15/15/15 RETINAS/ 0/0 0"
    moves_no_pat = engine.generate_moves(cgp=cgp_opening, max_candidates=5)

    # Enable PAT
    engine.set_pat("CSW24")
    moves_pat = engine.generate_moves(cgp=cgp_opening, max_candidates=5)

    # Clean up state
    engine.set_pat(None)

    assert len(moves_no_pat) > 0
    assert len(moves_pat) > 0

    # Without PAT, all 7-letter anagrams on an empty board have identical 66.0 equity
    equities_no_pat = [m.equity for m in moves_no_pat]
    assert all(eq == 66.0 for eq in equities_no_pat)

    # With PAT, positional term differentiates candidate equities
    equities_pat = [m.equity for m in moves_pat]
    assert len(set(equities_pat)) > 1, "PAT should differentiate candidate equities"
    assert moves_pat[0].coord_str == "8D", "Top PAT move on RETINAS should be centered at 8D"


def test_magpie_simulation_execution(engine):
    """Verifies that MAGPIE Monte Carlo simulation (PIMC) runs rollouts."""
    engine.set_lexicon("CSW24")
    cgp_opening = "15/15/15/15/15/15/15/15/15/15/15/15/15/15/15 RETINAS/ 0/0 0"
    engine.set_cgp(cgp_opening)
    engine.generate_moves(max_candidates=5)
    sim_out = engine.simulate(iterations=50)

    assert sim_out is not None
    assert len(sim_out) > 0
    assert "8B" in sim_out or "8C" in sim_out or "8D" in sim_out
    assert "Showing" in sim_out or "1:" in sim_out


