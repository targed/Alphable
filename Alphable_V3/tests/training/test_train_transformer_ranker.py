"""
Unit tests for SmolLM2 Scrabble candidate ranker training pipeline.
"""

import json
import os
import pytest
import torch
from transformers import AutoTokenizer

from alphable.training.train_transformer_ranker import (
    extract_match_ranking_samples,
    collate_ranking_batch,
    ScrabbleRankingDataset,
)


def test_extract_match_ranking_samples_mock(tmp_path):
    match_dir = tmp_path / "mock_match"
    match_dir.mkdir()
    analysis_file = match_dir / "analysis.json"

    mock_analysis = [
        {
            "turn_title": "Turn 1",
            "rack": ["A", "E", "I", "R", "S", "T", "Z"],
            "suggestions": [
                {"coords": "8D", "word": "RETIZAS", "points": 90, "leave": "", "equity": 95.0},
                {"coords": "8G", "word": "ZA", "points": 22, "leave": "EIRST", "equity": 40.0},
                {"coords": "8G", "word": "AT", "points": 4, "leave": "EIRSZ", "equity": 15.0},
            ],
        },
        {
            "turn_title": "Turn 2",
            "rack": ["Q"],
            "suggestions": [
                {"coords": "8A", "word": "QI", "points": 11, "leave": "", "equity": 10.0}
            ],  # Only 1 candidate -> should be skipped
        },
    ]

    analysis_file.write_text(json.dumps(mock_analysis))

    samples = extract_match_ranking_samples(str(match_dir), max_candidates_per_turn=4)
    assert len(samples) == 1
    sample = samples[0]

    assert "<|im_start|>system" in sample["prompt"]
    assert "Hand Rack: [AEIRSTZ]" in sample["prompt"]
    assert sample["num_candidates"] == 3
    assert 0 <= sample["target_label_idx"] < 3
    # Target candidate should be RETIZAS
    target_label = chr(ord('A') + sample["target_label_idx"])
    assert f"[{target_label}] 8D RETIZAS" in sample["prompt"]


def test_collate_ranking_batch():
    item1 = {
        "input_ids": torch.tensor([1, 2, 3]),
        "attention_mask": torch.tensor([1, 1, 1]),
        "target_label_idx": torch.tensor(1),
    }
    item2 = {
        "input_ids": torch.tensor([4, 5]),
        "attention_mask": torch.tensor([1, 1]),
        "target_label_idx": torch.tensor(0),
    }

    batch = collate_ranking_batch([item1, item2], pad_token_id=0)
    assert batch["input_ids"].shape == (2, 3)
    assert batch["attention_mask"].shape == (2, 3)
    assert torch.equal(batch["input_ids"][1], torch.tensor([4, 5, 0]))
    assert torch.equal(batch["attention_mask"][1], torch.tensor([1, 1, 0]))
    assert torch.equal(batch["target_label_idx"], torch.tensor([1, 0]))
