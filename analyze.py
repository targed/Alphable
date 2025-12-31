import json
import matplotlib.pyplot as plt
import pandas as pd
import os

LOG_PATH = "./scrabble_az_checkpoints/learner.jsonl"

def plot_training():
    data = []
    if not os.path.exists(LOG_PATH):
        print("No learner.jsonl found!")
        return

    with open(LOG_PATH, 'r') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))

    df = pd.DataFrame(data)
    
    # Extract nested loss values
    df['policy_loss'] = df['loss'].apply(lambda x: x.get('policy', None))
    df['value_loss'] = df['loss'].apply(lambda x: x.get('value', None))
    
    # Plotting
    fig, ax1 = plt.subplots(figsize=(10, 6))

    color = 'tab:red'
    ax1.set_xlabel('Training Step')
    ax1.set_ylabel('Policy Loss', color=color)
    ax1.plot(df['step'], df['policy_loss'], color=color, label='Policy Loss')
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx() 
    color = 'tab:blue'
    ax2.set_ylabel('Value Loss', color=color)
    ax2.plot(df['step'], df['value_loss'], color=color, label='Value Loss')
    ax2.tick_params(axis='y', labelcolor=color)

    plt.title('Alphable Training Progress')
    fig.tight_layout()
    plt.savefig('training_progress.png', dpi=150, bbox_inches='tight')
    print("Plot saved to training_progress.png")

if __name__ == "__main__":
    plot_training()