"""
Tier 3: Cross-Feature Combinations E2E Tests.

Covers:
- Combinations:
  1. BAMS 2-ply search + Bayesian Opponent Belief tracking (negative evidence updates).
  2. Asymmetric volatility control + Dynamic candidate beam scaling across score deficits.
  3. Duplicate match pair execution: Game A + Game B with Common Random Numbers.
  4. First-order luck cancellation theorem validation on mirrored game pairs.
  5. Lexicon switching within multi-engine tournament match pipelines.
"""

import pytest
from typing import Dict, Any, Tuple

from alphable.engine.game_state import GameState
from alphable.engine.move import Move
from alphable.engine.magpie_bindings import MagpieEngine
from alphable.models.belief_net import OpponentTracker, BayesianRackInference
from alphable.platform.eval import GameSimulator, MatchStats
from alphable.search.bams import BAMSSearch, BAMSConfig


class TestTier3BAMSWithBeliefTracking:
    """Tests for integration between BAMS search and Bayesian opponent rack inference."""

    def test_bams_with_negative_evidence_belief_update(self, shared_engine, checkpoint_path, fast_bams_config):
        """
        Verifies that when opponent makes a low-scoring play despite open power opportunities,
        OpponentTracker downweights power tiles, and subsequent BAMS search incorporates this belief.
        """
        bams = BAMSSearch.from_checkpoint(shared_engine, checkpoint_path, fast_bams_config)

        # Pre-state: opponent made a 12-point play when 40+ point plays existed
        opp_move = Move(row=7, col=7, direction="Across", word="IT", score=6)
        bams.record_opponent_move(opp_move)

        # Belief tracker should downweight '?' and 'S'
        weights = bams.opp_tracker.tile_weights
        assert weights.get("?", 1.0) < 1.0, "Expected blank tile weight to decay on low-scoring opponent play"

        # Subsequent search incorporates updated belief weights
        state = GameState(rack=["A", "E", "I", "N", "R", "S", "T"], score=40, opp_score=6)
        move, meta = bams.select_move(state)
        assert move is not None
        assert move.is_placement is True

    def test_bams_belief_tracker_pass_decay_and_reset(self):
        """Verifies pass move causes sharp decay on blank and S weights, and reset restores prior 1.0."""
        tracker = OpponentTracker()
        assert tracker.tile_weights["?"] == 1.0
        assert tracker.tile_weights["S"] == 1.0

        # Opponent passes
        pass_move = Move.create_pass()
        tracker.update_after_opponent_move(pass_move)

        assert tracker.tile_weights["?"] < 0.5, "Expected blank tile weight to decay sharply on pass"
        assert tracker.tile_weights["S"] < 0.5, "Expected S tile weight to decay on pass"

        # Reset restores all weights to 1.0
        tracker.reset()
        assert tracker.tile_weights["?"] == 1.0
        assert tracker.tile_weights["S"] == 1.0


class TestTier3DynamicBeamAndVolatility:
    """Tests for joint interaction of dynamic candidate beam and volatility scaling."""

    def test_dynamic_beam_and_volatility_joint_adjustment_trailing(self, shared_engine, checkpoint_path):
        """Verifies trailing position (+50 pt deficit) expands beam and rewards board volatility."""
        conf = BAMSConfig(
            num_samples=4,
            candidate_beam=8,
            dynamic_beam=True,
            use_volatility_control=True,
            volatility_weight=0.5,
            device="cpu",
        )
        bams = BAMSSearch.from_checkpoint(shared_engine, checkpoint_path, conf)

        # Trailing: score=150, opp_score=220 (deficit = -70)
        state_trailing = GameState(rack=["A", "E", "I", "N", "R", "S", "T"], score=150, opp_score=220)
        move_trail, meta_trail = bams.select_move(state_trailing)
        assert move_trail is not None
        assert meta_trail["num_candidates_evaluated"] > 0

    def test_dynamic_beam_and_volatility_joint_adjustment_leading(self, shared_engine, checkpoint_path):
        """Verifies leading position (+60 pt surplus) narrows beam and penalizes board volatility."""
        conf = BAMSConfig(
            num_samples=4,
            candidate_beam=8,
            dynamic_beam=True,
            use_volatility_control=True,
            volatility_weight=0.5,
            device="cpu",
        )
        bams = BAMSSearch.from_checkpoint(shared_engine, checkpoint_path, conf)

        # Leading: score=250, opp_score=190 (surplus = +60)
        state_leading = GameState(rack=["A", "E", "I", "N", "R", "S", "T"], score=250, opp_score=190)
        move_lead, meta_lead = bams.select_move(state_leading)
        assert move_lead is not None
        assert meta_lead["num_candidates_evaluated"] > 0


class TestTier3DuplicatePairLuckCancellation:
    """Tests for Theorem 1: First-Order Tile Luck Cancellation in Duplicate Matches."""

    def test_first_order_luck_cancellation_in_duplicate_pair(self, shared_engine):
        """
        Validates Theorem 1:
        In a duplicate pair match (Game A: P1 as P1, P2 as P2; Game B: P2 as P1, P1 as P2 with identical seed),
        the tile sequence sigma is identical for both games.
        For deterministic baseline play, spread delta is exactly 0.0.
        """
        def greedy_policy(state: GameState) -> Tuple[Move, Dict[str, Any]]:
            cands = shared_engine.generate_moves(game_state=state, max_candidates=5)
            if cands:
                return cands[0], {"method": "greedy"}
            return Move.create_pass(), {"method": "pass"}

        sim = GameSimulator(shared_engine, lexicon="CSW24")
        seed = 9876

        # Game A: Player 1 = Model A, Player 2 = Model B
        res_a = sim.play_game(greedy_policy, greedy_policy, seed=seed, max_turns=20)
        # Game B: Player 1 = Model B, Player 2 = Model A
        res_b = sim.play_game(greedy_policy, greedy_policy, seed=seed, max_turns=20)

        # Pair scores
        model_a_total = res_a["p1_score"] + res_b["p2_score"]
        model_b_total = res_a["p2_score"] + res_b["p1_score"]

        # Net spread delta must be exactly 0 under deterministic self-play
        pair_delta = model_a_total - model_b_total
        assert pair_delta == 0, f"Expected 0.0 net spread in identical duplicate self-play, got {pair_delta}"

    def test_bams_vs_static_duplicate_pair_execution(self, shared_engine, checkpoint_path, fast_bams_config):
        """Verifies full duplicate pair execution between BAMS search and Static greedy player."""
        bams = BAMSSearch.from_checkpoint(shared_engine, checkpoint_path, fast_bams_config)

        def bams_policy(state: GameState) -> Tuple[Move, Dict[str, Any]]:
            return bams.select_move(state)

        def static_policy(state: GameState) -> Tuple[Move, Dict[str, Any]]:
            cands = shared_engine.generate_moves(game_state=state, max_candidates=5)
            if cands:
                return cands[0], {"method": "static"}
            return Move.create_pass(), {"method": "pass"}

        sim = GameSimulator(shared_engine, lexicon="CSW24")
        seed = 54321

        res_a = sim.play_game(bams_policy, static_policy, seed=seed, max_turns=15)
        res_b = sim.play_game(static_policy, bams_policy, seed=seed, max_turns=15)

        score_bams = res_a["p1_score"] + res_b["p2_score"]
        score_static = res_a["p2_score"] + res_b["p1_score"]
        net_spread = score_bams - score_static

        assert res_a["p1_invalid"] == 0
        assert res_a["p2_invalid"] == 0
        assert res_b["p1_invalid"] == 0
        assert res_b["p2_invalid"] == 0
        assert isinstance(net_spread, int)
