import json
import pytest
import torch
from alphable.data.dataset import AlphableDataset, get_dataloaders


def test_alphable_dataset_loading_and_shapes(tmp_path):
    # Create sample JSONL file
    sample_file = tmp_path / "samples.jsonl"
    samples = [
        {
            'board': '.' * 225,
            'rack': 'ABCDEFG',
            'score_diff': 15,
            'bag': 86,
            'target': 1.0,
        },
        {
            'board': 'CAT' + '.' * 222,
            'rack': 'DOG',
            'score_diff': -10,
            'bag': 70,
            'target': -0.5,
        },
        # Empty line to verify graceful skip
        "",
        # Corrupt line to verify graceful skip
        "{invalid json",
        {
            'board': '.' * 220, # Short board to verify auto-padding
            'rack': '?',
            'score_diff': 0,
            'bag': 10,
            'target': 0.8,
        },
    ]

    with open(sample_file, 'w', encoding='utf-8') as f:
        for s in samples:
            if isinstance(s, dict):
                f.write(json.dumps(s) + '\n')
            else:
                f.write(s + '\n')

    dataset = AlphableDataset(str(sample_file))
    assert len(dataset) == 3

    # Check item 0
    b0, s0, t0 = dataset[0]
    assert b0.shape == (31, 15, 15)
    assert s0.shape == (36,)
    assert t0.shape == (1,)
    assert t0.item() == 1.0

    # Check item 1
    b1, s1, t1 = dataset[1]
    assert b1.shape == (31, 15, 15)
    assert s1.shape == (36,)
    assert t1.item() == -0.5


def test_get_dataloaders(tmp_path):
    sample_file = tmp_path / "dataloader_test.jsonl"
    with open(sample_file, 'w', encoding='utf-8') as f:
        for i in range(20):
            sample = {
                'board': '.' * 225,
                'rack': 'RACK',
                'score_diff': i,
                'bag': 80 - i,
                'target': float(i) / 20.0,
            }
            f.write(json.dumps(sample) + '\n')

    train_loader, val_loader = get_dataloaders(str(sample_file), batch_size=4, train_split=0.8)
    assert len(train_loader.dataset) == 16
    assert len(val_loader.dataset) == 4

    for boards, states, targets in train_loader:
        assert boards.shape[1:] == (31, 15, 15)
        assert states.shape[1:] == (36,)
        assert targets.shape[1:] == (1,)
        break
