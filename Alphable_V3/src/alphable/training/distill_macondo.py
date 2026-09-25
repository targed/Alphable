"""
Offline Knowledge Distillation from Macondo Grandmaster Analyzer data.

Extracts ~2,300 grandmaster-evaluated board states and equities from completed
Woogles matches (data/woogles/matches/*/analysis.json + game.gcg) and fine-tunes
AlphableValueNet to align its strategic evaluation with Macondo ground truth.
"""

import os
import glob
import json
import re
import argparse
from typing import List, Tuple, Dict, Any

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import numpy as np
from tqdm import tqdm

from alphable.core import inference
from alphable.core.alphable_net import AlphableValueNet, load_checkpoint_compatible


def parse_position(pos: str) -> Tuple[int, int, str]:
    """
    Parses a Scrabble position string into (row, col, direction).
    e.g. '8G' -> (7, 6, 'Across'), 'H13' -> (12, 7, 'Down').
    """
    if not pos:
        return None, None, None
    pos = pos.upper()
    if pos[0].isalpha():
        # Down (e.g. H13)
        match = re.match(r"^([A-Z])(\d+)$", pos)
        if match:
            col = ord(match.group(1)) - ord('A')
            row = int(match.group(2)) - 1
            return row, col, 'Down'
    else:
        # Across (e.g. 8G)
        match = re.match(r"^(\d+)([A-Z])$", pos)
        if match:
            row = int(match.group(1)) - 1
            col = ord(match.group(2)) - ord('A')
            return row, col, 'Across'
    return None, None, None


def extract_match_samples(match_dir: str) -> List[Dict[str, Any]]:
    """
    Extracts (board, rack, score_diff, bag_remaining, target_value) tuples
    from a single match folder containing game.gcg and analysis.json.
    """
    gcg_file = os.path.join(match_dir, "game.gcg")
    analysis_file = os.path.join(match_dir, "analysis.json")

    if not (os.path.exists(gcg_file) and os.path.exists(analysis_file)):
        return []

    try:
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
    except Exception:
        return []

    if not analysis_data:
        return []

    try:
        with open(gcg_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception:
        return []

    # 1. Parse player names & initial moves
    player_names = []
    gcg_moves = []
    final_scores = {}

    for line in lines:
        line = line.strip()
        if line.startswith("#player1"):
            parts = line.split()
            if len(parts) >= 2:
                player_names.append(parts[1])
        elif line.startswith("#player2"):
            parts = line.split()
            if len(parts) >= 2:
                player_names.append(parts[1])
        elif line.startswith(">"):
            # Turn line: >Player: RACK COORDS WORD +PTS TOTAL
            m = line[1:].strip().split()
            if len(m) >= 4:
                p_name = m[0].rstrip(":")
                rack_str = m[1]
                coords_str = m[2]
                word_str = m[3]
                pts = 0
                tot = 0
                for part in m[4:]:
                    if part.startswith("+"):
                        try:
                            pts = int(part[1:])
                        except ValueError:
                            pass
                    else:
                        try:
                            tot = int(part)
                            final_scores[p_name] = tot
                        except ValueError:
                            pass
                gcg_moves.append({
                    "player": p_name,
                    "rack": rack_str,
                    "coords": coords_str,
                    "word": word_str,
                    "points": pts,
                    "total": tot,
                })

    if len(player_names) < 2 and gcg_moves:
        # Deduce player names from moves
        for m in gcg_moves:
            if m["player"] not in player_names:
                player_names.append(m["player"])

    if len(player_names) < 2:
        return []

    p1, p2 = player_names[0], player_names[1]
    p1_final = final_scores.get(p1, 0)
    p2_final = final_scores.get(p2, 0)

    # 2. Replay board move by move and correlate with analysis
    board = [['.' for _ in range(15)] for _ in range(15)]
    current_scores = {p1: 0, p2: 0}
    tiles_played = 0

    samples = []
    turn_limit = min(len(gcg_moves), len(analysis_data))

    for t_idx in range(turn_limit):
        m = gcg_moves[t_idx]
        ana_turn = analysis_data[t_idx]
        suggestions = ana_turn.get("suggestions", [])
        if not suggestions:
            continue

        p_current = m["player"]
        p_opp = p2 if p_current == p1 else p1

        my_rack = list(m["rack"].replace(".", ""))
        my_score = current_scores[p_current]
        opp_score = current_scores[p_opp]
        score_diff = my_score - opp_score
        bag_remaining = max(0, 100 - tiles_played - 14)

        # Macondo equity for best available move
        top_equity = float(suggestions[0].get("equity", 0.0))

        # Outcome value from game outcome perspective
        final_diff = (p1_final - p2_final) if p_current == p1 else (p2_final - p1_final)
        v_outcome = float(np.tanh(final_diff / 100.0))

        # Macondo equity normalized: typical range is [-60, +60] points
        v_macondo = float(np.tanh(top_equity / 50.0))

        # Combined target value
        v_target = 0.75 * v_macondo + 0.25 * v_outcome

        b_tensor = inference.board_to_tensor(board)
        s_tensor = inference.state_to_tensor(my_rack, score_diff, bag_remaining)

        samples.append({
            "board": b_tensor,
            "state": s_tensor,
            "target": torch.tensor([v_target], dtype=torch.float32),
            "equity": top_equity,
        })

        # Apply move to board
        r, c, d = parse_position(m["coords"])
        if r is not None and c is not None:
            word = m["word"]
            is_down = (d == "Down")
            for k, ch in enumerate(word):
                cr = r + (k if is_down else 0)
                cc = c + (0 if is_down else k)
                if ch != '.':
                    board[cr][cc] = ch
                    tiles_played += 1

        current_scores[p_current] = m["total"]

    return samples


class MacondoDistillationDataset(Dataset):
    def __init__(self, samples: List[Dict[str, Any]]):
        self.samples = samples

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        item = self.samples[idx]
        return item["board"], item["state"], item["target"]


def build_or_load_dataset(matches_dir: str, cache_path: str) -> List[Dict[str, Any]]:
    """Loads cached dataset or extracts from all match folders."""
    if os.path.exists(cache_path):
        print(f"Loading cached distilled dataset from {cache_path}...")
        return torch.load(cache_path)

    print(f"Scanning match folders in {matches_dir}...")
    match_folders = sorted(glob.glob(os.path.join(matches_dir, "match_*")))
    all_samples = []

    for m_dir in tqdm(match_folders, desc="Extracting Macondo turns"):
        samples = extract_match_samples(m_dir)
        all_samples.extend(samples)

    print(f"Extracted {len(all_samples)} grandmaster-annotated turn samples!")
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    torch.save(all_samples, cache_path)
    print(f"Saved dataset cache to {cache_path}.")
    return all_samples


def train_macondo_distillation(
    base_model_path: str,
    output_model_path: str,
    samples: List[Dict[str, Any]],
    epochs: int = 8,
    batch_size: int = 64,
    learning_rate: float = 1e-4,
    device: str = None,
):
    """
    Fine-tunes AlphableValueNet using supervised distillation against Macondo ground-truth values.
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"\n=======================================================")
    print(f"Starting Offline Macondo Distillation Fine-Tuning")
    print(f"Device: {device} | Samples: {len(samples)} | Epochs: {epochs} | LR: {learning_rate}")
    print(f"=======================================================")

    # Split into train/validation (85% / 15%)
    num_samples = len(samples)
    indices = list(range(num_samples))
    np.random.seed(42)
    np.random.shuffle(indices)

    split = int(0.85 * num_samples)
    train_idx, val_idx = indices[:split], indices[split:]

    train_data = MacondoDistillationDataset([samples[i] for i in train_idx])
    val_data = MacondoDistillationDataset([samples[i] for i in val_idx])

    train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_data, batch_size=batch_size, shuffle=False)

    model = AlphableValueNet().to(device)
    if os.path.exists(base_model_path):
        print(f"Loading pre-trained base model weights from {base_model_path}...")
        load_checkpoint_compatible(model, base_model_path, device=device)
    else:
        print(f"Notice: {base_model_path} not found. Training from scratch.")

    criterion = nn.MSELoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_val_loss = float("inf")

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0

        for boards, states, targets in train_loader:
            boards = boards.to(device)
            states = states.to(device)
            targets = targets.to(device)

            optimizer.zero_grad()
            preds = model(boards, states)
            loss = criterion(preds, targets)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * len(targets)

        train_loss /= len(train_data)
        scheduler.step()

        # Validation
        model.eval()
        val_loss = 0.0
        all_preds = []
        all_targets = []

        with torch.no_grad():
            for boards, states, targets in val_loader:
                boards = boards.to(device)
                states = states.to(device)
                targets = targets.to(device)

                preds = model(boards, states)
                loss = criterion(preds, targets)
                val_loss += loss.item() * len(targets)

                all_preds.extend(preds.view(-1).cpu().tolist())
                all_targets.extend(targets.view(-1).cpu().tolist())

        val_loss /= len(val_data)
        std_p = np.std(all_preds) if len(all_preds) > 1 else 0.0
        std_t = np.std(all_targets) if len(all_targets) > 1 else 0.0
        if std_p > 1e-6 and std_t > 1e-6:
            corr = float(np.corrcoef(all_preds, all_targets)[0, 1])
        else:
            corr = 0.0

        print(
            f"Epoch {epoch:2d}/{epochs} | "
            f"Train MSE: {train_loss:.4f} | "
            f"Val MSE: {val_loss:.4f} | "
            f"Equity Correlation (r): {corr:+.3f}"
        )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            os.makedirs(os.path.dirname(output_model_path), exist_ok=True)
            torch.save(model.state_dict(), output_model_path)
            print(f"  ✓ Saved improved model checkpoint to {output_model_path}")

    print("\n✓ Offline Macondo distillation fine-tuning completed successfully!")
    return output_model_path


def main():
    parser = argparse.ArgumentParser(description="Distill Macondo Grandmaster Analyzer data into AlphableValueNet.")
    parser.add_argument("--matches-dir", type=str, default="data/woogles/matches", help="Directory containing match replays.")
    parser.add_argument("--cache-path", type=str, default="data/distilled_macondo_dataset.pt", help="Path to cached dataset tensor file.")
    parser.add_argument("--base-model", type=str, default="models/alphable_v3_rl_gen2.pth", help="Base model checkpoint.")
    parser.add_argument("--output-model", type=str, default="models/alphable_v3_rl_gen3_distilled.pth", help="Output distilled checkpoint.")
    parser.add_argument("--epochs", type=int, default=8, help="Number of fine-tuning epochs.")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size for training.")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate.")
    args = parser.parse_args()

    samples = build_or_load_dataset(args.matches_dir, args.cache_path)
    train_macondo_distillation(
        base_model_path=args.base_model,
        output_model_path=args.output_model,
        samples=samples,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
    )


if __name__ == "__main__":
    main()
