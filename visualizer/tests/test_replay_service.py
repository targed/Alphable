import pytest
from visualizer.backend.services.replay_service import ReplayService

def test_replay_discovery():
    service = ReplayService()
    games = service.list_all_games()
    assert isinstance(games, list)
    if len(games) > 0:
        g0 = games[0]
        assert "id" in g0
        assert "category" in g0
        assert "final_score" in g0
        assert "player_names" in g0

def test_load_single_game():
    service = ReplayService()
    games = service.list_all_games()
    # Find a game from vs_greedy or vs_nn
    v3_game = next((g for g in games if g["category"] in ("vs_greedy", "vs_nn", "matches", "results")), None)
    if v3_game:
        data = service.get_game_details(v3_game["category"], v3_game["filename"])
        assert data is not None
        assert "turns" in data
        assert len(data["turns"]) > 0

def test_v4_tournament_discovery():
    service = ReplayService()
    tourneys = service.list_v4_tournaments()
    assert isinstance(tourneys, list)
    assert len(tourneys) > 0
    t0 = tourneys[0]
    assert "run_id" in t0
    assert "total_games" in t0
    assert "win_rate" in t0
