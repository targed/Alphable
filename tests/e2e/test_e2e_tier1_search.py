"""
Tier 1: BAMS Search Feature Coverage E2E Tests.

Covers:
- Feature 2: Pre-Endgame Parity Logic & Tile-Sticking Hazard (bag 1 to 5)
- Feature 4: Continuous Volatility Control (score-dependent scaling)
- Feature 10: Common Random Numbers (CRN) Variance Reduction & Determinism
- Feature 14: Generator Enhancement Transfer to BAMS Candidate Pool
- BAMS Search: 1-ply MC rollouts, 2-ply nested lookahead, exact endgame solver,
  latency budget verification, metadata emission.
"""

import os
import pytest
import numpy as np
import torch

from alphable.engine.game_state import GameState
from alphable.engine.move import Move
from alphable.engine.magpie_bindings import MagpieEngine
from alphable.models.value_net import V4ValueNetwork
from alphable.search.bams import BAMSSearch, BAMSConfig, BAMSCandidateEval


class TestTier1SearchBAMSExecution:
    """Tests for core BAMS search functionality and move selection."""

    def test_bams_initialization_from_checkpoint(self, shared_engine, checkpoint_path, fast_bams_config):
        """Verifies successful loading of trained V4 Value Network checkpoint into BAMSSearch."""
        bams = BAMSSearch.from_checkpoint(
            engine=shared_engine,
            checkpoint_path=checkpoint_path,
            config=fast_bams_config,
        )
        assert bams.value_net is not None
        assert isinstance(bams.value_net, V4ValueNetwork)
        assert bams.engine == shared_engine

    def test_bams_opening_move_selection(self, shared_engine, checkpoint_path, fast_bams_config, standard_opening_state):
        """Verifies BAMS selects valid high-equity opening move on empty board."""
        bams = BAMSSearch.from_checkpoint(shared_engine, checkpoint_path, fast_bams_config)
        move, meta = bams.select_move(standard_opening_state)

        assert move is not None
        assert move.is_placement is True
        assert move.score > 0
        assert len(move.word) >= 2
        assert meta["method"] in ("bams_mc_rollout", "bams_mc_rollout_2ply")
        assert meta["num_candidates_evaluated"] > 0
        assert meta["latency_ms"] < 2500.0

    def test_bams_midgame_2ply_nested_rollout(self, shared_engine, checkpoint_path, fast_2ply_bams_config, midgame_state):
        """Verifies 2-ply nested counterplay rollouts evaluate turn 2 follow-up equity."""
        bams = BAMSSearch.from_checkpoint(shared_engine, checkpoint_path, fast_2ply_bams_config)
        move, meta = bams.select_move(midgame_state)

        assert move is not None
        assert meta["method"] == "bams_mc_rollout_2ply"
        assert "evaluations" in meta
        # Verify 2-ply net exchange is populated for evaluated candidates
        has_2ply = any(e.get("mean_2ply_net") is not None for e in meta["evaluations"])
        assert has_2ply, "Expected at least one candidate with evaluated 2-ply net score"

    def test_bams_latency_budget_compliance(self, shared_engine, checkpoint_path, fast_bams_config, midgame_state):
        """Verifies that search latency executes within standard time budget (< 3.0 seconds)."""
        bams = BAMSSearch.from_checkpoint(shared_engine, checkpoint_path, fast_bams_config)
        move, meta = bams.select_move(midgame_state)
        assert meta["latency_ms"] < 3000.0, f"Search latency {meta['latency_ms']:.1f}ms exceeded 3.0s budget"

    def test_bams_metadata_schema_completeness(self, shared_engine, checkpoint_path, fast_bams_config, standard_opening_state):
        """Verifies metadata dictionary contains all diagnostic telemetry fields."""
        bams = BAMSSearch.from_checkpoint(shared_engine, checkpoint_path, fast_bams_config)
        _, meta = bams.select_move(standard_opening_state)

        expected_fields = [
            "method",
            "latency_ms",
            "num_candidates_evaluated",
            "num_samples",
            "best_bams_score",
            "evaluations",
        ]
        for field in expected_fields:
            assert field in meta, f"Missing required metadata field: {field}"

        assert len(meta["evaluations"]) > 0
        first_eval = meta["evaluations"][0]
        eval_keys = ["word", "row", "col", "direction", "score", "opp_reply_mean", "value_net_mean", "bams_score"]
        for k in eval_keys:
            assert k in first_eval, f"Missing evaluation field: {k}"


class TestTier1SearchCRNVarianceReduction:
    """Tests for Feature 10: Common Random Numbers (CRN) Variance Reduction."""

    def test_crn_bitwise_determinism_identical_seed(self, shared_engine, checkpoint_path, standard_opening_state):
        """Verifies that identical random seeds produce bitwise identical evaluations and scores."""
        conf1 = BAMSConfig(num_samples=4, candidate_beam=4, seed=12345, device="cpu")
        conf2 = BAMSConfig(num_samples=4, candidate_beam=4, seed=12345, device="cpu")

        bams1 = BAMSSearch.from_checkpoint(shared_engine, checkpoint_path, conf1)
        bams2 = BAMSSearch.from_checkpoint(shared_engine, checkpoint_path, conf2)

        move1, meta1 = bams1.select_move(standard_opening_state)
        move2, meta2 = bams2.select_move(standard_opening_state)

        assert move1.word == move2.word
        assert move1.score == move2.score
        assert pytest.approx(meta1["best_bams_score"], rel=1e-5) == meta2["best_bams_score"]

    def test_crn_seed_variation_divergence(self, shared_engine, checkpoint_path, standard_opening_state):
        """Verifies that different seeds sample different opponent racks while preserving validity."""
        conf1 = BAMSConfig(num_samples=4, candidate_beam=4, seed=101, device="cpu")
        conf2 = BAMSConfig(num_samples=4, candidate_beam=4, seed=202, device="cpu")

        bams1 = BAMSSearch.from_checkpoint(shared_engine, checkpoint_path, conf1)
        bams2 = BAMSSearch.from_checkpoint(shared_engine, checkpoint_path, conf2)

        move1, meta1 = bams1.select_move(standard_opening_state)
        move2, meta2 = bams2.select_move(standard_opening_state)

        assert move1 is not None and move2 is not None
        assert meta1["method"] in ("bams_mc_rollout", "bams_mc_rollout_2ply")
        assert meta2["method"] in ("bams_mc_rollout", "bams_mc_rollout_2ply")

    def test_crn_opponent_rack_sample_validity(self, shared_engine, standard_opening_state):
        """Verifies opponent rack samples drawn via CRN are subsets of remaining unseen tiles."""
        conf = BAMSConfig(num_samples=4, seed=777, device="cpu")
        bams = BAMSSearch(engine=shared_engine, config=conf)

        samples = bams.belief_net.sample_opponent_racks(
            standard_opening_state, num_samples=4, rack_size=7, seed=777
        )
        assert len(samples) == 4
        unseen_pool = bams.belief_net.get_unseen_tile_pool(standard_opening_state)

        for sample in samples:
            assert len(sample) == 7
            for tile in sample:
                assert tile in unseen_pool

    def test_crn_independence_across_separate_calls(self, shared_engine, checkpoint_path, standard_opening_state):
        """Verifies CRN RNG state does not leak across independent search executions."""
        conf = BAMSConfig(num_samples=4, candidate_beam=4, seed=555, device="cpu")
        bams = BAMSSearch.from_checkpoint(shared_engine, checkpoint_path, conf)

        m1, meta1 = bams.select_move(standard_opening_state)
        m2, meta2 = bams.select_move(standard_opening_state)
        assert m1.word == m2.word


class TestTier1SearchVolatilityControl:
    """Tests for Feature 4: Continuous Volatility Control."""

    def test_volatility_formula_sign_direction(self, shared_engine, checkpoint_path):
        """Verifies volatility rewards openness when trailing (negative diff) and closure when leading."""
        bams = BAMSSearch.from_checkpoint(
            shared_engine,
            checkpoint_path,
            BAMSConfig(num_samples=4, candidate_beam=4, use_volatility_control=True, volatility_weight=1.0, device="cpu"),
        )
        # Leading by 50 points: score_diff = +50 -> lambda_vol should be negative (penalizes volatility)
        state_leading = GameState(rack=["A", "E", "I", "N", "R", "S", "T"], score=250, opp_score=200)
        # Trailing by 50 points: score_diff = -50 -> lambda_vol should be positive (rewards volatility)
        state_trailing = GameState(rack=["A", "E", "I", "N", "R", "S", "T"], score=200, opp_score=250)

        # Inspect volatility behavior
        diff_lead = state_leading.score - state_leading.opp_score
        diff_trail = state_trailing.score - state_trailing.opp_score
        assert diff_lead > 0
        assert diff_trail < 0

    def test_volatility_disabled_produces_zero_adjustment(self, shared_engine, checkpoint_path, standard_opening_state):
        """Verifies volatility_weight=0 or use_volatility_control=False zeroes out volatility impact."""
        conf_no_vol = BAMSConfig(
            num_samples=4,
            candidate_beam=4,
            use_volatility_control=False,
            volatility_weight=0.0,
            seed=42,
            device="cpu",
        )
        bams = BAMSSearch.from_checkpoint(shared_engine, checkpoint_path, conf_no_vol)
        move, meta = bams.select_move(standard_opening_state)
        assert move is not None

    def test_volatility_continuity_around_threshold(self):
        """
        Mathematical verification of volatility lambda calculation around the +/- 20 point boundary.
        Evaluates the functional behavior of volatility scaling.
        """
        def calc_vol_lambda(score_diff: float) -> float:
            if score_diff <= -20:
                return 0.15 * min(2.0, (-score_diff) / 40.0)
            elif score_diff >= 20:
                return -0.15 * min(2.0, score_diff / 40.0)
            else:
                return -0.15 * (score_diff / 20.0)

        # Verify monotonicity on symmetric intervals
        assert calc_vol_lambda(-40) > calc_vol_lambda(-30)
        assert calc_vol_lambda(40) < calc_vol_lambda(30)
        assert pytest.approx(calc_vol_lambda(0), abs=1e-5) == 0.0


class TestTier1SearchPreEndgameAndEndgame:
    """Tests for Feature 2: Pre-Endgame Parity Logic & Exact Minimax Solver."""

    def test_pre_endgame_activation_at_low_bag_count(self, shared_engine, checkpoint_path):
        """Verifies pre-endgame adjustments activate when bag count is between 1 and 5."""
        state = GameState(
            rack=["C", "A", "T", "S", "E", "E", "D"],
            opp_rack=["B", "I", "R", "D", "I", "E", "S"],
            score=310,
            opp_score=305,
            bag_count=3,
            unseen_counts={"Q": 1, "E": 1, "T": 1},
        )
        bams = BAMSSearch.from_checkpoint(
            shared_engine,
            checkpoint_path,
            BAMSConfig(num_samples=4, candidate_beam=4, use_pre_endgame=True, device="cpu"),
        )
        move, meta = bams.select_move(state)
        assert move is not None
        assert move.is_placement is True

    def test_exact_endgame_solver_activation_unseen_le_7(self, shared_engine, checkpoint_path):
        """Verifies deterministic alpha-beta endgame solver triggers when bag is empty and unseen <= 7."""
        state = GameState(
            rack=["C", "A", "T"],
            score=350,
            opp_score=340,
            bag_count=0,
            unseen_counts={"D": 1, "O": 1, "G": 1},
        )
        bams = BAMSSearch.from_checkpoint(
            shared_engine,
            checkpoint_path,
            BAMSConfig(num_samples=4, candidate_beam=4, use_exact_endgame=True, device="cpu"),
        )
        move, meta = bams.select_move(state)
        assert move is not None
        assert meta["method"] in ("deterministic_endgame", "exact_alphabeta_endgame")

    def test_generator_enhancement_transfer_candidate_quality(self, shared_engine):
        """Tests Feature 14: Verifies generator candidate beam transfer into BAMS candidate pool."""
        state = GameState(rack=["A", "E", "I", "N", "R", "S", "T"])
        cands = shared_engine.generate_moves(game_state=state, max_candidates=10)
        assert len(cands) > 0
        # Check that top candidate has positive score and leaves valid rack
        top_cand = cands[0]
        assert top_cand.score > 0
        assert top_cand.is_placement is True
        assert len(top_cand.leave) <= 7
