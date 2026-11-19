"""
Fault-Tolerant Tournament Checkpointing and Recovery.

Provides atomic, append-only JSONL streaming for tournament match pairs to ensure
zero progress loss during SLURM cluster preemption, walltime expiration, or SIGINT.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple, Optional


class TournamentCheckpointManager:
    """Manages incremental journal checkpointing for tournament runs."""

    def __init__(
        self,
        checkpoint_path: str | Path,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.path = Path(checkpoint_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata: Dict[str, Any] = {}

        if not self.path.exists() or self.path.stat().st_size == 0:
            if metadata is not None:
                self.metadata = dict(metadata)
                header = {"type": "metadata", **self.metadata}
                with open(self.path, "w", encoding="utf-8") as f:
                    f.write(json.dumps(header) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
        else:
            # Read metadata from existing file
            self._read_metadata()

    def _read_metadata(self) -> None:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return
        with open(self.path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            if first_line:
                try:
                    obj = json.loads(first_line)
                    if obj.get("type") == "metadata":
                        self.metadata = {k: v for k, v in obj.items() if k != "type"}
                except Exception:
                    pass

    def is_resumable(self) -> bool:
        """Returns True if the checkpoint file exists and has data."""
        return self.path.exists() and self.path.stat().st_size > 0

    def record_pair(self, pair_record: Dict[str, Any]) -> None:
        """Atomically appends and syncs a completed duplicate pair record."""
        line = json.dumps(pair_record) + "\n"
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())

    def load_completed_pairs(self) -> Tuple[Set[int], List[Dict[str, Any]]]:
        """
        Reads all valid completed pair records from the checkpoint journal.

        Returns:
            Tuple of (completed_seed_set, completed_records_list).
        """
        if not self.path.exists():
            return set(), []

        completed_seeds: Set[int] = set()
        records: List[Dict[str, Any]] = []

        with open(self.path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    # Incomplete write / corruption at tail; ignore damaged line
                    continue

                if obj.get("type") == "metadata":
                    continue

                if "seed" in obj:
                    seed = int(obj["seed"])
                    completed_seeds.add(seed)
                    records.append(obj)

        return completed_seeds, records

    def is_complete(self, total_pairs: int) -> bool:
        """Checks if all scheduled pairs have been recorded."""
        completed_seeds, _ = self.load_completed_pairs()
        return len(completed_seeds) >= total_pairs
