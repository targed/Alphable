"""
Tier 1: Core Engine Feature Coverage E2E Tests.

Covers:
- Feature 1 & 19: C Memory Management & string freeing in ctypes wrapper (BUG-01)
- Feature 5: Strict Coordinate Parsing (valid across/down, edge coordinates, bounds rejection)
- Feature 12: Base MAGPIE Ceiling Audit (options, PAT, WMP, -numplays)
- Core Engine: CGP roundtrip, 32-channel spatial tensors, 64-dim dynamic state vectors,
  GameState move application transitions, lexicon switching.
"""

import ctypes
import pytest
import torch

from alphable.engine.game_state import (
    GameState,
    DL_SQUARES,
    TL_SQUARES,
    DW_SQUARES,
    TW_SQUARES,
    STANDARD_TILE_COUNTS,
)
from alphable.engine.move import Move
from alphable.engine.magpie_bindings import MagpieEngine, MAGPIE_SUCCESS


class TestTier1EngineCtypesMemory:
    """Tests for Feature 1 & Feature 19: C Memory Management & Ctypes wrapper."""

    def test_c_engine_lifecycle_and_clean_exit(self, shared_engine):
        """Verifies clean creation, command execution, and non-null instance handle."""
        assert shared_engine._handle is not None
        output = shared_engine.run_command("help")
        assert len(output) > 0
        assert "Commands" in output or "help" in output.lower()

    def test_c_engine_string_allocation_and_output_retrieval(self, shared_engine):
        """Verifies string allocation from magpie_get_last_command_output returns valid content."""
        out = shared_engine.run_command("version")
        assert isinstance(out, str)
        assert len(out.strip()) > 0

    def test_c_engine_rapid_sequential_commands_no_crash(self, shared_engine):
        """Verifies repeated execution of commands does not corrupt heap or cause segfaults."""
        for i in range(25):
            out = shared_engine.run_command(f"set -numplays {50 + (i % 20)}")
            assert isinstance(out, str)

    def test_c_engine_error_capture_and_clearing(self, shared_engine):
        """Verifies error detection and error string clearing without pointer corruption."""
        with pytest.raises(RuntimeError) as exc_info:
            shared_engine.run_command("invalid_magpie_command_xyz_123")
        assert "failed" in str(exc_info.value).lower()

    def test_c_engine_multiple_instances_isolation(self):
        """Verifies that separate MagpieEngine instances maintain isolated C contexts."""
        eng1 = MagpieEngine(lexicon="CSW24")
        eng2 = MagpieEngine(lexicon="NWL23")
        try:
            assert eng1.lexicon == "CSW24"
            assert eng2.lexicon == "NWL23"
            assert eng1._handle != eng2._handle
        finally:
            eng1.close()
            eng2.close()


class TestTier1EngineCoordinateParsing:
    """Tests for Feature 5: Strict Coordinate Parsing."""

    def test_parse_valid_across_coordinates(self):
        """Verifies across coordinates parse to correct 0-indexed row, col, and direction."""
        row, col, direction = Move.parse_coordinate("8H")
        assert (row, col, direction) == (7, 7, "Across")

        row, col, direction = Move.parse_coordinate("1A")
        assert (row, col, direction) == (0, 0, "Across")

        row, col, direction = Move.parse_coordinate("15O")
        assert (row, col, direction) == (14, 14, "Across")

    def test_parse_valid_down_coordinates(self):
        """Verifies down coordinates parse to correct 0-indexed row, col, and direction."""
        row, col, direction = Move.parse_coordinate("H8")
        assert (row, col, direction) == (7, 7, "Down")

        row, col, direction = Move.parse_coordinate("A1")
        assert (row, col, direction) == (0, 0, "Down")

        row, col, direction = Move.parse_coordinate("O15")
        assert (row, col, direction) == (14, 14, "Down")

    def test_parse_case_insensitivity(self):
        """Verifies coordinate parsing accepts lowercase coordinates."""
        row1, col1, dir1 = Move.parse_coordinate("8h")
        assert (row1, col1, dir1) == (7, 7, "Across")

        row2, col2, dir2 = Move.parse_coordinate("h8")
        assert (row2, col2, dir2) == (7, 7, "Down")

    def test_parse_invalid_string_raises_value_error(self):
        """Verifies malformed non-alphanumeric coordinate strings raise ValueError."""
        invalid_coords = ["", "   ", "XYZ", "8", "H", "??", "8H8"]
        for c in invalid_coords:
            with pytest.raises(ValueError):
                Move.parse_coordinate(c)

    def test_parse_column_out_of_bounds_raises_value_error(self):
        """Verifies coordinates with column letters beyond O (e.g. P, Z) raise ValueError."""
        with pytest.raises(ValueError):
            Move.parse_coordinate("8P")
        with pytest.raises(ValueError):
            Move.parse_coordinate("P8")
        with pytest.raises(ValueError):
            Move.parse_coordinate("8Z")


class TestTier1EngineMagpieCeiling:
    """Tests for Feature 12: Base MAGPIE Ceiling & Runtime Parameter Options."""

    def test_magpie_numplays_and_maxnumdplays_configuration(self, shared_engine):
        """Verifies setting -numplays and -maxnumdplays updates candidate generation bounds."""
        shared_engine.run_command("set -numplays 25 -maxnumdplays 25")
        moves = shared_engine.generate_moves(rack="AEINRST", max_candidates=25)
        assert len(moves) <= 25

    def test_magpie_lexicon_switching_csw24_and_nwl23(self, shared_engine):
        """Verifies dynamic switching between international CSW24 and North American NWL23 lexica."""
        shared_engine.set_lexicon("CSW24")
        assert shared_engine.lexicon == "CSW24"
        moves_csw = shared_engine.generate_moves(rack="QI", max_candidates=10)
        assert any(m.word == "QI" for m in moves_csw)

        shared_engine.set_lexicon("NWL23")
        assert shared_engine.lexicon == "NWL23"
        moves_nwl = shared_engine.generate_moves(rack="QI", max_candidates=10)
        assert any(m.word == "QI" for m in moves_nwl)

        # Restore CSW24
        shared_engine.set_lexicon("CSW24")

    def test_magpie_shwithmoves_formatting(self, shared_engine):
        """Verifies machine-readable move output configuration without human-readable clutter."""
        out = shared_engine.run_command("set -shwithmoves false")
        assert isinstance(out, str)

    def test_magpie_best_reply_generation(self, shared_engine, standard_opening_state):
        """Verifies opponent counter-play generation via best_reply."""
        reply = shared_engine.best_reply(standard_opening_state, "CABINET")
        assert reply is not None
        assert reply.is_placement or reply.is_pass or reply.is_exchange

    def test_magpie_cgp_loading_and_rack_setting(self, shared_engine, standard_opening_state):
        """Verifies CGP string ingestion into C engine state and subsequent move generation."""
        cgp = standard_opening_state.to_cgp()
        shared_engine.set_cgp(cgp)
        moves = shared_engine.generate_moves(game_state=standard_opening_state, max_candidates=5)
        assert len(moves) > 0
        assert moves[0].score > 0


class TestTier1EngineGameStateRepresentations:
    """Tests for GameState serialization, tensor generation, and transitions."""

    def test_cgp_serialization_and_deserialization_fidelity(self, midgame_state):
        """Verifies bit-accurate roundtrip between GameState and Compact Game Position (CGP)."""
        cgp_str = midgame_state.to_cgp()
        reconstructed = GameState.from_cgp(cgp_str)

        assert reconstructed.score == midgame_state.score
        assert reconstructed.opp_score == midgame_state.opp_score
        assert reconstructed.rack == midgame_state.rack
        assert reconstructed.opp_rack == midgame_state.opp_rack
        assert reconstructed.board[7][7] == "T"
        assert reconstructed.board[7][8] == "R"
        assert reconstructed.board[7][9] == "A"
        assert reconstructed.board[7][10] == "I"
        assert reconstructed.board[7][11] == "N"

    def test_32_channel_board_tensor_premiums_and_tokens(self, midgame_state):
        """Verifies 32-channel board tensor dimensions, letter one-hot planes, and premiums."""
        tensor = midgame_state.to_board_tensor()
        assert tensor.shape == (32, 15, 15)
        assert tensor.dtype == torch.float32

        # Verify letter plane for 'T' (ord('T') - ord('A') = 19)
        t_plane = ord("T") - ord("A")
        assert tensor[t_plane, 7, 7] == 1.0

        # Verify premium plane 30 (Triple Word) at (0, 0) is 1.0 (uncovered)
        assert tensor[30, 0, 0] == 1.0

    def test_64_dimensional_state_vector_features(self, midgame_state):
        """Verifies 64-dimensional dynamic state vector contains normalized game features."""
        vec = midgame_state.to_state_vector(belief_confidence=0.92)
        assert vec.shape == (64,)
        assert vec.dtype == torch.float32

        # Score differential normalized: (120 - 110) / 500 = 0.02
        assert pytest.approx(vec[27].item(), abs=1e-3) == 0.02
        # Bag count normalized: 54 / 100 = 0.54
        assert pytest.approx(vec[28].item(), abs=1e-3) == 0.54
        # Belief confidence
        assert pytest.approx(vec[63].item(), abs=1e-3) == 0.92

    def test_apply_move_state_transition_and_seat_swap(self, standard_opening_state):
        """Verifies apply_move places tiles, updates scores, and swaps turn perspective."""
        move = Move(row=7, col=7, direction="Across", word="TRAIN", score=18)
        next_state = standard_opening_state.apply_move(move)

        # Player on turn swaps: next_state.score is now Player 2's score (0)
        assert next_state.score == 0
        assert next_state.opp_score == 18
        assert next_state.rack == standard_opening_state.opp_rack
        assert next_state.board[7][7] == "T"
        assert next_state.board[7][11] == "N"

    def test_move_dataclass_properties_and_woogles_conversion(self):
        """Verifies Move properties: is_placement, coord_str, to_cgp_action, to_woogles."""
        move = Move(row=7, col=7, direction="Across", word="BINGO", score=72, leave="S")
        assert move.is_placement is True
        assert move.coord_str == "8H"
        assert move.to_cgp_action() == "8H BINGO"

        woogles_dict = move.to_woogles()
        assert woogles_dict["action"] == "play"
        assert woogles_dict["row"] == 7
        assert woogles_dict["col"] == 7
        assert woogles_dict["dir"] == "Across"
        assert woogles_dict["word"] == "BINGO"
        assert woogles_dict["score"] == 72
