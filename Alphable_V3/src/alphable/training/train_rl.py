import argparse
import json
import os
import time

import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau
from tqdm import tqdm

from alphable.core.alphable_net import AlphableValueNet, load_checkpoint_compatible
from alphable.data.dataset import get_dataloaders


def train_rl(
    data_file,
    init_model_path,
    save_path,
    batch_size,
    lr,
    weight_decay,
    num_epochs,
    train_split,
    early_stopping_patience,
):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    if not os.path.exists(data_file):
        raise FileNotFoundError(f"RL dataset not found at {data_file}")

    print(f"Loading RL dataset from {data_file}...")
    train_loader, val_loader = get_dataloaders(
        data_file,
        batch_size=batch_size,
        train_split=train_split,
    )
    print(
        f"Train batches: {len(train_loader)} | Val batches: {len(val_loader)}")

    model = AlphableValueNet().to(device)
    if init_model_path and os.path.exists(init_model_path):
        print(f"Warm-starting from {init_model_path}")
        loaded, total = load_checkpoint_compatible(model, init_model_path, device)
        print(f"Loaded {loaded}/{total} tensors from {init_model_path}")
    else:
        fallback_model = 'models/alphable_best_val_model.pth'
        if os.path.exists(fallback_model):
            print(
                f"Warning: init model not found. Falling back to {fallback_model}"
            )
            loaded, total = load_checkpoint_compatible(model, fallback_model, device)
            print(f"Loaded {loaded}/{total} tensors from {fallback_model}")
        else:
            print(
                "Warning: init model not found. Training RL model from random initialization.")

    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr,
                            weight_decay=weight_decay)
    scheduler = ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=2)

    best_val_loss = float('inf')
    epochs_without_improvement = 0
    history = []

    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    print("Starting RL Training...")
    for epoch in range(num_epochs):
        start = time.time()
        model.train()
        train_loss = 0.0

        train_loop = tqdm(train_loader, leave=False,
                          desc=f"Epoch {epoch+1}/{num_epochs} [Train]")
        for boards, states, targets in train_loop:
            boards = boards.to(device)
            states = states.to(device)
            targets = targets.to(device)

            optimizer.zero_grad()
            outputs = model(boards, states)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            train_loop.set_postfix(loss=f"{loss.item():.4f}")

        avg_train = train_loss / max(1, len(train_loader))

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            val_loop = tqdm(val_loader, leave=False,
                            desc=f"Epoch {epoch+1}/{num_epochs} [Val]")
            for boards, states, targets in val_loop:
                boards = boards.to(device)
                states = states.to(device)
                targets = targets.to(device)

                outputs = model(boards, states)
                loss = criterion(outputs, targets)
                val_loss += loss.item()

        avg_val = val_loss / max(1, len(val_loader))
        epoch_time = time.time() - start

        print(
            f"Epoch {epoch+1:02d}/{num_epochs} | Time: {epoch_time:.2f}s | "
            f"Train Loss: {avg_train:.4f} | Val Loss: {avg_val:.4f}"
        )

        history.append({
            'epoch': epoch + 1,
            'train_loss': avg_train,
            'val_loss': avg_val,
            'time': epoch_time,
        })
        history_path = save_path.replace('.pth', '_history.json')
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)

        scheduler.step(avg_val)

        if avg_val < best_val_loss:
            best_val_loss = avg_val
            epochs_without_improvement = 0
            torch.save(model.state_dict(), save_path)
            print(
                f"   -> Best RL model saved to {save_path} (Val Loss: {best_val_loss:.4f})")
        else:
            epochs_without_improvement += 1
            print(
                f"   -> No val improvement for {epochs_without_improvement}/{early_stopping_patience}")

        if epochs_without_improvement >= early_stopping_patience:
            print(
                f"Early stopping triggered at epoch {epoch+1}. Best RL Val Loss: {best_val_loss:.4f}"
            )
            break


def main():
    parser = argparse.ArgumentParser(
        description='Train RL value network from self-play outcomes.')
    parser.add_argument(
        '--data', type=str, default='data/rl/rl_samples.jsonl', help='Path to RL samples jsonl.')
    parser.add_argument('--init-model', type=str,
                        default='models/alphable_rl_best_val_model.pth', help='Warm-start checkpoint path.')
    parser.add_argument('--save-model', type=str,
                        default='models/alphable_rl_best_val_model.pth', help='Output RL checkpoint path.')
    parser.add_argument('--batch-size', type=int, default=128)
    parser.add_argument('--lr', type=float, default=5e-4)
    parser.add_argument('--weight-decay', type=float, default=1e-4)
    parser.add_argument('--epochs', type=int, default=20)
    parser.add_argument('--train-split', type=float, default=0.9)
    parser.add_argument('--early-stop', type=int, default=4)
    args = parser.parse_args()

    train_rl(
        data_file=args.data,
        init_model_path=args.init_model,
        save_path=args.save_model,
        batch_size=args.batch_size,
        lr=args.lr,
        weight_decay=args.weight_decay,
        num_epochs=args.epochs,
        train_split=args.train_split,
        early_stopping_patience=args.early_stop,
    )


if __name__ == '__main__':
    main()
