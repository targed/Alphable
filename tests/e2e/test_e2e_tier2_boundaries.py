"""
Tier 2: Boundary & Corner Cases E2E Tests.

Covers:
- Boundary conditions: Empty bag (0 tiles), single tile remaining (1 tile),
  maximum tiles placed (7 tiles / bingo), consecutive scoreless pass chains (6 passes).
- Coordinate edge bounds: Row 1, Row 15, Col A, Col O.
- Coordinate rejection: Row 0, Row 16, Col P, Col Z, negative rows.
- Adversarial & Extreme scenarios: All-blank rack, power-tile rack, heavy-vowel rack,
  edge-of-board tile placements, malformed CGP handling.
"""

import pytest
from typing import Dict, Any, Tuple

from alphable.engine.game_state import GameState, STANDARD_TILE_COUNTS, TILE_VALUES
from alphable.engine.move import Move
from alphable.engine.magpie_bindings import MagpieEngine
from alphable.platform.eval import ScrabbleBag, GameSimulator


class TestTier2BagAndScoreBoundaries:
    """Tests for edge cases in bag depletion, pass chains, and score extrema."""

    def test_empty_bag_draw_returns_empty_list(self):
        """Verifies that drawing from an empty bag returns an empty list without error."""
        bag = ScrabbleBag(seed=42)
        all_tiles = bag.draw(100)
        assert len(all_tiles) == 100
        assert bag.count == 0

        # Draw from empty bag
        extra = bag.draw(7)
        assert extra == []
        assert bag.count == 0

    def test_single_tile_in_bag_draw_returns_single_tile(self):
        """Verifies drawing 7 tiles when only 1 tile remains in the bag returns exactly 1 tile."""
        bag = ScrabbleBag(seed=42)
        _ = bag.draw(99)
        assert bag.count == 1

        drawn = bag.draw(7)
        assert len(drawn) == 1
        assert bag.count == 0

    def test_consecutive_pass_chain_triggers_game_termination(self, shared_engine):
        """Verifies 6 consecutive scoreless turns / passes terminates the match immediately."""
        def pass_policy(state: GameState) -> Tuple[Move, Dict[str, Any]]:
            return Move.create_pass(), {"method": "pass"}

        sim = GameSimulator(shared_engine, lexicon="CSW24")
        result = sim.play_game(pass_policy, pass_policy, seed=1234, max_turns=60)

        # Game must terminate within 6 turns due to 6 scoreless passes
        assert result["total_turns"] <= 6
        assert len(result["turn_history"]) <= 6
        assert result["winner"] in (0, 1, 2)

    def test_zero_score_exchange_move_mechanics(self):
        """Verifies exchange move scores 0 points, preserves equity, and marks is_exchange."""
        exch = Move.create_exchange(tiles="QZ", score=0, leave="AEINR", equity=-2.5)
        assert exch.is_exchange is True
        assert exch.is_placement is False
        assert exch.is_pass is False
        assert exch.score == 0
        assert exch.word == "QZ"
        assert exch.leave == "AEINR"
        assert exch.equity == -2.5

    def test_maximum_seven_tile_bingo_play(self, shared_engine):
        """Verifies bingo play places all 7 rack tiles and earns 50-point bonus."""
        state = GameState(rack=["R", "E", "T", "I", "N", "A", "S"], score=0, opp_score=0)
        cands = shared_engine.generate_moves(game_state=state, max_candidates=20)
        assert len(cands) > 0

        # Find bingo move (length 7 on opening board)
        bingo_moves = [c for c in cands if len(c.word) == 7 and c.score >= 50]
        assert len(bingo_moves) > 0
        top_bingo = bingo_moves[0]
        assert top_bingo.score >= 50, f"Expected bingo score >= 50, got {top_bingo.score}"


class TestTier2CoordinateBoundariesAndRejection:
    """Tests for grid coordinate boundary extremities and out-of-bounds rejection."""

    def test_coordinate_min_boundaries_row1_col_a(self):
        """Verifies boundary coordinates at (row 1, col A) parse cleanly to (0, 0)."""
        row_a, col_a, dir_a = Move.parse_coordinate("1A")
        assert (row_a, col_a, dir_a) == (0, 0, "Across")

        row_d, col_d, dir_d = Move.parse_coordinate("A1")
        assert (row_d, col_d, dir_d) == (0, 0, "Down")

    def test_coordinate_max_boundaries_row15_col_o(self):
        """Verifies boundary coordinates at (row 15, col O) parse cleanly to (14, 14)."""
        row_a, col_a, dir_a = Move.parse_coordinate("15O")
        assert (row_a, col_a, dir_a) == (14, 14, "Across")

        row_d, col_d, dir_d = Move.parse_coordinate("O15")
        assert (row_d, col_d, dir_d) == (14, 14, "Down")

    def test_coordinate_rejection_row_zero(self):
        """Verifies row 0 ('0A' or 'A0') is rejected with ValueError."""
        with pytest.raises(ValueError):
            Move.parse_coordinate("0A")
        with pytest.raises(ValueError):
            Move.parse_coordinate("A0")

    def test_coordinate_rejection_row_sixteen(self):
        """Verifies row 16 ('16A' or 'A16') is rejected with ValueError."""
        with pytest.raises(ValueError):
            Move.parse_coordinate("16A")
        with pytest.raises(ValueError):
            Move.parse_coordinate("A16")

    def test_coordinate_rejection_large_row_numbers(self):
        """Verifies extreme row numbers ('99A', 'A99', '100A') raise ValueError."""
        with pytest.raises(ValueError):
            Move.parse_coordinate("99A")
        with pytest.raises(ValueError):
            Move.parse_coordinate("A99")
        with pytest.raises(ValueError):
            Move.parse_coordinate("100O")

    def test_coordinate_rejection_column_past_o(self):
        """Verifies column letters past 'O' ('8P', 'P8', '1Z', 'Z15') raise ValueError."""
        for invalid in ["8P", "P8", "1Z", "Z15", "8Q", "Q8"]:
            with pytest.raises(ValueError):
                Move.parse_coordinate(invalid)


class TestTier2AdversarialRacksAndBoards:
    """Tests for adversarial input racks, boards, and CGP parsing."""

    def test_adversarial_two_blank_maximum_rack(self, shared_engine):
        """Verifies move generation executes on rack with maximum legal blanks (2 blanks: '??STARED')."""
        state = GameState(rack=["?", "?", "S", "T", "A", "R", "E"], score=0, opp_score=0)
        cands = shared_engine.generate_moves(game_state=state, max_candidates=10)
        assert len(cands) > 0
        assert cands[0].score > 0

    def test_adversarial_impossible_three_blank_rack_rejected(self, shared_engine):
        """Verifies that exceeding the physical bag limit of 2 blanks raises a tile conservation error."""
        state = GameState(rack=["?", "?", "?", "S", "T", "A", "R"], score=0, opp_score=0)
        with pytest.raises(RuntimeError) as exc_info:
            shared_engine.generate_moves(game_state=state, max_candidates=5)
        assert "not available in the bag" in str(exc_info.value)

    def test_adversarial_power_tile_rack(self, shared_engine):
        """Verifies move generation on high-point power-tile rack 'QZXJKAE'."""
        state = GameState(rack=["Q", "Z", "X", "J", "K", "A", "E"], score=0, opp_score=0)
        cands = shared_engine.generate_moves(game_state=state, max_candidates=10)
        assert len(cands) > 0
        assert any(c.score >= 20 for c in cands)

    def test_adversarial_heavy_vowel_rack(self, shared_engine):
        """Verifies move generation on vowel-saturated rack 'AEIOUAE'."""
        state = GameState(rack=["A", "E", "I", "O", "U", "A", "E"], score=0, opp_score=0)
        cands = shared_engine.generate_moves(game_state=state, max_candidates=5)
        assert len(cands) > 0

    def test_adversarial_single_letter_rack(self, shared_engine):
        """Verifies move generation when player has only 1 tile remaining on rack."""
        state = GameState(rack=["A"], score=300, opp_score=290, bag_count=0)
        cands = shared_engine.generate_moves(game_state=state, max_candidates=5)
        assert isinstance(cands, list)

    def test_adversarial_cgp_deserialization_validation(self):
        """Verifies GameState.from_cgp handles malformed or truncated CGP strings gracefully."""
        with pytest.raises((ValueError, IndexError)):
            GameState.from_cgp("")

        with pytest.raises((ValueError, IndexError)):
            GameState.from_cgp("invalid_cgp_format")
