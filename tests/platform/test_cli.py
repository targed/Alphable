"""
Unit tests for Alphable V4 Command Center, Model Presets, and Policy Resolution.
"""

import io
import os
import sys
import pytest
from unittest.mock import patch

from alphable_v4.cli import (
    MODEL_REGISTRY,
    PRESET_ALIASES,
    resolve_preset,
    build_policy,
    cmd_models,
    get_shared_engine,
)
from alphable_v4.engine.game_state import GameState


def test_preset_registry_completeness():
    expected_presets = {"latest", "5-frontiers", "rl-gen1", "scaled", "v4-baseline", "static-magpie"}
    assert expected_presets.issubset(set(MODEL_REGISTRY.keys()))

    for key, info in MODEL_REGISTRY.items():
        assert "name" in info
        assert "short_name" in info
        assert "description" in info
        assert "status" in info


def test_preset_alias_resolution():
    assert resolve_preset("champion")[0] == "latest"
    assert resolve_preset("calibrated")[0] == "latest"
    assert resolve_preset("frontiers")[0] == "5-frontiers"
    assert resolve_preset("v5-frontier-v4")[0] == "5-frontiers"
    assert resolve_preset("frontier-v4")[0] == "5-frontiers"
    assert resolve_preset("rl")[0] == "rl-gen1"
    assert resolve_preset("self-play")[0] == "rl-gen1"
    assert resolve_preset("deep")[0] == "scaled"
    assert resolve_preset("deep-scaled")[0] == "scaled"
    assert resolve_preset("baseline")[0] == "v4-baseline"
    assert resolve_preset("magpie")[0] == "static-magpie"

    with pytest.raises(ValueError, match="Unknown model preset"):
        resolve_preset("non_existent_model_xyz")


def test_build_magpie_policy():
    engine = get_shared_engine("CSW24")
    policy_fn, full_name, short_name = build_policy(engine, spec="magpie")
    assert short_name == "Base-MAGPIE"
    assert "Base MAGPIE" in full_name

    state = GameState(board=[[None]*15 for _ in range(15)], rack=["A", "B", "C", "D", "E", "F", "G"], lexicon="CSW24")
    move, meta = policy_fn(state)
    assert move is not None
    assert meta.get("method") == "magpie_static_top"


def test_build_magpie_pat_and_tuned_policies():
    engine = get_shared_engine("CSW24")

    # PAT Policy
    pol_pat, name_pat, short_pat = build_policy(engine, spec="magpie-pat")
    assert short_pat == "MAGPIE-PAT"
    assert "PAT" in name_pat

    state = GameState(board=[[None]*15 for _ in range(15)], rack=list("RETINAS"), lexicon="CSW24")
    m_pat, meta_pat = pol_pat(state)
    assert m_pat is not None
    assert meta_pat.get("method") == "magpie_pat_top"

    # Tuned Policy
    pol_tuned, name_tuned, short_tuned = build_policy(engine, spec="magpie-tuned")
    assert short_tuned == "MAGPIE-Tuned"
    assert "Maximally Tuned" in name_tuned

    m_tuned, meta_tuned = pol_tuned(state)
    assert m_tuned is not None
    assert meta_tuned.get("method") in ("magpie_sim_top", "magpie_pat_top", "magpie_endgame_solve")

    # V4-PAT Policy
    pol_v4pat, name_v4pat, short_v4pat = build_policy(engine, spec="v4-pat")
    assert short_v4pat == "V4-Champion-PAT"
    assert callable(pol_v4pat)



def test_build_bams_presets():
    engine = get_shared_engine("CSW24")

    # Test latest champion
    pol_latest, name_latest, short_latest = build_policy(engine, spec="latest")
    assert short_latest == "V4-Champion"
    assert callable(pol_latest)

    # Test 5-frontiers champion
    pol_frontiers, name_frontiers, short_frontiers = build_policy(engine, spec="5-frontiers")
    assert short_frontiers == "5-Frontiers"
    assert callable(pol_frontiers)

    # Test rl-gen1
    pol_rl, name_rl, short_rl = build_policy(engine, spec="rl-gen1")
    assert short_rl == "RL-Gen1"
    assert callable(pol_rl)


def test_cmd_models_output():
    buf = io.StringIO()
    with patch("sys.stdout", buf):
        cmd_models(None)
    output = buf.getvalue()
    assert "ALPHABLE V4: NEURAL CHECKPOINTS & SEARCH PRESETS CATALOG" in output
    assert "• PRESET: 'latest'" in output
    assert "• PRESET: '5-frontiers'" in output
    assert "• PRESET: 'rl-gen1'" in output
    assert "• PRESET: 'scaled'" in output
    assert "• PRESET: 'v4-baseline'" in output


def test_cmd_history_ledger():
    from alphable_v4.cli import cmd_history
    import argparse

    args = argparse.Namespace(show=None, compare=None, tag=None, model=None, limit=25)
    buf = io.StringIO()
    with patch("sys.stdout", buf):
        cmd_history(args)
    output = buf.getvalue()

    assert "ALPHABLE V4 TOURNAMENT BENCHMARK HISTORY LEDGER" in output
    assert "V4-Baseline vs Base-MAGPIE" in output
    assert "5-Frontiers vs Base-MAGPIE" in output
    assert "V4-Champion vs Base-MAGPIE" in output
    assert "3000g-duplicate-championship" in output


def test_cmd_history_show_and_compare():
    from alphable_v4.cli import cmd_history
    import argparse

    # Test show
    args_show = argparse.Namespace(show="run_20261015_215837", compare=None, tag=None, model=None, limit=25)
    buf = io.StringIO()
    with patch("sys.stdout", buf):
        cmd_history(args_show)
    output_show = buf.getvalue()
    assert "TOURNAMENT RUN DETAILS: run_20261015_215837" in output_show
    assert "Duplicate (Pair-Swapped, Zero Luck)" in output_show
    assert "806W - 664L - 30D" in output_show

    # Test compare
    args_comp = argparse.Namespace(
        show=None,
        compare=["run_20261013_143000", "run_20261015_215837"],
        tag=None,
        model=None,
        limit=25,
    )
    buf_comp = io.StringIO()
    with patch("sys.stdout", buf_comp):
        cmd_history(args_comp)
    output_comp = buf_comp.getvalue()
    assert "HEAD-TO-HEAD BENCHMARK RUN COMPARISON" in output_comp
    assert "Delta (B - A)" in output_comp
    assert "+0.5%" in output_comp

