"""
Tests for GameState representation, tensor generation, and CGP conversion.
"""

import pytest
import torch
from alphable.engine.game_state import GameState, DL_SQUARES, TL_SQUARES, DW_SQUARES, TW_SQUARES
from alphable.engine.move import Move
from alphable.engine.magpie_bindings import MagpieEngine


def test_empty_game_state():
    state = GameState(rack=["A", "B", "C", "D", "E", "F", "G"])
    assert len(state.rack) == 7
    assert state.score == 0
    assert state.opp_score == 0
    cgp = state.to_cgp()
    assert "15/15/15/15/15/15/15/15/15/15/15/15/15/15/15 ABCDEFG/ 0/0 0" in cgp


def test_cgp_roundtrip():
    original = GameState(
        rack=["A", "E", "I", "N", "R", "S", "T"],
        opp_rack=["C", "A", "B", "I", "N", "E", "T"],
        score=45,
        opp_score=32,
        scoreless_turns=1,
        lexicon="CSW24",
    )
    # Place a word in center
    original.board[7][7] = "T"
    original.board[7][8] = "E"
    original.board[7][9] = "S"
    original.board[7][10] = "T"

    cgp_str = original.to_cgp()
    reconstructed = GameState.from_cgp(cgp_str)

    assert reconstructed.score == 45
    assert reconstructed.opp_score == 32
    assert reconstructed.scoreless_turns == 1
    assert reconstructed.rack == original.rack
    assert reconstructed.opp_rack == original.opp_rack
    assert reconstructed.board[7][7] == "T"
    assert reconstructed.board[7][8] == "E"
    assert reconstructed.board[7][9] == "S"
    assert reconstructed.board[7][10] == "T"
    assert reconstructed.board[0][0] is None


def test_board_tensor_dimensions_and_premiums():
    state = GameState(rack=["A", "E", "I", "N", "R", "S", "T"])
    tensor = state.to_board_tensor()

    assert tensor.shape == (32, 15, 15)
    assert tensor.dtype == torch.float32

    # Verify unoccupied premium squares are 1.0
    for r, c in DL_SQUARES:
        assert tensor[27, r, c] == 1.0
    for r, c in TL_SQUARES:
        assert tensor[28, r, c] == 1.0
    for r, c in DW_SQUARES:
        assert tensor[29, r, c] == 1.0
    for r, c in TW_SQUARES:
        assert tensor[30, r, c] == 1.0

    # Place a tile on a Double Word square (1, 1)
    state.board[1][1] = "A"
    tensor_after = state.to_board_tensor()
    # Premium should now be covered (0.0)
    assert tensor_after[29, 1, 1] == 0.0
    # Letter plane A (0) should be 1.0
    assert tensor_after[0, 1, 1] == 1.0
    # Overlap plane (31) should be 1.0 because 'A' is in rack
    assert tensor_after[31, 1, 1] == 1.0


def test_state_vector_dimensions_and_features():
    state = GameState(
        rack=["A", "?", "S", "E", "E", "D", "Y"],
        score=150,
        opp_score=100,
        bag_count=50,
    )
    vec = state.to_state_vector(belief_confidence=0.85)

    assert vec.shape == (64,)
    assert vec.dtype == torch.float32

    # Check blank count (dim 26)
    assert vec[26] == 1.0
    # Check normalized score diff (dim 27): (150 - 100) / 500 = 0.1
    assert abs(vec[27].item() - 0.1) < 1e-4
    # Check normalized bag (dim 28): 50 / 100 = 0.5
    assert abs(vec[28].item() - 0.5) < 1e-4
    # Has blank flag (dim 32)
    assert vec[32] == 1.0
    # Has S flag (dim 33)
    assert vec[33] == 1.0
    # Belief confidence (dim 63)
    assert abs(vec[63].item() - 0.85) < 1e-4


def test_apply_move():
    state = GameState(
        rack=["C", "A", "T", "S", "E", "E", "D"],
        opp_rack=["B", "I", "R", "D", "I", "E", "S"],
        score=0,
        opp_score=0,
    )
    move = Move(
        row=7,
        col=7,
        direction="Across",
        word="CATS",
        score=24,
    )
    next_state = state.apply_move(move)

    # Next player on turn
    assert next_state.rack == ["B", "I", "R", "D", "I", "E", "S"]
    assert next_state.opp_rack == ["E", "E", "D"]
    assert next_state.score == 0
    assert next_state.opp_score == 24
    assert next_state.board[7][7] == "C"
    assert next_state.board[7][8] == "A"
    assert next_state.board[7][9] == "T"
    assert next_state.board[7][10] == "S"


def test_generate_moves_from_game_state():
    eng = MagpieEngine(lexicon="CSW24")
    state = GameState(
        rack=["A", "E", "I", "N", "R", "S", "T"],
        score=0,
        opp_score=0,
    )
    moves = eng.generate_moves(game_state=state)
    assert len(moves) > 0
    assert moves[0].score > 0
    eng.close()
