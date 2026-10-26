import json
import pytest
from visualizer.backend.app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_api_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert "v4" in data["available_engines"]

def test_api_engines(client):
    res = client.get("/api/engines")
    assert res.status_code == 200
    data = res.get_json()
    assert "engines" in data
    assert any(e["id"] == "v4" for e in data["engines"])

def test_api_models_query(client):
    res = client.get("/api/models?engine=v4")
    assert res.status_code == 200
    data = res.get_json()
    assert "models" in data
    assert len(data["models"]) > 0

def test_api_interactive_move(client):
    payload = {
        "engine": "v4",
        "model": "v4-baseline",
        "board": [[None for _ in range(15)] for _ in range(15)],
        "rack": ["A", "Q", "R", "T", "U", "Y", "Z"],
        "score_diff": 0,
        "bag_remaining": 86
    }
    res = client.post("/api/interactive/move", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert "action" in data
    assert "candidates" in data
    assert len(data["candidates"]) > 0

def test_api_validate_move(client):
    payload = {
        "engine": "v4",
        "board": [[None for _ in range(15)] for _ in range(15)],
        "rack": ["A", "Q", "R", "T", "U", "Y", "Z"],
        "move": {
            "word": "QUA",
            "row": 7,
            "col": 7,
            "direction": "Across"
        }
    }
    res = client.post("/api/interactive/validate", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert "valid" in data

def test_api_compare_position(client):
    payload = {
        "board": [[None for _ in range(15)] for _ in range(15)],
        "rack": ["T", "R", "A", "I", "N", "E", "R"],
        "engines": ["v4", "magpie"]
    }
    res = client.post("/api/compare/position", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert "comparisons" in data
    assert "v4" in data["comparisons"]


def test_api_interactive_move_empty_rack_returns_pass(client):
    """When a game ends and rack is empty, /api/interactive/move should return PASS instead of 400."""
    payload = {
        "engine": "v4",
        "model": "v4-baseline",
        "board": [[None for _ in range(15)] for _ in range(15)],
        "rack": [],
        "score_diff": 0,
        "bag_remaining": 0
    }
    res = client.post("/api/interactive/move", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["action"] == "PASS"
    assert data["points"] == 0


def test_api_dictionary_lookup(client):
    """Test word validity and definition lookup endpoint."""
    res = client.get("/api/dictionary/lookup?word=QUIZ&lexicon=CSW24")
    assert res.status_code == 200
    data = res.get_json()
    assert data["word"] == "QUIZ"
    assert data["valid"] is True
    assert data["score"] == 22
    assert "definition" in data
    assert len(data["definition"]) > 0

    # Phoney / invalid word
    res_invalid = client.get("/api/dictionary/lookup?word=XYZZYNOTAWARD&lexicon=CSW24")
    assert res_invalid.status_code == 200
    data_invalid = res_invalid.get_json()
    assert data_invalid["valid"] is False


