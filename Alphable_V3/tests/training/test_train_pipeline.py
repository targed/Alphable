import os
import json
import pytest
from unittest.mock import MagicMock, patch

from alphable.training import train_supervised, train_rl
from alphable.pipeline import calibration_cycle


@pytest.fixture
def dummy_dataset(tmp_path):
    dataset_file = tmp_path / "dummy_samples.jsonl"
    lines = []
    # Create 8 simple samples
    for i in range(8):
        sample = {
            "board": "." * 225,
            "rack": "ABCDEFG",
            "score_diff": 10 * i,
            "bag": 86 - i,
            "target": 0.1 * i,
        }
        lines.append(json.dumps(sample))
    dataset_file.write_text("\n".join(lines))
    return str(dataset_file)


def test_train_supervised_validate_args(dummy_dataset):
    args = MagicMock()
    args.data = dummy_dataset
    args.train_split = 0.8
    args.epochs = 1
    args.batch_size = 2
    args.positive_weight = 1.0
    args.negative_weight = 1.0
    args.target_scale = 1.0
    args.early_stop_patience = 2
    args.resume_model = None

    # Should pass without error
    train_supervised.validate_args(args)

    # Invalid dataset path
    args.data = "non_existent_file.jsonl"
    with pytest.raises(FileNotFoundError):
        train_supervised.validate_args(args)

    # Invalid split
    args.data = dummy_dataset
    args.train_split = 1.5
    with pytest.raises(ValueError, match="train-split"):
        train_supervised.validate_args(args)

    # Invalid epochs
    args.train_split = 0.8
    args.epochs = 0
    with pytest.raises(ValueError, match="epochs"):
        train_supervised.validate_args(args)


def test_train_supervised_one_epoch_cpu(dummy_dataset, tmp_path):
    save_model_path = str(tmp_path / "supervised_test.pth")
    args = MagicMock()
    args.data = dummy_dataset
    args.save_dir = str(tmp_path)
    args.save_model = save_model_path
    args.resume_model = None
    args.batch_size = 2
    args.train_split = 0.75
    args.epochs = 1
    args.lr = 1e-3
    args.weight_decay = 1e-4
    args.scheduler_factor = 0.5
    args.scheduler_patience = 1
    args.positive_weight = 1.0
    args.negative_weight = 1.0
    args.target_scale = 1.0
    args.early_stop_patience = 2
    args.device = 'cpu'
    args.seed = 42

    train_supervised.train(args)

    assert os.path.exists(save_model_path)
    history_path = save_model_path.replace(".pth", "_history.json")
    assert os.path.exists(history_path)
    with open(history_path, "r") as f:
        hist = json.load(f)
    assert len(hist) == 1
    assert "train_loss" in hist[0]
    assert "val_loss" in hist[0]


def test_train_rl_one_epoch_cpu(dummy_dataset, tmp_path):
    save_model_path = str(tmp_path / "rl_test.pth")
    train_rl.train_rl(
        data_file=dummy_dataset,
        init_model_path=None,
        save_path=save_model_path,
        batch_size=2,
        lr=1e-3,
        weight_decay=1e-4,
        num_epochs=1,
        train_split=0.75,
        early_stopping_patience=2,
    )

    assert os.path.exists(save_model_path)
    history_path = save_model_path.replace(".pth", "_history.json")
    assert os.path.exists(history_path)


def test_calibration_cycle_build_commands():
    args = MagicMock()
    args.python = "python"
    args.games = 10
    args.rl_data = "data/rl.jsonl"
    args.selfplay_top_k = 3
    args.selfplay_temperature = 0.1
    args.infer_batch_size = 128
    args.append = True
    args.init_model = "init.pth"
    args.rl_model = "rl.pth"
    args.batch_size = 32
    args.lr = 1e-3
    args.weight_decay = 1e-4
    args.epochs = 5
    args.train_split = 0.9
    args.early_stop = 3
    args.bc_model = "bc.pth"
    args.eval_games = 10

    cmds = calibration_cycle.build_commands(args)
    assert len(cmds) == 3
    names = [name for name, _ in cmds]
    assert names == ["self_play", "train_rl", "evaluate"]
    # Check self_play command contains --append
    assert "--append" in cmds[0][1]


def test_calibration_cycle_run_and_tee(tmp_path):
    log_file = tmp_path / "test.log"
    # Run echo command
    rc, dur = calibration_cycle.run_and_tee(
        ["python", "-c", "print('hello calibration')"],
        cwd=str(tmp_path),
        log_path=str(log_file),
    )
    assert rc == 0
    assert dur >= 0
    assert log_file.exists()
    content = log_file.read_text()
    assert "hello calibration" in content


def test_calibration_cycle_main(tmp_path):
    with patch("alphable.pipeline.calibration_cycle.run_and_tee", return_value=(0, 0.5)), \
         patch("sys.argv", [
             "calibration_cycle.py",
             "--workspace", str(tmp_path),
             "--games", "1",
             "--eval-games", "1",
             "--logs-dir", "logs",
         ]):
        calibration_cycle.main()
        logs_dir = tmp_path / "logs"
        assert logs_dir.exists()
