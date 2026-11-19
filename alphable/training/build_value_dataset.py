"""
End-to-end Value Dataset Generation CLI for Alphable V4.

Coordinates ingestion of parsed matches and Macondo ground-truth equities,
validating sample integrity and producing train and validation splits.
"""

from __future__ import annotations
import os
import argparse
from alphable.training.macondo_distill import build_macondo_distillation_dataset


def main():
    parser = argparse.ArgumentParser(description="Build Alphable V4 Value Network Dataset")
    parser.add_argument(
        "--matches-dir",
        type=str,
        default="/home/targed/Documents/Git/Alphable/Alphable_V3/data/woogles/matches",
        help="Directory containing match_* folders with game.gcg and analysis.json",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/home/targed/Documents/Git/Alphable/Alphable_V4/data/value",
        help="Output directory for train_distilled.npz and val_distilled.npz",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Number of parallel worker processes",
    )
    parser.add_argument(
        "--val-split",
        type=float,
        default=0.1,
        help="Fraction of data reserved for validation (default 0.10)",
    )

    args = parser.parse_args()

    print("=== Alphable V4: Building Value Dataset ===")
    print(f"Source matches: {args.matches_dir}")
    print(f"Output directory: {args.output_dir}")

    n_train, n_val = build_macondo_distillation_dataset(
        matches_dir=args.matches_dir,
        output_dir=args.output_dir,
        max_workers=args.max_workers,
        val_split=args.val_split,
    )

    print(f"\nDataset build complete: {n_train} train samples, {n_val} validation samples.")


if __name__ == "__main__":
    main()
