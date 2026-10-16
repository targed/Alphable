"""
Macondo Ground-Truth Knowledge Distillation Pipeline for Alphable V4.

Extracts grandmaster-evaluated board states and equities from completed
matches (containing game.gcg and analysis.json), applies continuous deficit
labeling, and outputs high-performance training tensors for the V4 Value Network.
"""

from __future__ import annotations
import os
import glob
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import torch
import pandas as pd
from tqdm import tqdm

from alphable_v4.engine.game_state import GameState
from alphable_v4.training.parse_gcg import parse_gcg_file, ParsedGame, ParsedTurn


def extract_match_distillation_samples(match_dir: str) -> List[Dict[str, Any]]:
    """
    Extracts (board_tensor, state_vector, target_value, raw_equity) samples
    from a single match directory containing game.gcg and analysis.json.
    """
    gcg_file = os.path.join(match_dir, "game.gcg")
    analysis_file = os.path.join(match_dir, "analysis.json")

    if not (os.path.exists(gcg_file) and os.path.exists(analysis_file)):
        return []

    try:
        with open(analysis_file, "r", encoding="utf-8", errors="ignore") as f:
            analysis_data = json.load(f)
    except Exception:
        return []

    if not analysis_data or not isinstance(analysis_data, list):
        return []

    game = parse_gcg_file(gcg_file)
    if not game or not game.turns:
        return []

    samples: List[Dict[str, Any]] = []
    turn_limit = min(len(game.turns), len(analysis_data))

    for t_idx in range(turn_limit):
        turn = game.turns[t_idx]
        ana_turn = analysis_data[t_idx]
        suggestions = ana_turn.get("suggestions", [])
        if not suggestions:
            continue

        # Top equity from Macondo analysis
        top_equity = float(suggestions[0].get("equity", 0.0))

        # Macondo equity normalized via tanh: typical equity range [-50, +50] pts
        v_macondo = float(np.tanh(top_equity / 50.0))

        # Final game outcome margin normalized via tanh
        v_outcome = float(np.tanh(turn.final_margin / 100.0))

        # Combined anchored regression target: 75% grandmaster equity + 25% game outcome
        v_target = 0.75 * v_macondo + 0.25 * v_outcome

        # Reconstruct GameState from before_cgp
        try:
            state = GameState.from_cgp(turn.board_before_cgp)
            board_tensor = state.to_board_tensor().numpy()  # (32, 15, 15)
            state_vector = state.to_state_vector().numpy()   # (64,)
        except Exception:
            continue

        samples.append({
            "game_id": game.game_id,
            "turn_index": t_idx,
            "board_tensor": board_tensor,
            "state_vector": state_vector,
            "target": v_target,
            "raw_equity": top_equity,
            "margin": turn.final_margin,
            "lexicon": game.lexicon,
        })

    return samples


def process_match_batch(match_dirs: List[str]) -> List[Dict[str, Any]]:
    """Helper for batch multiprocessing."""
    batch_samples = []
    for d in match_dirs:
        samples = extract_match_distillation_samples(d)
        batch_samples.extend(samples)
    return batch_samples


def build_macondo_distillation_dataset(
    matches_dir: str,
    output_dir: str,
    max_workers: int = 4,
    val_split: float = 0.1,
) -> Tuple[int, int]:
    """
    Scans matches_dir for match_* directories, extracts distillation samples,
    and saves train and val datasets as compressed .npz / .parquet files.
    """
    os.makedirs(output_dir, exist_ok=True)
    pattern = os.path.join(matches_dir, "match_*")
    all_match_dirs = sorted(glob.glob(pattern))

    print(f"Found {len(all_match_dirs)} candidate match directories in {matches_dir}")
    if not all_match_dirs:
        print("No matches found.")
        return 0, 0

    all_samples: List[Dict[str, Any]] = []

    # Chunk match directories for parallel processing
    chunk_size = max(1, len(all_match_dirs) // (max_workers * 4))
    chunks = [
        all_match_dirs[i : i + chunk_size]
        for i in range(0, len(all_match_dirs), chunk_size)
    ]

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_match_batch, c) for c in chunks]
        for f in tqdm(as_completed(futures), total=len(futures), desc="Extracting samples"):
            try:
                batch = f.result()
                all_samples.extend(batch)
            except Exception as e:
                print(f"Batch failed: {e}")

    total_samples = len(all_samples)
    print(f"Total distilled samples extracted: {total_samples}")
    if total_samples == 0:
        return 0, 0

    # Shuffle and split into train/val
    np.random.seed(42)
    indices = np.random.permutation(total_samples)
    val_count = int(total_samples * val_split)
    train_indices = indices[val_count:]
    val_indices = indices[:val_count]

    # Package into compressed numpy arrays
    def save_split(split_indices, filename):
        boards = np.stack([all_samples[i]["board_tensor"] for i in split_indices])
        states = np.stack([all_samples[i]["state_vector"] for i in split_indices])
        targets = np.array([all_samples[i]["target"] for i in split_indices], dtype=np.float32)
        equities = np.array([all_samples[i]["raw_equity"] for i in split_indices], dtype=np.float32)

        out_path = os.path.join(output_dir, filename)
        np.savez_compressed(
            out_path,
            board_tensors=boards,
            state_vectors=states,
            targets=targets,
            raw_equities=equities,
        )
        print(f"Saved {len(split_indices)} samples to {out_path} ({os.path.getsize(out_path) / (1024*1024):.2f} MB)")

    save_split(train_indices, "train_distilled.npz")
    save_split(val_indices, "val_distilled.npz")

    return len(train_indices), len(val_indices)
