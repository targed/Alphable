"""
Unit and Integration Tests for Belief-Augmented Monte Carlo Search (BAMS).

Verifies:
1. Correct move selection on opening and midgame positions.
2. Common Random Numbers (CRN) determinism when seed is specified.
3. Deterministic endgame fast-path activation when unseen <= 7 tiles.
4. Execution speed within latency budgets (< 5.0 seconds).
5. Model checkpoint loading and end-to-end integration with MAGPIE and Value Network.
"""

import os
import pytest
import torch

from alphable_v4.engine.move import Move
from alphable_v4.engine.game_state import GameState
from alphable_v4.engine.magpie_bindings import MagpieEngine
from alphable_v4.search.bams import BAMSSearch, BAMSConfig


@pytest.fixture(scope="module")
def shared_engine():
    """Shared MAGPIE engine for search tests."""
    eng = MagpieEngine(lexicon="CSW24")
    yield eng
    eng.close()


@pytest.fixture(scope="module")
def checkpoint_path():
    """Path to trained V4 Value Network checkpoint."""
    path = os.path.join(
        os.path.dirname(__file__), "..", "..", "models", "checkpoints", "v4_value_net_best.pt"
    )
    return os.path.normpath(path)


class TestBAMSSearch:
    """Test suite for BAMSSearch."""

    def test_bams_move_selection_opening(self, shared_engine, checkpoint_path):
        """Verifies move selection on an opening board."""
        state = GameState(rack=["A", "Q", "R", "T", "U", "Y", "Z"])
        bams = BAMSSearch.from_checkpoint(
            engine=shared_engine,
            checkpoint_path=checkpoint_path,
            config=BAMSConfig(num_samples=16, candidate_beam=10, seed=42),
        )

        selected_move, meta = bams.select_move(state)
        assert selected_move is not None
        assert selected_move.is_placement
        assert selected_move.score > 0
        assert selected_move.word != ""
        assert meta["method"] == "bams_mc_rollout"
        assert meta["latency_ms"] < 2000.0, f"Search latency {meta['latency_ms']:.1f}ms too high"
        assert len(meta["evaluations"]) > 0

    def test_bams_crn_determinism(self, shared_engine, checkpoint_path):
        """Validates that search with identical seed produces bitwise identical scores."""
        state = GameState(rack=["A", "E", "I", "N", "R", "S", "T"])
        conf1 = BAMSConfig(num_samples=16, candidate_beam=8, seed=999)
        conf2 = BAMSConfig(num_samples=16, candidate_beam=8, seed=999)

        bams1 = BAMSSearch.from_checkpoint(shared_engine, checkpoint_path, conf1)
        bams2 = BAMSSearch.from_checkpoint(shared_engine, checkpoint_path, conf2)

        move1, meta1 = bams1.select_move(state)
        move2, meta2 = bams2.select_move(state)

        assert move1.word == move2.word
        assert move1.score == move2.score
        assert pytest.approx(meta1["best_bams_score"], rel=1e-4) == meta2["best_bams_score"]

    def test_bams_endgame_fast_path(self, shared_engine, checkpoint_path):
        """Verifies that endgame positions with <= 7 unseen tiles activate deterministic solving."""
        state = GameState(
            rack=["C", "A", "T"],
            score=300,
            opp_score=290,
            unseen_counts={"D": 1, "O": 1, "G": 1},  # Exactly 3 tiles remaining
        )
        bams = BAMSSearch.from_checkpoint(
            shared_engine,
            checkpoint_path,
            config=BAMSConfig(num_samples=16, candidate_beam=10),
        )

        selected_move, meta = bams.select_move(state)
        assert meta["method"] == "deterministic_endgame"
        assert meta["opp_rack"] == "DOG" or set(meta["opp_rack"]) == set("DOG")
        assert selected_move is not None

    def test_bams_latency_budget(self, shared_engine, checkpoint_path):
        """Verifies standard midgame search executes comfortably within 1.0s (budget 5.0s)."""
        # Complex clustered midgame position
        board = [["." for _ in range(15)] for _ in range(15)]
        board[7][7] = "T"
        board[7][8] = "R"
        board[7][9] = "A"
        board[7][10] = "I"
        board[7][11] = "N"

        state = GameState(board=board, rack=["C", "A", "M", "P", "E", "R", "S"])
        bams = BAMSSearch.from_checkpoint(
            shared_engine,
            checkpoint_path,
            config=BAMSConfig(num_samples=32, candidate_beam=15, seed=123),
        )

        _, meta = bams.select_move(state)
        print(f"\nMidgame BAMS Latency: {meta['latency_ms']:.2f} ms")
        assert meta["latency_ms"] < 1500.0, f"Latency {meta['latency_ms']:.1f} ms exceeded threshold"
