import os
import json
import tempfile
from alphable.eval.analyze import plot_loss_history


def test_plot_loss_history():
    with tempfile.TemporaryDirectory() as tmpdir:
        history_path = os.path.join(tmpdir, "history.json")
        out_png = os.path.join(tmpdir, "plot.png")

        sample_data = [
            {"epoch": 1, "train_loss": 0.5, "val_loss": 0.4, "time": 10.0},
            {"epoch": 2, "train_loss": 0.3, "val_loss": 0.35, "time": 10.0},
        ]
        with open(history_path, "w") as f:
            json.dump(sample_data, f)

        plot_loss_history(history_path, out_png, "Test Plot")
        assert os.path.exists(out_png)
        assert os.path.getsize(out_png) > 1000
