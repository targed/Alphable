import argparse
import os
import time

import torch
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau
from tqdm import tqdm

from alphable.core.alphable_net import AlphableValueNet
from alphable.data.dataset import get_dataloaders


def parse_args():
    parser = argparse.ArgumentParser(
        description='Train Alphable supervised value model.'
    )

    # Paths / IO
    parser.add_argument(
        '--data',
        default='data/supervised/samples.jsonl',
        help='Path to supervised training JSONL file.',
    )
    parser.add_argument(
        '--save-dir',
        default='models',
        help='Directory used when --save-model is not provided.',
    )
    parser.add_argument(
        '--save-model',
        default=None,
        help='Full output model checkpoint path. Overrides --save-dir.',
    )
    parser.add_argument(
        '--resume-model',
        default=None,
        help='Optional checkpoint path to warm-start from.',
    )

    # Data split and batching
    parser.add_argument(
        '--batch-size',
        type=int,
        default=None,
        help='Batch size. If omitted: 128 on CUDA, 32 on CPU.',
    )
    parser.add_argument(
        '--train-split',
        type=float,
        default=0.9,
        help='Training split ratio in (0,1). Validation uses the remainder.',
    )

    # Optimization
    parser.add_argument('--epochs', type=int, default=20)
    parser.add_argument('--lr', type=float, default=1e-3)
    parser.add_argument('--weight-decay', type=float, default=1e-4)
    parser.add_argument(
        '--scheduler-factor',
        type=float,
        default=0.1,
        help='ReduceLROnPlateau factor.',
    )
    parser.add_argument(
        '--scheduler-patience',
        type=int,
        default=3,
        help='ReduceLROnPlateau patience.',
    )

    # Loss shaping / regularization
    parser.add_argument('--positive-weight', type=float, default=5.0)
    parser.add_argument('--negative-weight', type=float, default=1.0)
    parser.add_argument('--target-scale', type=float, default=0.8)
    parser.add_argument('--early-stop-patience', type=int, default=4)

    # Runtime
    parser.add_argument(
        '--device',
        default='auto',
        choices=['auto', 'cpu', 'cuda'],
        help='Training device selection.',
    )
    parser.add_argument('--seed', type=int, default=42)

    return parser.parse_args()


def resolve_device(device_arg):
    if device_arg == 'auto':
        return torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    return torch.device(device_arg)


def resolve_save_path(args):
    if args.save_model:
        save_dir = os.path.dirname(args.save_model) or '.'
        os.makedirs(save_dir, exist_ok=True)
        return args.save_model

    os.makedirs(args.save_dir, exist_ok=True)
    return os.path.join(args.save_dir, 'alphable_best_val_model.pth')


def validate_args(args):
    if not os.path.exists(args.data):
        raise FileNotFoundError(
            f'Dataset not found at {args.data}. Please run prepare_dataset.py first.'
        )
    if not (0.0 < args.train_split < 1.0):
        raise ValueError('--train-split must be between 0 and 1 (exclusive).')
    if args.epochs < 1:
        raise ValueError('--epochs must be >= 1.')
    if args.batch_size is not None and args.batch_size < 1:
        raise ValueError('--batch-size must be >= 1.')
    if args.positive_weight <= 0 or args.negative_weight <= 0:
        raise ValueError('Loss weights must be > 0.')
    if args.target_scale <= 0:
        raise ValueError('--target-scale must be > 0.')
    if args.early_stop_patience < 1:
        raise ValueError('--early-stop-patience must be >= 1.')
    if args.resume_model and not os.path.exists(args.resume_model):
        raise FileNotFoundError(
            f'Resume checkpoint not found: {args.resume_model}')


def train(args):
    validate_args(args)

    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    device = resolve_device(args.device)
    if device.type == 'cuda' and not torch.cuda.is_available():
        print('CUDA requested but unavailable. Falling back to CPU.')
        device = torch.device('cpu')

    save_path = resolve_save_path(args)
    batch_size = args.batch_size
    if batch_size is None:
        batch_size = 128 if device.type == 'cuda' else 32

    print(f'Using device: {device}')
    print(f'Loading dataset from {args.data}...')
    print(f'Batch size: {batch_size} | Train split: {args.train_split}')
    print(f'Best checkpoint path: {save_path}')

    train_loader, val_loader = get_dataloaders(
        args.data,
        batch_size=batch_size,
        train_split=args.train_split,
    )
    print(
        f'Train batches: {len(train_loader)} | Val batches: {len(val_loader)}')

    model = AlphableValueNet().to(device)
    if args.resume_model:
        model.load_state_dict(torch.load(
            args.resume_model, map_location=device, weights_only=True))
        print(f'Resumed model from {args.resume_model}')

    optimizer = optim.AdamW(
        model.parameters(),
        lr=args.lr,
        weight_decay=args.weight_decay,
    )
    scheduler = ReduceLROnPlateau(
        optimizer,
        mode='min',
        factor=args.scheduler_factor,
        patience=args.scheduler_patience,
    )

    best_val_loss = float('inf')
    epochs_without_improvement = 0

    print('Starting Supervised Training...')

    for epoch in range(args.epochs):
        start_time = time.time()

        model.train()
        train_loss = 0.0
        total_train_targets = 0.0
        total_train_preds = 0.0
        train_items = 0

        train_loop = tqdm(
            train_loader,
            leave=False,
            desc=f'Epoch {epoch+1}/{args.epochs} [Train]',
        )
        for batch_boards, batch_states, batch_targets in train_loop:
            batch_boards = batch_boards.to(device)
            batch_states = batch_states.to(device)
            batch_targets = batch_targets.to(device)

            optimizer.zero_grad()
            outputs = model(batch_boards, batch_states)

            smoothed_targets = batch_targets * args.target_scale
            weights = torch.where(
                batch_targets > 0,
                args.positive_weight,
                args.negative_weight,
            )
            loss = (((outputs - smoothed_targets) ** 2)
                    * weights).mean() / weights.mean()

            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            train_loop.set_postfix(loss=loss.item())

            total_train_targets += batch_targets.sum().item()
            total_train_preds += outputs.sum().item()
            train_items += batch_targets.numel()

        avg_train_loss = train_loss / len(train_loader)
        mean_train_target = total_train_targets / train_items
        mean_train_pred = total_train_preds / train_items

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            val_loop = tqdm(
                val_loader,
                leave=False,
                desc=f'Epoch {epoch+1}/{args.epochs} [Val]',
            )
            for batch_boards, batch_states, batch_targets in val_loop:
                batch_boards = batch_boards.to(device)
                batch_states = batch_states.to(device)
                batch_targets = batch_targets.to(device)

                outputs = model(batch_boards, batch_states)
                smoothed_targets = batch_targets * args.target_scale
                weights = torch.where(
                    batch_targets > 0,
                    args.positive_weight,
                    args.negative_weight,
                )
                loss = (((outputs - smoothed_targets) ** 2)
                        * weights).mean() / weights.mean()
                val_loss += loss.item()

        avg_val_loss = val_loss / len(val_loader)
        epoch_time = time.time() - start_time

        print(
            f'Epoch {epoch+1:02d}/{args.epochs} | Time: {epoch_time:.2f}s | '
            f'Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f}'
        )
        print(
            f'   -> Mean Target: {mean_train_target:.4f} | Mean Pred: {mean_train_pred:.4f}')

        scheduler.step(avg_val_loss)

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            epochs_without_improvement = 0
            torch.save(model.state_dict(), save_path)
            print(
                f'   -> Best model saved to {save_path} (Val Loss: {best_val_loss:.4f})')
        else:
            epochs_without_improvement += 1
            print(
                f'   -> No val improvement for '
                f'{epochs_without_improvement}/{args.early_stop_patience} epoch(s)'
            )

        if epochs_without_improvement >= args.early_stop_patience:
            print(
                f'Early stopping triggered at epoch {epoch+1}. '
                f'Best Val Loss: {best_val_loss:.4f}'
            )
            break


def main():
    train(parse_args())


if __name__ == '__main__':
    main()
