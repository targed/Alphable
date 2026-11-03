import pytest
from visualizer.backend.app import create_app
from visualizer.backend.adapters.v3_adapter import V3_AVAILABLE

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_e2e_health_and_static_serving(client):
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    data = res_health.get_json()
    assert data["status"] == "ok"
    assert data["frontend_built"] is True

    # Test static index.html serving at root
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert b"<!DOCTYPE html>" in res_root.data or b"Alphable Visualizer" in res_root.data

def test_e2e_all_engines_move_generation(client):
    board = [[None for _ in range(15)] for _ in range(15)]
    rack = ["C", "A", "T", "S", "E", "R", "D"]

    engines = ["v4", "magpie", "greedy"]
    if V3_AVAILABLE:
        engines.append("v3")

    for engine in engines:
        payload = {
            "engine": engine,
            "board": board,
            "rack": rack,
            "score_diff": 0,
            "bag_remaining": 86,
            "lexicon": "CSW24"
        }
        res = client.post("/api/interactive/move", json=payload)
        assert res.status_code == 200, f"Engine {engine} failed: {res.data}"
        data = res.get_json()
        assert data["action"] == "PLAY"
        assert "move" in data
        assert data["points"] > 0
        assert len(data["candidates"]) > 0

def test_e2e_cross_engine_comparison(client):
    board = [[None for _ in range(15)] for _ in range(15)]
    board[7][7] = "A"
    rack = ["C", "T", "S", "E", "R", "D", "O"]

    engines = ["v4", "magpie"]
    if V3_AVAILABLE:
        engines.append("v3")

    payload = {
        "board": board,
        "rack": rack,
        "engines": engines,
        "lexicon": "CSW24"
    }
    res = client.post("/api/compare/position", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert "comparisons" in data
    assert "v4" in data["comparisons"]
    assert "magpie" in data["comparisons"]
    assert data["comparisons"]["v4"]["action"] == "PLAY"
    assert data["comparisons"]["magpie"]["action"] == "PLAY"
    if V3_AVAILABLE:
        assert "v3" in data["comparisons"]
        assert data["comparisons"]["v3"]["action"] == "PLAY"
