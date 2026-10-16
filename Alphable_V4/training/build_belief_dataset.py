"""
Dataset Builder for Opponent Hidden Rack Belief Network.

Extracts (visible_state, ground_truth_opponent_rack) pairs from parsed GCG games.
Used for training and evaluating opponent rack prediction models.
"""

from __future__ import annotations
import os
import glob
from typing import List, Dict, Tuple, Optional, Any
import numpy as np
import torch
from tqdm import tqdm

from alphable_v4.engine.game_state import GameState, STANDARD_TILE_COUNTS
from alphable_v4.training.parse_gcg import parse_gcg_file, ParsedGame


def extract_game_belief_samples(game: ParsedGame) -> List[Dict[str, Any]]:
    """
    Extracts belief training pairs from a parsed game.
    For each turn, visible state contains:
    - Board tensor (32 channels)
    - State vector (64 dimensions)
    - Target: Ground truth opponent rack (27-dim count vector for A-Z + blank)
    """
    samples: List[Dict[str, Any]] = []
    turns = game.turns

    for t_idx in range(len(turns) - 1):
        curr_turn = turns[t_idx]
        next_turn = turns[t_idx + 1]

        # The opponent on current turn is the player who plays on next_turn
        opp_rack_str = next_turn.rack
        if not opp_rack_str:
            continue

        try:
            state = GameState.from_cgp(curr_turn.board_before_cgp)
            board_tensor = state.to_board_tensor().numpy()
            state_vector = state.to_state_vector().numpy()
        except Exception:
            continue

        # Target 27-dim count vector (26 letters + blank)
        target_counts = np.zeros(27, dtype=np.float32)
        for ch in opp_rack_str:
            upper = ch.upper()
            if upper == '?':
                target_counts[26] += 1.0
            else:
                idx = ord(upper) - ord('A')
                if 0 <= idx < 26:
                    target_counts[idx] += 1.0

        samples.append({
            "game_id": game.game_id,
            "turn_index": t_idx,
            "board_tensor": board_tensor,
            "state_vector": state_vector,
            "opp_rack_target": target_counts,
        })

    return samples


def build_belief_dataset(
    gcg_files: List[str],
    output_path: str,
) -> int:
    """Processes a list of GCG files and outputs a compressed belief dataset."""
    all_boards = []
    all_states = []
    all_targets = []

    print(f"Extracting belief samples from {len(gcg_files)} GCG games...")
    for f in tqdm(gcg_files):
        game = parse_gcg_file(f)
        if not game:
            continue
        samples = extract_game_belief_samples(game)
        for s in samples:
            all_boards.append(s["board_tensor"])
            all_states.append(s["state_vector"])
            all_targets.append(s["opp_rack_target"])

    if not all_boards:
        print("No samples extracted.")
        return 0

    boards_arr = np.stack(all_boards)
    states_arr = np.stack(all_states)
    targets_arr = np.stack(all_targets)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    np.savez_compressed(
        output_path,
        board_tensors=boards_arr,
        state_vectors=states_arr,
        opp_rack_targets=targets_arr,
    )
    print(f"Saved {len(all_boards)} belief samples to {output_path} ({os.path.getsize(output_path)/(1024*1024):.2f} MB)")
    return len(all_boards)
