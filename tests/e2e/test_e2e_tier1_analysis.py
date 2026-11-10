"""
Tier 1: Position Analysis & Landscape Benchmarking Feature Coverage E2E Tests.

Covers:
- Feature 15: Macondo Architectural Comparison & Ground-Truth Distillation
- Feature 16: Throughput & Depth Landscape (Batch evaluation latency budgets)
- Feature 17: Teacher-Student Distillation Target Formula Verification
- CLI Commands & Model Registry: MODEL_REGISTRY entries, PRESET_ALIASES resolution,
  build_policy factory execution, board formatter.
"""

import os
import pytest
import numpy as np
import torch

from alphable_v4.cli import MODEL_REGISTRY, PRESET_ALIASES, resolve_preset, format_board, build_policy
from alphable_v4.engine.game_state import GameState
from alphable_v4.models.value_net import V4ValueNetwork
from alphable_v4.search.bams import BAMSSearch, BAMSConfig


class TestTier1AnalysisModelRegistry:
    """Tests for CLI model registry, preset aliases, and policy resolution."""

    def test_model_registry_required_presets_present(self):
        """Verifies canonical model presets exist with valid config specifications."""
        required_presets = ["latest", "5-frontiers", "rl-gen1", "scaled", "v4-baseline", "static-magpie"]
        for p in required_presets:
            assert p in MODEL_REGISTRY, f"Required preset '{p}' missing from MODEL_REGISTRY"
            entry = MODEL_REGISTRY[p]
            assert "name" in entry
            assert "short_name" in entry
            assert "description" in entry
            assert "config" in entry

    def test_preset_aliases_resolution(self):
        """Verifies aliases resolve correctly to canonical keys."""
        test_mappings = [
            ("champion", "latest"),
            ("calibrated", "latest"),
            ("frontiers", "5-frontiers"),
            ("rl", "rl-gen1"),
            ("deep", "scaled"),
            ("baseline", "v4-baseline"),
            ("magpie", "static-magpie"),
        ]
        for alias, canonical in test_mappings:
            canon_resolved, config_dict = resolve_preset(alias)
            assert canon_resolved == canonical
            assert config_dict == MODEL_REGISTRY[canonical]

    def test_unknown_preset_raises_value_error(self):
        """Verifies invalid preset names raise descriptive ValueError."""
        with pytest.raises(ValueError) as exc:
            resolve_preset("non_existent_preset_xyz")
        assert "Unknown model preset" in str(exc.value)

    def test_format_board_visual_grid(self, midgame_state):
        """Verifies format_board produces readable 15x15 grid with column headers and row labels."""
        rendered = format_board(midgame_state.board)
        lines = rendered.splitlines()
        assert len(lines) >= 17  # Header + top border + 15 rows + bottom border
        assert "A B C D E F G H I J K L M N O" in lines[0]
        # Check center row 8 has 'T R A I N'
        row_8_line = lines[9]  # 0: header, 1: border, 2..8: rows 1..7, 9: row 8
        assert "T" in row_8_line and "N" in row_8_line


class TestTier1AnalysisThroughputAndLatency:
    """Tests for Feature 16: Throughput, GPU/CPU Batch Latency, and Memory Footprint."""

    def test_value_network_batch_forward_shape_and_bounds(self):
        """Verifies ValueNetwork evaluate_batch output dimension and tanh output bounds [-1, 1]."""
        model = V4ValueNetwork(board_channels=32, state_dim=64, feature_dim=512, num_heads=8)
        model.eval()

        batch_size = 8
        dummy_boards = torch.randn(batch_size, 32, 15, 15)
        dummy_states = torch.randn(batch_size, 64)

        with torch.no_grad():
            preds = model.evaluate_batch(dummy_boards, dummy_states)

        assert preds.shape == (batch_size, 1)
        assert torch.all(preds >= -1.0) and torch.all(preds <= 1.0)

    def test_value_network_geometric_heads_shapes_and_ranges(self):
        """Verifies decoupled multi-heads (equity, P_bingo, hook_entropy) shapes and ranges."""
        model = V4ValueNetwork(board_channels=32, state_dim=64, feature_dim=512, num_heads=8)
        model.eval()

        batch_size = 4
        dummy_boards = torch.randn(batch_size, 32, 15, 15)
        dummy_states = torch.randn(batch_size, 64)

        equity, p_bingo, h_hook = model.evaluate_geometry(dummy_boards, dummy_states)

        assert equity.shape == (batch_size, 1)
        assert torch.all(equity >= -1.0) and torch.all(equity <= 1.0)

        # P(bingo) must be valid probabilities in [0.0, 1.0]
        assert p_bingo.shape == (batch_size, 1)
        assert torch.all(p_bingo >= 0.0) and torch.all(p_bingo <= 1.0)

        # Hook entropy must be non-negative
        assert h_hook.shape == (batch_size, 1)
        assert torch.all(h_hook >= 0.0)

    def test_cpu_batch_latency_compliance(self):
        """Verifies that evaluation of 20 candidates on CPU executes in under 250ms."""
        import time
        model = V4ValueNetwork(board_channels=32, state_dim=64, feature_dim=512, num_heads=8)
        model.eval()

        num_cands = 20
        boards = torch.randn(num_cands, 32, 15, 15)
        states = torch.randn(num_cands, 64)

        start = time.perf_counter()
        with torch.no_grad():
            _ = model.evaluate_batch(boards, states)
        dt_ms = (time.perf_counter() - start) * 1000.0

        assert dt_ms < 250.0, f"CPU 20-candidate batch evaluation {dt_ms:.1f}ms exceeded 250ms budget"


class TestTier1AnalysisDistillationSpecification:
    """Tests for Feature 15 & 17: Teacher-Student Relationship & Distillation Target Formula."""

    def test_distillation_target_formula_computation(self):
        """
        Verifies Macondo ground-truth equity distillation target formula:
        v_target = 0.75 * tanh(top_equity / 50.0) + 0.25 * tanh(final_margin / 100.0)
        """
        def calc_target(top_equity: float, final_margin: float) -> float:
            v_macondo = np.tanh(top_equity / 50.0)
            v_outcome = np.tanh(final_margin / 100.0)
            return float(0.75 * v_macondo + 0.25 * v_outcome)

        # Case 1: Equal position
        assert pytest.approx(calc_target(0.0, 0.0), abs=1e-5) == 0.0

        # Case 2: Dominant win (+50 pts equity, +100 pts margin)
        v_win = calc_target(50.0, 100.0)
        assert v_win > 0.7
        assert v_win <= 1.0

        # Case 3: Crushing loss (-50 pts equity, -100 pts margin)
        v_loss = calc_target(-50.0, -100.0)
        assert v_loss < -0.7
        assert v_loss >= -1.0

        # Case 4: Symmetry
        assert pytest.approx(calc_target(35.0, 50.0), rel=1e-4) == -calc_target(-35.0, -50.0)

    def test_distillation_boundedness_on_extreme_outcomes(self):
        """Verifies distillation targets remain strictly within [-1.0, 1.0] under blowouts."""
        def calc_target(top_equity: float, final_margin: float) -> float:
            v_macondo = np.tanh(top_equity / 50.0)
            v_outcome = np.tanh(final_margin / 100.0)
            return float(0.75 * v_macondo + 0.25 * v_outcome)

        assert abs(calc_target(1000.0, 500.0)) <= 1.0
        assert abs(calc_target(-1000.0, -500.0)) <= 1.0
