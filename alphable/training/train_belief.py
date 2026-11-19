"""
Alphable V4 Neural Belief Network Training Script.

Trains NeuralBeliefNet on (state_vector -> opp_rack_distribution) to predict
the letter distribution in the opponent's hidden rack.
"""

from __future__ import annotations
import os
import time
from typing import Dict, Any

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW

from alphable_v4.models.belief_net import NeuralBeliefNet


class BeliefDataset(Dataset):
    """PyTorch Dataset loading state vectors and normalized opponent rack target distributions."""

    def __init__(self, npz_path: str):
        data = np.load(npz_path)
        self.state_vectors = torch.from_numpy(data["state_vectors"]).float()
        raw_targets = torch.from_numpy(data["opp_rack_targets"]).float()
        # Normalize targets to probability distribution (sum to 1.0)
        sums = raw_targets.sum(dim=-1, keepdim=True).clamp(min=1.0)
        self.targets = raw_targets / sums

    def __len__(self) -> int:
        return len(self.targets)

    def __getitem__(self, idx: int):
        return self.state_vectors[idx], self.targets[idx]


def train_belief_network(
    data_path: str = "data/belief/belief_dataset.npz",
    checkpoint_dir: str = "alphable_v4/models/checkpoints",
    epochs: int = 15,
    batch_size: int = 128,
    lr: float = 1e-3,
    device_str: str = "cuda",
) -> Dict[str, Any]:
    device = torch.device(device_str if torch.cuda.is_available() else "cpu")
    print(f"Training NeuralBeliefNet on device: {device}")

    dataset = BeliefDataset(data_path)
    val_size = int(len(dataset) * 0.1)
    train_size = len(dataset) - val_size
    train_set, val_set = torch.utils.data.random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True, drop_last=True)
    val_loader = DataLoader(val_set, batch_size=batch_size, shuffle=False)

    model = NeuralBeliefNet(state_dim=64, hidden_dim=256).to(device)
    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    # KL Divergence between predicted probability distribution and ground truth
    criterion = nn.KLDivLoss(reduction="batchmean")

    os.makedirs(checkpoint_dir, exist_ok=True)
    checkpoint_path = os.path.join(checkpoint_dir, "v4_belief_net_best.pt")

    best_val_loss = float("inf")
    for epoch in range(1, epochs + 1):
        model.train()
        total_train_loss = 0.0
        t0 = time.time()

        for states, targets in train_loader:
            states, targets = states.to(device), targets.to(device)
            optimizer.zero_grad()
            preds = model(states)  # (B, 27) softmax
            log_preds = torch.log(preds.clamp(min=1e-8))
            loss = criterion(log_preds, targets)
            loss.backward()
            optimizer.step()
            total_train_loss += loss.item() * len(targets)

        # Validation
        model.eval()
        total_val_loss = 0.0
        with torch.no_grad():
            for states, targets in val_loader:
                states, targets = states.to(device), targets.to(device)
                preds = model(states)
                log_preds = torch.log(preds.clamp(min=1e-8))
                loss = criterion(log_preds, targets)
                total_val_loss += loss.item() * len(targets)

        val_loss = total_val_loss / len(val_set)
        train_loss = total_train_loss / len(train_set)
        epoch_time = time.time() - t0

        print(f"Epoch {epoch:02d}/{epochs:02d} [{epoch_time:.1f}s] Train KL: {train_loss:.5f} | Val KL: {val_loss:.5f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "val_loss": best_val_loss,
            }, checkpoint_path)

    print(f"Belief network checkpoint saved to {checkpoint_path} with Best Val KL: {best_val_loss:.5f}")
    return {"checkpoint_path": checkpoint_path, "best_val_loss": best_val_loss}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()

    train_belief_network(epochs=args.epochs, batch_size=args.batch_size, lr=args.lr)
