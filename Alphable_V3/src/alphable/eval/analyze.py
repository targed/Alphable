import argparse
import json
import os
import matplotlib.pyplot as plt


def plot_loss_history(history_file, output_png='training_progress.png', title='Alphable Training Loss'):
    """Plot training and validation loss curves from a history JSON file."""
    if not os.path.exists(history_file):
        print(f"History file not found: {history_file}")
        return

    with open(history_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not data:
        print(f"No history entries found in {history_file}")
        return

    epochs = [d['epoch'] for d in data]
    train_loss = [d['train_loss'] for d in data]
    val_loss = [d['val_loss'] for d in data]

    fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
    ax.plot(epochs, train_loss, label='Train Loss', color='#2563eb', linewidth=2.0, marker='o', markersize=4)
    ax.plot(epochs, val_loss, label='Val Loss', color='#dc2626', linewidth=2.0, marker='s', markersize=4)

    ax.set_title(title, fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel('Epoch', fontsize=12)
    ax.set_ylabel('Loss (MSE)', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(fontsize=11)

    os.makedirs(os.path.dirname(output_png) or '.', exist_ok=True)
    fig.tight_layout()
    plt.savefig(output_png, bbox_inches='tight')
    plt.close()
    print(f"Loss plot successfully saved to: {output_png}")


def main():
    parser = argparse.ArgumentParser(description='Plot Alphable training loss and evaluation progress.')
    parser.add_argument('--history', type=str, required=True, help='Path to _history.json file.')
    parser.add_argument('--output', type=str, default='training_progress.png', help='Output PNG path.')
    parser.add_argument('--title', type=str, default='Alphable V3 Training Progress', help='Chart title.')
    args = parser.parse_args()

    plot_loss_history(args.history, args.output, args.title)


if __name__ == '__main__':
    main()
