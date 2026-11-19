"""
Tests for TournamentCheckpointManager.
"""

import json
from pathlib import Path
import pytest

from alphable.platform.checkpoint import TournamentCheckpointManager


def test_checkpoint_initialization_and_metadata(tmp_path: Path):
    ckpt_path = tmp_path / "test_run.checkpoint.jsonl"
    metadata = {
        "run_id": "test_run_123",
        "p1_name": "Player 1",
        "p2_name": "Player 2",
        "total_pairs": 5,
        "mode": "duplicate",
    }
    
    mgr = TournamentCheckpointManager(ckpt_path, metadata=metadata)
    assert ckpt_path.exists()
    assert mgr.is_resumable()
    
    completed_seeds, completed_records = mgr.load_completed_pairs()
    assert len(completed_seeds) == 0
    assert len(completed_records) == 0


def test_checkpoint_record_pair_and_resume(tmp_path: Path):
    ckpt_path = tmp_path / "test_run.checkpoint.jsonl"
    metadata = {
        "run_id": "test_run_123",
        "total_pairs": 3,
    }
    
    mgr = TournamentCheckpointManager(ckpt_path, metadata=metadata)
    
    pair1 = {
        "pair": 1,
        "seed": 1000,
        "p1_pair_total": 800,
        "p2_pair_total": 750,
        "net_spread": 50,
        "verdict": "P1 WON MATCH",
    }
    mgr.record_pair(pair1)
    
    # Reload from checkpoint file (simulate interruption and resume)
    mgr_resumed = TournamentCheckpointManager(ckpt_path)
    completed_seeds, records = mgr_resumed.load_completed_pairs()
    
    assert 1000 in completed_seeds
    assert len(records) == 1
    assert records[0]["seed"] == 1000
    assert records[0]["net_spread"] == 50
    assert not mgr_resumed.is_complete(total_pairs=3)
    
    # Record remaining pairs
    pair2 = {"pair": 2, "seed": 1031, "p1_pair_total": 780, "p2_pair_total": 810, "net_spread": -30, "verdict": "P2 WON MATCH"}
    pair3 = {"pair": 3, "seed": 1062, "p1_pair_total": 820, "p2_pair_total": 820, "net_spread": 0, "verdict": "MATCH TIED"}
    mgr_resumed.record_pair(pair2)
    mgr_resumed.record_pair(pair3)
    
    assert mgr_resumed.is_complete(total_pairs=3)


def test_checkpoint_handles_corrupt_line(tmp_path: Path):
    ckpt_path = tmp_path / "corrupt.checkpoint.jsonl"
    with open(ckpt_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "metadata", "total_pairs": 2}) + "\n")
        f.write(json.dumps({"pair": 1, "seed": 1000, "net_spread": 20}) + "\n")
        # Incomplete/corrupt JSON line from crash:
        f.write('{"pair": 2, "seed": 1031, "net_spread":\n')
        
    mgr = TournamentCheckpointManager(ckpt_path)
    completed_seeds, records = mgr.load_completed_pairs()
    assert 1000 in completed_seeds
    assert 1031 not in completed_seeds
    assert len(records) == 1
