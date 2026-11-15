#!/usr/bin/env python3
"""
Salvage completed duplicate tournament pairs from SLURM output log (Mill-*.out)
and reconstruct the incremental checkpoint journal.
"""

import re
import json
from pathlib import Path

LOG_FILE = Path("Mill-2747300.out")
CKPT_FILE = Path("data/tournaments/checkpoints/hybrid-pimc_vs_magpie-tuned_10k-hpc.checkpoint.jsonl")


def salvage():
    if not LOG_FILE.exists():
        print(f"Log file {LOG_FILE} not found.")
        return

    pattern = re.compile(
        r"Pair\s+(\d+)/\d+\s+\[Seed\s+(\d+)\]:\s+(\S+)\s+(\d+)\+(\d+)=(\d+)\s+pts\s+vs\s+(\S+)\s+(\d+)\+(\d+)=(\d+)\s+pts\s+\|\s+Net:\s+([+-]?\d+)\s+pts\s+\|\s+(.*)"
    )

    records = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            m = pattern.match(line.strip())
            if m:
                pair_num = int(m.group(1))
                seed = int(m.group(2))
                p1_short = m.group(3)
                p1_gA = int(m.group(4))
                p1_gB = int(m.group(5))
                p1_total = int(m.group(6))
                p2_short = m.group(7)
                p2_gA = int(m.group(8))
                p2_gB = int(m.group(9))
                p2_total = int(m.group(10))
                net = int(m.group(11))
                verdict = m.group(12)

                rec = {
                    "pair": pair_num,
                    "seed": seed,
                    "p1_name": "Alphable V4 Hybrid PIMC (Native Simulation + Neural Re-Ranking)",
                    "p1_short": p1_short,
                    "p2_name": "Maximally Tuned Base MAGPIE (PAT + PIMC + Endgame)",
                    "p2_short": p2_short,
                    "p1_gameA_score": p1_gA,
                    "p1_gameB_score": p1_gB,
                    "p1_pair_total": p1_total,
                    "p2_gameA_score": p2_gA,
                    "p2_gameB_score": p2_gB,
                    "p2_pair_total": p2_total,
                    "net_spread": net,
                    "phase_spreads": {},
                    "verdict": verdict,
                }
                records.append(rec)

    print(f"Parsed {len(records)} completed pairs from {LOG_FILE}.")

    # Read existing metadata or construct default
    meta = {
        "type": "metadata",
        "p1_spec": "hybrid-pimc",
        "p2_spec": "magpie-tuned",
        "total_pairs": 5000,
        "lexicon": "CSW24",
        "start_seed": 1000,
        "seed_stride": 31,
    }

    # Backup existing checkpoint if present
    if CKPT_FILE.exists():
        backup_file = CKPT_FILE.with_suffix(".jsonl.bak")
        CKPT_FILE.rename(backup_file)
        print(f"Backed up existing checkpoint to {backup_file}.")

    # Write all recovered pairs
    with open(CKPT_FILE, "w", encoding="utf-8") as f:
        f.write(json.dumps(meta) + "\n")
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    print(f"Successfully recovered {len(records)} pairs to {CKPT_FILE}!")


if __name__ == "__main__":
    salvage()
