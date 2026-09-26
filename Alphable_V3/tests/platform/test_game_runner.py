import json
import os
import pytest
from pathlib import Path
from alphable.platform.base import (
    AbstractPlatformAdapter,
    OnlineGameState,
    PlatformGameConfig,
    PlatformMove,
)
from alphable.platform.runner import OnlineGameRunner


class MockPlatformAdapter(AbstractPlatformAdapter):
    """Simulates an online game adapter for automated testing."""

    def __init__(self):
        self.game_over = False
        self.turns_played = 0
        self.moves_received: list[PlatformMove] = []
        self.board = [["." for _ in range(15)] for _ in range(15)]

    def start(self, headless: bool = False, user_data_dir: str = None) -> None:
        pass

    def ensure_logged_in(self) -> str:
        return "MockUser"

    def create_game(self, config: PlatformGameConfig) -> str:
        return "https://woogles.io/game/mock_12345"

    def get_game_state(self) -> OnlineGameState:
        return OnlineGameState(
            board=self.board,
            rack=["A", "B", "C", "D", "E", "F", "G"],
            my_score=50 * self.turns_played,
            opponent_score=45 * self.turns_played,
            my_name="Alphable",
            opponent_name="HastyBot",
            is_my_turn=True,
            bag_remaining=86 - (self.turns_played * 7),
            turn_number=self.turns_played + 1,
            is_game_over=self.game_over,
            winner="Alphable" if self.game_over else None,
        )

    def wait_for_my_turn(self, poll_interval: float = 0.5, timeout: float = 300.0) -> OnlineGameState:
        return self.get_game_state()

    def play_move(self, move: PlatformMove) -> bool:
        self.moves_received.append(move)
        self.turns_played += 1
        # Stop match after 2 turns for quick unit testing
        if self.turns_played >= 2:
            self.game_over = True
        return True

    def is_game_over(self) -> bool:
        return self.game_over

    def get_final_result(self) -> dict:
        return {
            "my_name": "Alphable",
            "opponent_name": "HastyBot",
            "my_score": 100,
            "opponent_score": 90,
            "winner": "Alphable",
            "url": "https://woogles.io/game/mock_12345",
        }

    def export_gcg(self, destination_path: str):
        p = Path(destination_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("#mock gcg\n>Alphable: A 8H CAT +10 10\n")
        return str(p)

    def extract_analysis(self) -> list:
        return [{"turn_title": "Turn 1", "suggestions": [{"coords": "8H", "word": "CAT", "points": 10, "leave": "DEFG", "equity": 15.2}]}]

    def trigger_rematch(self) -> bool:
        self.game_over = False
        self.turns_played = 0
        return True

    def close(self) -> None:
        pass


def test_online_game_runner_flow(tmp_path):
    mock_adapter = MockPlatformAdapter()
    output_dir = tmp_path / "games"

    runner = OnlineGameRunner(
        adapter=mock_adapter,
        model_path="models/alphable_v3_rl_gen2.pth",
        dict_path="resources/CSW24.txt",
        mode="lookahead",
        value_weight=60.0,
        delay_min=0.01,  # Fast test delay
        delay_max=0.02,
        output_dir=str(output_dir),
        num_simulations=2,
        top_k=2,
    )

    config = PlatformGameConfig(
        opponent_type="bot",
        bot_name="HastyBot",
        dictionary="CSW24",
        time_control="15+0",
    )

    summary = runner.play_match(config)

    assert summary["platform"] == "woogles"
    assert summary["opponent"] == "HastyBot"
    assert summary["winner"] == "Alphable"
    assert summary["turns_count"] == 2
    assert len(mock_adapter.moves_received) == 2

    # Verify replay file created
    replay_file = Path(summary["game_replay"])
    assert replay_file.exists()

    # Verify dedicated match directory contents
    match_folder = Path(summary["match_folder"])
    assert match_folder.exists()
    assert (match_folder / "replay.json").exists()
    assert (match_folder / "game.gcg").exists()
    assert (match_folder / "analysis.json").exists()
    assert (match_folder / "summary.json").exists()

    with open(replay_file, "r") as f:
        replay_data = json.load(f)

    assert "metadata" in replay_data
    assert "turns" in replay_data
    assert len(replay_data["turns"]) == 2
    assert replay_data["player_names"] == ["Alphable", "HastyBot"]
    assert replay_data["analysis_turns_count"] == 1


def test_platform_game_over_immediate(tmp_path):
    mock_adapter = MockPlatformAdapter()
    mock_adapter.game_over = True
    output_dir = tmp_path / "games"

    runner = OnlineGameRunner(
        adapter=mock_adapter,
        model_path="models/alphable_v3_rl_gen2.pth",
        dict_path="resources/CSW24.txt",
        mode="greedy",
        output_dir=str(output_dir),
    )

    config = PlatformGameConfig(
        opponent_type="bot",
        bot_name="HastyBot",
        dictionary="CSW24",
    )

    summary = runner.play_match(config)
    assert summary["turns_count"] == 0
    assert summary["winner"] == "Alphable"


def test_multi_game_series_flow(tmp_path):
    mock_adapter = MockPlatformAdapter()
    output_dir = tmp_path / "games"

    runner = OnlineGameRunner(
        adapter=mock_adapter,
        model_path="models/alphable_v3_rl_gen2.pth",
        dict_path="resources/CSW24.txt",
        mode="greedy",
        delay_min=0.01,
        delay_max=0.01,
        output_dir=str(output_dir),
    )

    config = PlatformGameConfig(
        opponent_type="bot",
        bot_name="STEEBot",
        dictionary="CSW24",
        num_games=2,
        export_gcg=True,
        extract_analysis=True,
    )

    series_summary = runner.play_match(config)
    assert series_summary["total_games"] == 2
    assert series_summary["alphable_wins"] == 2
    assert len(series_summary["games"]) == 2

    # Both matches should have created their own dedicated folders
    for game in series_summary["games"]:
        match_folder = Path(game["match_folder"])
        assert match_folder.exists()
        assert (match_folder / "game.gcg").exists()
        assert (match_folder / "analysis.json").exists()


class FailingMoveMockAdapter(MockPlatformAdapter):
    """Adapter where PLAY moves fail to test retries, but PASS succeeds."""
    def __init__(self):
        super().__init__()
        self.play_attempts = 0
        self.recall_tiles_count = 0

    def recall_tiles(self):
        self.recall_tiles_count += 1

    def play_move(self, move: PlatformMove) -> bool:
        self.moves_received.append(move)
        if move.action == "PLAY":
            self.play_attempts += 1
            return False  # Simulate platform rejection
        elif move.action == "PASS":
            self.turns_played += 1
            self.game_over = True
            return True
        return False


def test_online_game_runner_retry_and_pass_fallback(tmp_path):
    failing_adapter = FailingMoveMockAdapter()
    output_dir = tmp_path / "games_retry"

    runner = OnlineGameRunner(
        adapter=failing_adapter,
        model_path="models/alphable_v3_rl_gen2.pth",
        dict_path="resources/CSW24.txt",
        mode="greedy",
        delay_min=0.01,
        delay_max=0.01,
        output_dir=str(output_dir),
    )

    config = PlatformGameConfig(
        opponent_type="bot",
        bot_name="HastyBot",
        dictionary="CSW24",
        num_games=1,
        export_gcg=False,
        extract_analysis=False,
    )

    summary = runner.play_match(config)
    # Runner should have attempted PLAY 3 times, recalled tiles 3 times, and then successfully passed
    assert failing_adapter.play_attempts == 3
    assert failing_adapter.recall_tiles_count >= 3
    # Check that the last submitted move was PASS
    assert failing_adapter.moves_received[-1].action == "PASS"
    assert summary["winner"] == "Alphable"


class CrashingFirstGameAdapter(MockPlatformAdapter):
    """Adapter where game 1 throws TimeoutError during create_game, but game 2 succeeds."""
    def __init__(self):
        super().__init__()
        self.game_count = 0
        self.reset_to_lobby_called = 0

    def create_game(self, config: PlatformGameConfig) -> str:
        self.game_count += 1
        if self.game_count == 1:
            raise TimeoutError("Locator.click: Timeout 15000ms exceeded. waiting for locator('.bot').first")
        return "https://woogles.io/game/mock_game_2"

    def reset_to_lobby(self):
        self.reset_to_lobby_called += 1


def test_online_game_runner_series_error_isolation(tmp_path):
    crashing_adapter = CrashingFirstGameAdapter()
    output_dir = tmp_path / "games_series_crash"

    runner = OnlineGameRunner(
        adapter=crashing_adapter,
        model_path="models/alphable_v3_rl_gen2.pth",
        dict_path="resources/CSW24.txt",
        mode="greedy",
        delay_min=0.01,
        delay_max=0.01,
        output_dir=str(output_dir),
    )

    config = PlatformGameConfig(
        opponent_type="bot",
        bot_name="HastyBot",
        dictionary="CSW24",
        num_games=2,
        export_gcg=False,
        extract_analysis=False,
    )

    series_summary = runner.play_match(config)
    # The runner must NOT crash! It should record game 1 error, reset to lobby, and successfully play game 2
    assert series_summary["total_games"] == 2
    assert series_summary["completed_games"] == 2
    assert len(series_summary["games"]) == 2
    assert "error" in series_summary["games"][0]["status"]
    assert series_summary["games"][1]["winner"] == "Alphable"
    assert crashing_adapter.reset_to_lobby_called >= 1

