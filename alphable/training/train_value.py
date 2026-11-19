"""
Alphable V4 Value Network Training Script.

Trains V4ValueNetwork (ResNet-18 + 8-head Cross-Attention) on Macondo-distilled
equity datasets with continuous deficit scaling.

Success Criteria:
1. Validation Huber loss <= 0.05
2. Pearson correlation with Macondo equity >= 0.90
3. Inference latency on GPU < 5.0 ms for 100 candidates
"""

from __future__ import annotations
import os
import sys
import time
import argparse
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR

from alphable_v4.models.value_net import V4ValueNetwork


class ValueDataset(Dataset):
    """PyTorch Dataset loading pre-processed board tensors, state vectors, and equity targets."""

    def __init__(self, npz_path: str):
        data = np.load(npz_path)
        self.board_tensors = torch.from_numpy(data["board_tensors"]).float()
        self.state_vectors = torch.from_numpy(data["state_vectors"]).float()
        self.targets = torch.from_numpy(data["targets"]).float().unsqueeze(1)
        self.raw_equities = torch.from_numpy(data["raw_equities"]).float()

    def __len__(self) -> int:
        return len(self.targets)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        return (
            self.board_tensors[idx],
            self.state_vectors[idx],
            self.targets[idx],
            self.raw_equities[idx],
        )


def compute_metrics(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> Dict[str, float]:
    """Evaluates validation loss and Pearson correlation."""
    model.eval()
    total_loss = 0.0
    all_preds = []
    all_targets = []
    all_raw = []

    with torch.no_grad():
        for boards, states, targets, raw in loader:
            boards = boards.to(device)
            states = states.to(device)
            targets = targets.to(device)

            preds = model(boards, states)
            loss = criterion(preds, targets)
            total_loss += loss.item() * len(targets)

            all_preds.append(preds.squeeze(1).cpu().numpy())
            all_targets.append(targets.squeeze(1).cpu().numpy())
            all_raw.append(raw.numpy())

    preds_arr = np.concatenate(all_preds)
    targets_arr = np.concatenate(all_targets)
    raw_arr = np.concatenate(all_raw)

    val_loss = total_loss / len(loader.dataset)
    
    # Pearson correlation with normalized target
    corr_target = float(np.corrcoef(preds_arr, targets_arr)[0, 1])
    # Pearson correlation with raw Macondo equity
    corr_raw = float(np.corrcoef(preds_arr, raw_arr)[0, 1])

    return {
        "loss": val_loss,
        "corr_target": corr_target,
        "corr_raw": corr_raw,
    }


def train_value_network(
    train_path: str = "data/value/train_distilled.npz",
    val_path: str = "data/value/val_distilled.npz",
    checkpoint_dir: str = "alphable_v4/models/checkpoints",
    epochs: int = 30,
    batch_size: int = 128,
    lr: float = 1e-4,
    weight_decay: float = 1e-4,
    device_str: str = "cuda",
) -> Dict[str, Any]:
    """Trains V4ValueNetwork and saves the best checkpoint."""
    device = torch.device(device_str if torch.cuda.is_available() else "cpu")
    print(f"Training on device: {device}")

    # Datasets and Loaders
    train_dataset = ValueDataset(train_path)
    val_dataset = ValueDataset(val_path)
    print(f"Loaded {len(train_dataset)} training samples, {len(val_dataset)} validation samples.")

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        drop_last=True,
        pin_memory=torch.cuda.is_available(),
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        pin_memory=torch.cuda.is_available(),
    )

    # Initialize model
    model = V4ValueNetwork(board_channels=32, state_dim=64, feature_dim=512, num_heads=8)
    model.to(device)

    criterion = nn.HuberLoss(delta=0.1)
    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)

    os.makedirs(checkpoint_dir, exist_ok=True)
    best_checkpoint_path = os.path.join(checkpoint_dir, "v4_value_net_best.pt")

    best_val_loss = float("inf")
    best_corr = -1.0
    history = []

    start_time = time.time()
    for epoch in range(1, epochs + 1):
        model.train()
        epoch_train_loss = 0.0
        t0 = time.time()

        for boards, states, targets, _ in train_loader:
            boards = boards.to(device)
            states = states.to(device)
            targets = targets.to(device)

            optimizer.zero_grad()
            preds = model(boards, states)
            loss = criterion(preds, targets)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            epoch_train_loss += loss.item() * len(targets)

        scheduler.step()
        train_loss = epoch_train_loss / len(train_dataset)

        # Validation
        val_metrics = compute_metrics(model, val_loader, criterion, device)
        epoch_time = time.time() - t0

        print(
            f"Epoch {epoch:02d}/{epochs:02d} [{epoch_time:.1f}s] "
            f"Train Loss: {train_loss:.5f} | Val Loss: {val_metrics['loss']:.5f} | "
            f"Corr(Target): {val_metrics['corr_target']:.4f} | Corr(Raw): {val_metrics['corr_raw']:.4f}"
        )

        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_metrics["loss"],
            "corr_target": val_metrics["corr_target"],
            "corr_raw": val_metrics["corr_raw"],
        })

        # Save best model based on validation loss & correlation
        if val_metrics["loss"] < best_val_loss:
            best_val_loss = val_metrics["loss"]
            best_corr = val_metrics["corr_target"]
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "val_loss": best_val_loss,
                    "corr_target": best_corr,
                    "corr_raw": val_metrics["corr_raw"],
                    "config": {
                        "board_channels": 32,
                        "state_dim": 64,
                        "feature_dim": 512,
                        "num_heads": 8,
                    },
                },
                best_checkpoint_path,
            )

    total_time = time.time() - start_time
    print(f"\nTraining completed in {total_time:.1f}s.")
    print(f"Best Val Loss: {best_val_loss:.5f} (Target <= 0.05)")
    print(f"Best Correlation: {best_corr:.4f} (Target >= 0.90)")
    print(f"Checkpoint saved to {best_checkpoint_path}")

    return {
        "best_val_loss": best_val_loss,
        "best_corr": best_corr,
        "checkpoint_path": best_checkpoint_path,
        "history": history,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-4)
    args = parser.parse_args()

    train_value_network(epochs=args.epochs, batch_size=args.batch_size, lr=args.lr)
