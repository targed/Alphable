"""
Tests for Parallel Duplicate Tournament Engine and Multi-Process Scaling.
"""

from pathlib import Path
import pytest

from alphable.platform.eval import run_parallel_duplicate_tournament, _run_duplicate_pair_worker
from alphable.platform.checkpoint import TournamentCheckpointManager


def test_run_duplicate_pair_worker():
    """Verifies that an isolated worker executes Game A & Game B for a pair."""
    task = {
        "pair_idx": 0,
        "seed": 1000,
        "p1_spec": "greedy",
        "p2_spec": "magpie",
        "lexicon": "CSW24",
        "device": "cpu",
        "p1_kwargs": {},
        "p2_kwargs": {},
        "p1_model_path": None,
        "p2_model_path": None,
    }
    
    res = _run_duplicate_pair_worker(task)
    assert res["pair"] == 1
    assert res["seed"] == 1000
    assert "p1_pair_total" in res
    assert "p2_pair_total" in res
    assert "net_spread" in res
    assert "verdict" in res
    assert "phase_spreads" in res
    assert res["p1_pair_total"] == res["p1_gameA_score"] + res["p1_gameB_score"]
    assert res["p2_pair_total"] == res["p2_gameA_score"] + res["p2_gameB_score"]


def test_run_parallel_duplicate_tournament(tmp_path: Path):
    """Verifies multi-process duplicate tournament runs and aggregates statistics."""
    ckpt_file = tmp_path / "parallel_test.checkpoint.jsonl"
    
    result = run_parallel_duplicate_tournament(
        p1_spec="greedy",
        p2_spec="magpie",
        num_pairs=2,
        workers=2,
        lexicon="CSW24",
        device="cpu",
        checkpoint_path=str(ckpt_file),
        verbose=False,
    )
    
    assert result["total_games"] == 4
    assert result["duplicate_pairs"] == 2
    assert len(result["pair_records"]) == 2
    assert ckpt_file.exists()
    
    # Verify checkpoint manager confirms completion
    mgr = TournamentCheckpointManager(ckpt_file)
    assert mgr.is_complete(total_pairs=2)


def test_parallel_tournament_resume(tmp_path: Path):
    """Verifies that resuming skips completed pairs and finishes tournament."""
    ckpt_file = tmp_path / "resume_test.checkpoint.jsonl"
    
    # 1. Run 1 pair first
    res1 = run_parallel_duplicate_tournament(
        p1_spec="greedy",
        p2_spec="magpie",
        num_pairs=1,
        workers=1,
        lexicon="CSW24",
        device="cpu",
        checkpoint_path=str(ckpt_file),
        verbose=False,
    )
    assert len(res1["pair_records"]) == 1
    
    # 2. Resume requesting 2 pairs total
    res2 = run_parallel_duplicate_tournament(
        p1_spec="greedy",
        p2_spec="magpie",
        num_pairs=2,
        workers=2,
        lexicon="CSW24",
        device="cpu",
        checkpoint_path=str(ckpt_file),
        resume=True,
        verbose=False,
    )
    assert res2["duplicate_pairs"] == 2
    assert len(res2["pair_records"]) == 2
    seeds = [r["seed"] for r in res2["pair_records"]]
    assert seeds == [1000, 1031]
