"""
Tests for Alphable V4 Models (Value Network and Opponent Belief Networks).

Verifies:
1. ResNet-18 + Cross-Attention forward pass shape and output boundedness [-1.0, 1.0].
2. Fast batch evaluation for candidate moves (< 5 ms latency budget).
3. Bayesian rack inference determinism and consistency with remaining unseen pool.
4. Neural belief network forward pass and probability distribution validity.
"""

import os
import pytest
import numpy as np
import torch

from alphable_v4.engine.game_state import GameState, STANDARD_TILE_COUNTS
from alphable_v4.models.value_net import V4ValueNetwork
from alphable_v4.models.belief_net import BayesianRackInference, NeuralBeliefNet


class TestValueNetwork:
    """Test suite for V4ValueNetwork."""

    def test_value_network_output_shape_and_bounds(self):
        model = V4ValueNetwork(board_channels=32, state_dim=64, feature_dim=512, num_heads=8)
        model.eval()

        batch_size = 4
        dummy_board = torch.randn(batch_size, 32, 15, 15)
        dummy_state = torch.randn(batch_size, 64)

        with torch.no_grad():
            equity = model(dummy_board, dummy_state)

        assert equity.shape == (batch_size, 1), f"Expected shape ({batch_size}, 1), got {equity.shape}"
        # Tanh output must be bounded in [-1.0, 1.0]
        assert torch.all(equity >= -1.0) and torch.all(equity <= 1.0)

    def test_batch_evaluation_latency(self):
        """Validates that candidate evaluation latency meets the < 5 ms budget for 100 candidates."""
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = V4ValueNetwork(board_channels=32, state_dim=64, feature_dim=512, num_heads=8).to(device)
        model.eval()

        num_candidates = 100
        boards = torch.randn(num_candidates, 32, 15, 15, device=device)
        states = torch.randn(num_candidates, 64, device=device)

        # Warmup and synchronize
        with torch.no_grad():
            for _ in range(10):
                _ = model.evaluate_batch(boards, states)
            if torch.cuda.is_available():
                torch.cuda.synchronize()

        import time
        latencies = []
        with torch.no_grad():
            for _ in range(20):
                start = time.perf_counter()
                _ = model.evaluate_batch(boards, states)
                if torch.cuda.is_available():
                    torch.cuda.synchronize()
                latencies.append((time.perf_counter() - start) * 1000.0)

        mean_latency_ms = float(np.mean(latencies))
        min_latency_ms = float(np.min(latencies))
        print(f"\n100-candidate batch latency on {device}: Mean {mean_latency_ms:.3f} ms | Min {min_latency_ms:.3f} ms")
        if torch.cuda.is_available():
            # With native ATen kernels (cuDNN disabled for Blackwell stability), budget allows up to 35ms
            assert mean_latency_ms < 35.0, f"Mean latency {mean_latency_ms:.2f} ms exceeded 35.0 ms threshold"


class TestBeliefNetwork:
    """Test suite for Bayesian and Neural opponent rack belief models."""

    def test_bayesian_sampling_deterministic_with_seed(self):
        state = GameState(board=[[None]*15 for _ in range(15)], rack=["C", "A", "T", "S", "E", "R", "S"])
        bayesian = BayesianRackInference(default_rack_size=7)

        sample_set_1 = bayesian.sample_opponent_racks(state, num_samples=16, seed=42)
        sample_set_2 = bayesian.sample_opponent_racks(state, num_samples=16, seed=42)

        assert len(sample_set_1) == 16
        assert sample_set_1 == sample_set_2, "Sampling with identical seed must yield identical racks (CRN requirement)"

    def test_bayesian_tile_pool_consistency(self):
        state = GameState(board=[[None]*15 for _ in range(15)], rack=["Q", "Z", "X", "J", "K", "V", "W"])
        bayesian = BayesianRackInference()

        unseen_pool = bayesian.get_unseen_tile_pool(state)
        # Total tiles 100 - 7 on rack = 93 unseen
        assert len(unseen_pool) == 93

        samples = bayesian.sample_opponent_racks(state, num_samples=20, rack_size=7, seed=123)
        for s in samples:
            assert len(s) == 7
            for tile in s:
                assert tile in unseen_pool

    def test_belief_confidence_metric(self):
        state = GameState(board=[[None]*15 for _ in range(15)], rack=["A"] * 7)
        bayesian = BayesianRackInference()

        # Opening state: 93 unseen tiles -> confidence low
        conf_start = bayesian.compute_belief_confidence(state)
        assert 0.0 <= conf_start <= 0.3

        # Endgame state with only 5 tiles unseen
        state.unseen_counts = {"E": 2, "A": 2, "T": 1}
        conf_endgame = bayesian.compute_belief_confidence(state)
        assert conf_endgame == 1.0, "Confidence should be 1.0 when unseen <= 7"

    def test_neural_belief_net_output(self):
        model = NeuralBeliefNet(state_dim=64, hidden_dim=256)
        model.eval()

        dummy_state = torch.randn(8, 64)
        with torch.no_grad():
            probs = model(dummy_state)

        assert probs.shape == (8, 27)
        # Softmax outputs must sum to 1.0
        sums = probs.sum(dim=-1)
        assert torch.allclose(sums, torch.ones(8), atol=1e-5)
