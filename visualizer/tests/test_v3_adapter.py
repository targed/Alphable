import pytest
from visualizer.backend.adapters.v3_adapter import V3Adapter, V3_AVAILABLE

def test_v3_adapter_metadata_and_capabilities():
    adapter = V3Adapter()
    assert adapter.get_id() == "v3"
    assert "Alphable V3" in adapter.get_name()
    models = adapter.list_available_models()
    assert isinstance(models, list)

def test_v3_adapter_move_generation():
    if not V3_AVAILABLE:
        pytest.skip("Alphable V3 is not available in environment.")
    adapter = V3Adapter()
    board = [[None for _ in range(15)] for _ in range(15)]
    rack = ["C", "A", "T", "S", "E", "R", "D"]
    res = adapter.select_move(board, rack)
    assert res["action"] in ("PLAY", "PASS", "EXCHANGE")
    if res["action"] == "PLAY":
        assert "word" in res["move"]
        assert res["points"] > 0
        assert "candidates" in res
