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

    with open(replay_file, "r") as f:
        replay_data = json.load(f)

    assert "metadata" in replay_data
    assert "turns" in replay_data
    assert len(replay_data["turns"]) == 2
    assert replay_data["player_names"] == ["Alphable", "HastyBot"]


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
