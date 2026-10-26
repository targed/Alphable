import pytest
from visualizer.backend.adapters.v4_adapter import V4Adapter
from visualizer.backend.adapters.baseline_adapter import BaselineAdapter

def test_v4_adapter_initialization_and_metadata():
    adapter = V4Adapter()
    assert adapter.get_id() == "v4"
    assert "Alphable V4" in adapter.get_name()
    models = adapter.list_available_models()
    assert len(models) > 0
    assert any(m["id"] == "latest" for m in models)

def test_v4_adapter_move_selection_and_validation():
    adapter = V4Adapter()
    board = [[None for _ in range(15)] for _ in range(15)]
    rack = ["A", "Q", "R", "T", "U", "Y", "Z"]
    res = adapter.select_move(board, rack, model_name="v4-baseline")
    assert res["action"] in ("PLAY", "PASS", "EXCHANGE")
    assert "candidates" in res
    assert len(res["candidates"]) > 0

    top_move = res["candidates"][0]
    val = adapter.validate_move(board, rack, top_move)
    assert val["valid"] is True
    assert val["points"] > 0

def test_baseline_adapter_greedy_and_magpie():
    adapter = BaselineAdapter()
    assert adapter.get_id() == "baseline"
    board = [[None for _ in range(15)] for _ in range(15)]
    rack = ["C", "A", "T", "S", "E", "R", "D"]
    res_magpie = adapter.select_move(board, rack, mode="magpie")
    assert res_magpie["action"] == "PLAY"
    assert len(res_magpie["candidates"]) > 0

    res_greedy = adapter.select_move(board, rack, mode="greedy")
    assert res_greedy["action"] == "PLAY"
    assert len(res_greedy["candidates"]) > 0


def test_v4_adapter_sanitizes_exhausted_tiles_without_error_51():
    """Verify that when a letter on the board is repeated in rack (exhausting bag), it does not crash MAGPIE with error 51."""
    v4 = V4Adapter()
    baseline = BaselineAdapter()

    board = [[None for _ in range(15)] for _ in range(15)]
    # Place QUARTZY on board (consuming Z and Q)
    word = "QUARTZY"
    for i, ch in enumerate(word):
        board[7][4 + i] = ch

    # Rack with duplicate Z (only 1 Z exists in English Scrabble)
    duplicate_z_rack = ["Z", "Y", "L", "D", "H", "N", "B"]

    # Both V4 and MAGPIE baseline must not raise RuntimeError / error 51
    res_v4 = v4.select_move(board, duplicate_z_rack, model_name="v4-baseline")
    assert res_v4["action"] in ("PLAY", "PASS", "EXCHANGE")

    res_base = baseline.select_move(board, duplicate_z_rack, mode="magpie")
    assert res_base["action"] in ("PLAY", "PASS", "EXCHANGE")

