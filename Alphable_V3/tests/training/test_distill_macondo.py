import os
import json
import pytest
import torch

from alphable.training.distill_macondo import (
    parse_position,
    extract_match_samples,
    train_macondo_distillation,
)


def test_parse_position():
    r, c, d = parse_position("8G")
    assert r == 7
    assert c == 6
    assert d == "Across"

    r, c, d = parse_position("H13")
    assert r == 12
    assert c == 7
    assert d == "Down"

    r, c, d = parse_position("invalid")
    assert r is None


def test_extract_match_samples_mock(tmp_path):
    match_dir = tmp_path / "mock_match"
    match_dir.mkdir()

    gcg_file = match_dir / "game.gcg"
    analysis_file = match_dir / "analysis.json"

    gcg_content = (
        "#player1 Bot1 Bot1\n"
        "#player2 Bot2 Bot2\n"
        ">Bot1: DEEFOSW 8G FEW +18 18\n"
        ">Bot2: ABCEEST 9F CETE +22 22\n"
    )
    gcg_file.write_text(gcg_content)

    analysis_content = [
        {
            "turn_title": "Turn 1",
            "rack": ["D", "E", "E", "F", "O", "S", "W"],
            "suggestions": [{"coords": "8G", "word": "FEW", "points": 18, "equity": 31.5}]
        },
        {
            "turn_title": "Turn 2",
            "rack": ["A", "B", "C", "E", "E", "S", "T"],
            "suggestions": [{"coords": "9F", "word": "CETE", "points": 22, "equity": 25.0}]
        },
    ]
    analysis_file.write_text(json.dumps(analysis_content))

    samples = extract_match_samples(str(match_dir))
    assert len(samples) == 2
    assert samples[0]["board"].shape == (31, 15, 15)
    assert samples[0]["state"].shape == (36,)
    assert samples[0]["target"].shape == (1,)
    assert -1.0 <= samples[0]["target"].item() <= 1.0


def test_train_distillation_smoke(tmp_path):
    # Create synthetic samples
    samples = []
    for _ in range(16):
        b = torch.randn(31, 15, 15)
        s = torch.randn(36)
        t = torch.tensor([0.5], dtype=torch.float32)
        samples.append({"board": b, "state": s, "target": t})

    out_model = str(tmp_path / "test_distilled.pth")
    saved_path = train_macondo_distillation(
        base_model_path="nonexistent.pth",
        output_model_path=out_model,
        samples=samples,
        epochs=1,
        batch_size=8,
        device="cpu",
    )

    assert os.path.exists(saved_path)
    state = torch.load(saved_path, map_location="cpu")
    assert "conv_input.0.weight" in state
