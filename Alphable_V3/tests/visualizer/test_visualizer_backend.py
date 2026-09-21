import json
import os
import pytest
from pathlib import Path
from visualizer.backend.app import app, DATA_DIRS


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_health_check(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'
    assert 'dictionaries' in data
    assert 'models' in data
    assert 'data_dirs' in data
    assert 'default_model' in data


def test_get_dictionaries(client):
    response = client.get('/api/dictionaries')
    assert response.status_code == 200
    data = response.get_json()
    assert 'dictionaries' in data
    assert isinstance(data['dictionaries'], list)
    assert len(data['dictionaries']) > 0


def test_get_models(client):
    response = client.get('/api/models')
    assert response.status_code == 200
    data = response.get_json()
    assert 'models' in data
    assert isinstance(data['models'], list)
    if data['models']:
        m = data['models'][0]
        assert 'name' in m
        assert 'path' in m
        assert 'size_mb' in m


def test_get_games_filters_summaries(client, tmp_path, monkeypatch):
    test_dir = tmp_path / "vs_test"
    test_dir.mkdir()
    
    # Valid game replay JSON with turns and scores
    valid_game = {
        "metadata": {
            "player1": {"name": "P1", "type": "alphable", "final_score": 350},
            "player2": {"name": "P2", "type": "greedy", "final_score": 300},
        },
        "player_names": ["P1", "P2"],
        "final_score": [350, 300],
        "turns": [
            {"player": 0, "action_type": "PLAY", "word": "TESTING", "score": 75}
        ]
    }
    with open(test_dir / "game_20260920_120000.json", "w") as f:
        json.dump(valid_game, f)

    # Summary file that should be ignored
    summary_file = {
        "summary": "This is a run summary, not a game replay"
    }
    with open(test_dir / "run_20260920_120000_summary.json", "w") as f:
        json.dump(summary_file, f)

    monkeypatch.setitem(DATA_DIRS, "test", test_dir)

    response = client.get('/api/games')
    assert response.status_code == 200
    data = response.get_json()
    assert 'games' in data
    
    # Check that valid_game is present and summary is excluded
    filenames = [g['filename'] for g in data['games'] if g.get('category') == 'test']
    assert "game_20260920_120000.json" in filenames
    assert "run_20260920_120000_summary.json" not in filenames
    
    # Check metadata enrichment
    game_item = next(g for g in data['games'] if g['filename'] == "game_20260920_120000.json")
    assert game_item['winner'] == 'P1'
    assert game_item['score_margin'] == 50
    assert game_item['bingos'] == 1


def test_get_game_details(client, tmp_path, monkeypatch):
    test_dir = tmp_path / "vs_test"
    test_dir.mkdir(exist_ok=True)
    
    game_content = {
        "metadata": {"game_id": "test_123"},
        "player_names": ["A", "B"],
        "final_score": [100, 200],
        "turns": []
    }
    with open(test_dir / "game_1.json", "w") as f:
        json.dump(game_content, f)

    monkeypatch.setitem(DATA_DIRS, "test", test_dir)

    # Valid game request via /api/games/ and alias /api/game/
    resp = client.get('/api/games/test/game_1.json')
    assert resp.status_code == 200
    assert resp.get_json()['metadata']['game_id'] == 'test_123'

    resp_alias = client.get('/api/game/test/game_1.json')
    assert resp_alias.status_code == 200

    # Non-existent game request
    resp_404 = client.get('/api/games/test/nonexistent.json')
    assert resp_404.status_code == 404


def test_get_stats_overall_and_per_game(client, tmp_path, monkeypatch):
    test_dir = tmp_path / "vs_test"
    test_dir.mkdir(exist_ok=True)
    
    game_content = {
        "metadata": {"game_id": "test_123"},
        "player_names": ["Player 0", "Player 1"],
        "final_score": [120, 80],
        "turns": [
            {"player": 0, "action_type": "PLAY", "word": "RETINAS", "score": 70},
            {"player": 1, "action_type": "PLAY", "word": "CAT", "score": 10}
        ]
    }
    with open(test_dir / "game_stats_test.json", "w") as f:
        json.dump(game_content, f)

    monkeypatch.setitem(DATA_DIRS, "test", test_dir)

    # Overall stats
    resp_overall = client.get('/api/stats')
    assert resp_overall.status_code == 200
    overall_data = resp_overall.get_json()
    assert 'total_games' in overall_data
    assert 'categories' in overall_data

    # Per-game stats
    resp_per_game = client.get('/api/stats/test/game_stats_test.json')
    assert resp_per_game.status_code == 200
    per_game_data = resp_per_game.get_json()
    assert per_game_data['total_turns'] == 2
    assert per_game_data['player_stats'][0]['bingos'] == 1
    assert per_game_data['player_stats'][0]['bingo_words'] == ["RETINAS"]


def test_validate_user_move_endpoint(client):
    board = [["." for _ in range(15)] for _ in range(15)]
    rack = ["H", "E", "L", "L", "O", "X", "Y"]

    # Valid initial center move
    payload = {
        "board": board,
        "rack": rack,
        "move": {
            "row": 7,
            "col": 7,
            "word": "HELLO",
            "direction": "Across"
        }
    }
    resp = client.post('/api/interactive/validate_user_move',
                       data=json.dumps(payload),
                       content_type='application/json')
    assert resp.status_code == 200
    res = resp.get_json()
    assert res['valid'] is True
    assert res['points'] > 0
    assert res['score'] > 0

    # Invalid move: off-center on turn 1
    invalid_payload = {
        "board": board,
        "rack": rack,
        "move": {
            "row": 0,
            "col": 0,
            "word": "HELLO",
            "direction": "Across"
        }
    }
    resp_inv = client.post('/api/interactive/validate_user_move',
                           data=json.dumps(invalid_payload),
                           content_type='application/json')
    assert resp_inv.status_code == 200
    res_inv = resp_inv.get_json()
    assert res_inv['valid'] is False
    assert 'error' in res_inv


def test_interactive_ai_move_greedy_and_random(client):
    board = [["." for _ in range(15)] for _ in range(15)]
    rack = ["A", "B", "C", "D", "E", "F", "G"]

    # Greedy AI move
    payload = {
        "board": board,
        "rack": rack,
        "ai_type": "greedy",
        "score_diff": 0,
        "bag_remaining": 86
    }
    resp = client.post('/api/interactive/ai_move',
                       data=json.dumps(payload),
                       content_type='application/json')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'move' in data
    assert data['move'] is not None
    assert 'word' in data['move']
    assert 'new_rack' in data
    assert 'evals' in data
    assert 'evaluated_moves' in data

    # Random AI move
    payload['ai_type'] = "random"
    resp_rand = client.post('/api/interactive/ai_move',
                            data=json.dumps(payload),
                            content_type='application/json')
    assert resp_rand.status_code == 200
    assert resp_rand.get_json()['move'] is not None


def test_static_and_spa_routing(client):
    # Root route returns HTML
    resp_root = client.get('/')
    assert resp_root.status_code == 200
    assert 'text/html' in resp_root.content_type

    # Client-side SPA route falls back to HTML index
    resp_spa = client.get('/interactive')
    assert resp_spa.status_code == 200
    assert 'text/html' in resp_spa.content_type
