import sys
from unittest.mock import patch, MagicMock
import pytest

from alphable.cli import main as cli_main


def test_cli_help(capsys):
    with patch("sys.argv", ["alphable"]):
        cli_main.main()
    captured = capsys.readouterr()
    assert "Alphable V3 CLI" in captured.out or "usage:" in captured.out


@pytest.mark.parametrize("subcommand_args,mock_target", [
    (["data", "prepare"], "alphable.training.prepare_dataset.main"),
    (["train", "supervised"], "alphable.training.train_supervised.main"),
    (["train", "rl"], "alphable.training.train_rl.main"),
    (["train", "rl-selfplay"], "alphable.training.self_play_rl.main"),
    (["selfplay", "generate"], "alphable.training.self_play.main"),
    (["eval", "matches"], "alphable.eval.evaluate_matches.main"),
    (["eval", "baseline"], "alphable.eval.evaluate_vs_baseline.main"),
    (["eval", "plot"], "alphable.eval.analyze.main"),
    (["pipeline", "calibrate"], "alphable.pipeline.calibration_cycle.main"),
    (["search", "debug"], "alphable.core.search.main"),
])
def test_cli_routes(subcommand_args, mock_target):
    with patch("sys.argv", ["alphable"] + subcommand_args), \
         patch(mock_target) as mock_func:
        cli_main.main()
        assert mock_func.called
