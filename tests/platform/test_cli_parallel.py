"""
Tests for CLI parallel tournament options and invocation.
"""

from pathlib import Path
import pytest

from alphable_v4.cli import build_parser, cmd_tournament


def test_cli_parser_parallel_flags():
    """Verify that --parallel, --workers, --resume, and --checkpoint flags are accepted."""
    parser = build_parser()
    args = parser.parse_args([
        "tournament",
        "--model", "greedy",
        "--opponent", "magpie",
        "--games", "4",
        "--duplicate",
        "--parallel",
        "--workers", "4",
        "--resume",
        "--checkpoint", "data/tournaments/checkpoints/test.checkpoint.jsonl",
    ])
    
    assert args.command == "tournament"
    assert args.parallel is True
    assert args.workers == 4
    assert args.resume is True
    assert args.checkpoint == "data/tournaments/checkpoints/test.checkpoint.jsonl"


def test_cli_cmd_tournament_parallel_run(tmp_path: Path):
    """Verify end-to-end execution of cmd_tournament in parallel mode."""
    ckpt_file = tmp_path / "cli_test.checkpoint.jsonl"
    parser = build_parser()
    args = parser.parse_args([
        "tournament",
        "--model", "greedy",
        "--opponent", "magpie",
        "--games", "2",
        "--duplicate",
        "--parallel",
        "--workers", "2",
        "--checkpoint", str(ckpt_file),
        "--no-save",
    ])
    
    # Should execute without errors and populate checkpoint file
    cmd_tournament(args)
    assert ckpt_file.exists()
