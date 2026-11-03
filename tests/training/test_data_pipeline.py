"""
Unit tests for Alphable V4 data collection, GCG parsing, and distillation pipeline.
"""

import os
import tempfile
import pytest
import numpy as np
import torch

from alphable_v4.training.parse_gcg import parse_gcg_text, parse_gcg_coordinate, parse_gcg_file
from alphable_v4.training.macondo_distill import extract_match_distillation_samples
from alphable_v4.training.build_belief_dataset import extract_game_belief_samples


SAMPLE_GCG_TEXT = """#character-encoding UTF-8
#description Created with Macondo
#id io.woogles testgame123
#lexicon CSW24
#player1 Alice Alice
#player2 Bob Bob
>Alice: BNNOOQU 8F NOOB +12 12
>Bob: ACEIOTW 9E TAWIE +31 31
>Alice: ?ACIOSX 11E COAX +40 52
>Bob: ABCDEFG -ABC +0 31
>Alice: ?ACIOSX - +0 52
>Bob: (D) +4 35
"""


def test_parse_gcg_coordinate():
    # Across
    r, c, d = parse_gcg_coordinate("8H")
    assert r == 7
    assert c == 7
    assert d == "Across"

    r, c, d = parse_gcg_coordinate("1A")
    assert r == 0
    assert c == 0
    assert d == "Across"

    # Down
    r, c, d = parse_gcg_coordinate("H8")
    assert r == 7
    assert c == 7
    assert d == "Down"

    r, c, d = parse_gcg_coordinate("A15")
    assert r == 14
    assert c == 0
    assert d == "Down"

    # Pass & Exchange
    r, c, d = parse_gcg_coordinate("-")
    assert r is None and c is None and d is None


def test_parse_gcg_text():
    game = parse_gcg_text(SAMPLE_GCG_TEXT, game_id="testgame123")
    assert game is not None
    assert game.game_id == "testgame123"
    assert game.lexicon == "CSW24"
    assert game.player1 == "Alice"
    assert game.player2 == "Bob"
    assert len(game.turns) == 5

    # Turn 0: Alice plays NOOB
    t0 = game.turns[0]
    assert t0.player == "Alice"
    assert t0.word == "NOOB"
    assert t0.points == 12
    assert not t0.is_pass
    assert not t0.is_exchange

    # Turn 3: Bob exchanges -ABC
    t3 = game.turns[3]
    assert t3.player == "Bob"
    assert t3.is_exchange
    assert t3.exchanged_tiles == "ABC"

    # Turn 4: Alice passes
    t4 = game.turns[4]
    assert t4.player == "Alice"
    assert t4.is_pass


def test_real_match_extraction():
    match_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../Alphable_V3/data/woogles/matches/match_20260924_001412_aaa556goku")
    )
    if not os.path.exists(match_dir):
        pytest.skip("Test match directory not available")

    samples = extract_match_distillation_samples(match_dir)
    assert len(samples) > 0

    s0 = samples[0]
    assert s0["board_tensor"].shape == (32, 15, 15)
    assert s0["state_vector"].shape == (64,)
    assert isinstance(s0["target"], float)
    assert -1.0 <= s0["target"] <= 1.0


def test_belief_samples_extraction():
    game = parse_gcg_text(SAMPLE_GCG_TEXT, game_id="testgame123")
    samples = extract_game_belief_samples(game)
    assert len(samples) > 0

    s0 = samples[0]
    assert s0["board_tensor"].shape == (32, 15, 15)
    assert s0["state_vector"].shape == (64,)
    assert s0["opp_rack_target"].shape == (27,)

    # Total tiles in target rack should be positive
    assert s0["opp_rack_target"].sum() > 0


def test_hyperparameter_evaluation_function():
    """Verifies Frontier 5 hyperparameter evaluator runs duplicate match test cleanly."""
    from alphable_v4.training.optimize_hyperparams import evaluate_hyperparams
    from alphable_v4.engine.magpie_bindings import MagpieEngine

    engine = MagpieEngine(lexicon="CSW24")
    ckpt = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "models", "checkpoints", "v4_value_net_best.pt")
    )
    params = {"weight_2ply": 0.18, "opp_penalty_weight": 0.12, "max_static_deficit": 3.5, "value_weight": 4.5}

    res = evaluate_hyperparams(engine, ckpt, params, num_matches=1, base_seed=123)
    assert res["matches_played"] == 1
    assert res["total_games"] == 2
    assert "win_rate" in res
    assert "net_spread" in res
    assert isinstance(res["mean_bams_score"], float)
    assert isinstance(res["mean_magpie_score"], float)
