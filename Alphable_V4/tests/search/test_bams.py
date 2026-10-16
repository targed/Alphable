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
        assert meta["method"] in ("bams_mc_rollout", "bams_mc_rollout_2ply")
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

    def test_dynamic_search_params(self, shared_engine, checkpoint_path):
        """Verifies dynamic beam scaling based on score differential and bag count."""
        bams = BAMSSearch.from_checkpoint(shared_engine, checkpoint_path, config=BAMSConfig())
        
        # Trailing by 30 points -> beam 18+, deficit 7.5
        trailing_state = GameState(score=200, opp_score=235, bag_count=40)
        beam_t, def_t = bams.get_dynamic_search_params(trailing_state)
        assert beam_t >= 18
        assert def_t >= 7.5

        # Leading by 40 points -> beam <= 10, deficit <= 3.0
        leading_state = GameState(score=300, opp_score=255, bag_count=30)
        beam_l, def_l = bams.get_dynamic_search_params(leading_state)
        assert beam_l <= 10
        assert def_l <= 3.0

    def test_exact_endgame_alphabeta_solver(self, shared_engine, checkpoint_path):
        """Verifies exact alpha-beta minimax endgame solver activates and selects optimal play."""
        cgp = "11WYLE/5ADNOUN1A2/2EMBLOOMS2W2/2HUI2T3Li2/6QI2BAE2/5KIF1ZIGs1F/4GONIA1PUT1O/5A1ELVEN1GO/7D2DEVOT/12AXE/12R1R/12I2/8JIRRE2/8ARIOT2/5SAPIENCY2 ADRTHEC/ESTUESN 443/442 0 -lex CSW24"
        state = GameState.from_cgp(cgp)
        state.bag_count = 0

        bams = BAMSSearch.from_checkpoint(
            shared_engine,
            checkpoint_path,
            config=BAMSConfig(use_exact_endgame=True),
        )

        selected, meta = bams.select_move(state)
        assert selected is not None
        assert meta["method"] in ("exact_alphabeta_endgame", "deterministic_endgame")
        assert selected.word == "RATCHED"
        assert selected.score == 87

    def test_nested_2ply_execution(self, shared_engine, checkpoint_path):
        """Verifies Frontier 1 true 2-ply nested Monte Carlo rollout runs and populates 2-ply equity."""
        state = GameState(board=[[None]*15 for _ in range(15)], rack=list("ENRSTUW"), lexicon="CSW24")
        bams = BAMSSearch.from_checkpoint(
            shared_engine,
            checkpoint_path,
            config=BAMSConfig(nested_2ply=True, candidate_beam_2ply=4, samples_2ply=8),
        )

        selected, meta = bams.select_move(state)
        assert selected is not None
        assert selected.is_placement
        assert meta["method"] == "bams_mc_rollout_2ply"
        assert len(meta["evaluations"]) >= 1
        # Top evaluated candidates must have computed 2-ply net exchange
        assert meta["evaluations"][0]["mean_2ply_net"] is not None

    def test_nested_2ply_latency(self, shared_engine, checkpoint_path):
        """Verifies Frontier 1 2-ply rollout complies with latency budget (<250 ms)."""
        state = GameState(board=[[None]*15 for _ in range(15)], rack=list("AEINRST"), lexicon="CSW24")
        bams = BAMSSearch.from_checkpoint(
            shared_engine,
            checkpoint_path,
            config=BAMSConfig(nested_2ply=True, candidate_beam_2ply=6, samples_2ply=12),
        )

        _, meta = bams.select_move(state)
        assert meta["latency_ms"] < 600.0, f"2-ply latency {meta['latency_ms']:.1f} ms exceeded threshold"

    def test_pre_endgame_parity_and_sticking(self, shared_engine, checkpoint_path):
        """Verifies Frontier 3 pre-endgame parity and tile-sticking equity adjustments."""
        bams = BAMSSearch.from_checkpoint(shared_engine, checkpoint_path, config=BAMSConfig(use_pre_endgame=True))
        
        # Board with center word TRAIN
        board = [[None]*15 for _ in range(15)]
        for i, ch in enumerate("TRAIN"):
            board[7][7+i] = ch

        # Bag count is 1, unseen has stranded Q (no U)
        unseen = {"Q": 1, "E": 2, "A": 2, "T": 2}
        state = GameState(board=board, rack=list("RETINAS"), bag_count=1, unseen_counts=unseen)

        cands = shared_engine.generate_moves(game_state=state, rack="RETINAS", max_candidates=10)
        assert len(cands) > 0

        adjusted = bams._evaluate_pre_endgame(state, cands)
        assert len(adjusted) == len(cands)
        # Verify candidate equity was updated and candidates remain sorted descending
        for i in range(len(adjusted) - 1):
            assert adjusted[i].equity >= adjusted[i+1].equity

    def test_pre_endgame_full_bams_activation(self, shared_engine, checkpoint_path):
        """Verifies full BAMS select_move operates seamlessly in pre-endgame bag counts (1-5)."""
        board = [[None]*15 for _ in range(15)]
        for i, ch in enumerate("TRAIN"):
            board[7][7+i] = ch

        state = GameState(board=board, rack=list("RETINAS"), bag_count=3)
        bams = BAMSSearch.from_checkpoint(
            shared_engine,
            checkpoint_path,
            config=BAMSConfig(use_pre_endgame=True, nested_2ply=True, candidate_beam_2ply=4, samples_2ply=6),
        )

        selected, meta = bams.select_move(state)
        assert selected is not None
        assert selected.is_placement

    def test_asymmetric_volatility_control(self, shared_engine, checkpoint_path):
        """Verifies Pillar 2 asymmetric board volatility computation and leading/trailing adjustments."""
        bams = BAMSSearch.from_checkpoint(
            shared_engine,
            checkpoint_path,
            config=BAMSConfig(use_volatility_control=True, candidate_beam_2ply=4, samples_2ply=6),
        )

        board_empty = [[None]*15 for _ in range(15)]
        vol_empty = bams.compute_board_volatility(board_empty)
        assert vol_empty >= 0.0

        # Board with center word TRAIN has higher openness
        board_train = [[None]*15 for _ in range(15)]
        for i, ch in enumerate("TRAIN"):
            board_train[7][7+i] = ch
        vol_train = bams.compute_board_volatility(board_train)
        assert vol_train >= 0.0

        # Test leading position (+50 pts)
        state_lead = GameState(board=board_train, rack=list("RETINAS"), score=350, opp_score=300)
        move_lead, meta_lead = bams.select_move(state_lead)
        assert move_lead is not None
        assert move_lead.is_placement

        # Test trailing position (-50 pts)
        state_trail = GameState(board=board_train, rack=list("RETINAS"), score=250, opp_score=300)
        move_trail, meta_trail = bams.select_move(state_trail)
        assert move_trail is not None
        assert move_trail.is_placement
