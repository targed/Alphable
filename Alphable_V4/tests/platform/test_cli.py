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
