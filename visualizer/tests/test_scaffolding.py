import os
from pathlib import Path

def test_visualizer_directory_structure():
    vis_dir = Path(__file__).resolve().parent.parent
    assert (vis_dir / "requirements.txt").exists(), "requirements.txt should exist"
    assert (vis_dir / "backend").is_dir(), "backend dir should exist"
    assert (vis_dir / "backend" / "adapters").is_dir(), "adapters dir should exist"
    assert (vis_dir / "backend" / "services").is_dir(), "services dir should exist"
