import os
import time
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau
from tqdm import tqdm

from alphable_net import AlphableValueNet
from dataset import get_dataloaders

def train():
    # Setup Device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    # Path Configuration
    data_file = 'data/supervised/samples.jsonl'
    model_save_dir = 'models'
    os.makedirs(model_save_dir, exist_ok=True)
    best_model_path = os.path.join(model_save_dir, 'alphable_best_val_model.pth')

    # Check if dataset exists
    if not os.path.exists(data_file):
        print(f"Dataset not found at {data_file}. Please run prepare_dataset.py first.")
        return

    print(f"Loading dataset from {data_file}...")
    # Smaller batch size for CPU testing, increase for GPU training
    batch_size = 128 if torch.cuda.is_available() else 32
    train_loader, val_loader = get_dataloaders(data_file, batch_size=batch_size, train_split=0.9)
    print(f"Train batches: {len(train_loader)} | Val batches: {len(val_loader)}")

    # Setup Model, Loss, Optimizer
    model = AlphableValueNet().to(device)
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = ReduceLROnPlateau(optimizer, mode='min', factor=0.1, patience=3)

    num_epochs = 20
    best_val_loss = float('inf')

    print("Starting Supervised Training...")

    for epoch in range(num_epochs):
        start_time = time.time()

        # --- TRAINING PHASE ---
        model.train()
        train_loss = 0.0

        # Diagnostics
        total_train_targets = 0.0
        total_train_preds = 0.0
        train_items = 0

        # tqdm for progress bar
        train_loop = tqdm(train_loader, leave=False, desc=f"Epoch {epoch+1}/{num_epochs} [Train]")
        for batch_boards, batch_states, batch_targets in train_loop:
            # Move data to GPU
            batch_boards = batch_boards.to(device)
            batch_states = batch_states.to(device)
            batch_targets = batch_targets.to(device)

            optimizer.zero_grad()

            # Forward pass
            outputs = model(batch_boards, batch_states)

            # Weighted MSE Loss
            # Target is 1.0 (positive) or -1.0 (negative)
            weights = torch.where(batch_targets > 0, torch.tensor(10.0, device=device), torch.tensor(1.0, device=device))
            # Normalize by mean weight
            loss = (((outputs - batch_targets)**2) * weights).mean() / weights.mean()

            # Backward pass & optimize
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            train_loop.set_postfix(loss=loss.item())

            # Update diagnostics
            total_train_targets += batch_targets.sum().item()
            total_train_preds += outputs.sum().item()
            train_items += batch_targets.numel()

        avg_train_loss = train_loss / len(train_loader)
        mean_train_target = total_train_targets / train_items
        mean_train_pred = total_train_preds / train_items

        # --- VALIDATION PHASE ---
        model.eval()
        val_loss = 0.0

        with torch.no_grad():
            val_loop = tqdm(val_loader, leave=False, desc=f"Epoch {epoch+1}/{num_epochs} [Val]")
            for batch_boards, batch_states, batch_targets in val_loop:
                batch_boards = batch_boards.to(device)
                batch_states = batch_states.to(device)
                batch_targets = batch_targets.to(device)

                outputs = model(batch_boards, batch_states)

                # Weighted MSE Loss for validation as well to be consistent
                weights = torch.where(batch_targets > 0, torch.tensor(10.0, device=device), torch.tensor(1.0, device=device))
                loss = (((outputs - batch_targets)**2) * weights).mean() / weights.mean()

                val_loss += loss.item()

        avg_val_loss = val_loss / len(val_loader)

        # --- EPOCH SUMMARY ---
        epoch_time = time.time() - start_time
        print(f"Epoch {epoch+1:02d}/{num_epochs} | Time: {epoch_time:.2f}s | "
              f"Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f}")
        print(f"   -> Mean Target: {mean_train_target:.4f} | Mean Pred: {mean_train_pred:.4f}")

        # LR Scheduler Step
        scheduler.step(avg_val_loss)

        # Checkpointing
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            torch.save(model.state_dict(), best_model_path)
            print(f"   -> Best model saved to {best_model_path} (Val Loss: {best_val_loss:.4f})")

if __name__ == "__main__":
    train()
