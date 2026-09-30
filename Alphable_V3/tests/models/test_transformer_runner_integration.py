"""
Integration test for OnlineGameRunner with mode='transformer'.
"""

import pytest
from unittest.mock import MagicMock, patch
from alphable.platform.runner import OnlineGameRunner
from alphable.platform.base import PlatformGameConfig
from tests.platform.test_game_runner import MockPlatformAdapter


def test_runner_transformer_mode_initialization():
    mock_adapter = MockPlatformAdapter()
    with patch("alphable.models.transformer_ranker.SmolLM2CandidateRanker") as MockRanker:
        runner = OnlineGameRunner(
            adapter=mock_adapter,
            mode="transformer",
            dict_path="resources/CSW24.txt",
        )
        assert runner.mode == "transformer"
        assert runner.transformer_ranker is not None
        MockRanker.assert_called_once()


def test_runner_transformer_mode_move_selection(tmp_path):
    mock_adapter = MockPlatformAdapter()
    mock_ranker = MagicMock()
    chosen_move = {"row": 7, "col": 7, "dir": "Across", "word": "CAT"}
    mock_ranker.select_best_move.return_value = chosen_move

    with patch("alphable.models.transformer_ranker.SmolLM2CandidateRanker", return_value=mock_ranker):
        runner = OnlineGameRunner(
            adapter=mock_adapter,
            mode="transformer",
            dict_path="resources/CSW24.txt",
            output_dir=str(tmp_path / "games"),
            delay_min=0.0,
            delay_max=0.0,
        )

        config = PlatformGameConfig(num_games=1, bot_name="HastyBot")
        res = runner.play_match(config)

        assert res["turns_count"] >= 1
        assert mock_ranker.select_best_move.called
        assert len(mock_adapter.moves_received) >= 1
