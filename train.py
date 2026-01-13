import os
import sys

# --- CRITICAL GPU CONFIGURATION ---
# 1. Force Legacy Keras (Required for OpenSpiel compatibility)
os.environ["TF_USE_LEGACY_KERAS"] = "1"

# 2. Handle GPU Memory Growth via Environment Variable
# This tells TensorFlow: "Don't grab all VRAM." 
# We set this HERE so it applies to all forked processes automatically
# without needing to run risky Python code in the parent process.
os.environ["TF_FORCE_GPU_ALLOW_GROWTH"] = "true"

# 3. Suppress Info Logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import pyspiel
from open_spiel.python.algorithms.alpha_zero import alpha_zero
from open_spiel.python.utils import spawn
import scrabble 

import tensorflow as tf

# Note: GPU settings removed since we're forcing CPU usage to avoid
# CUDA multiprocessing initialization errors with spawn

def main(unused_argv):
    # Load game to verify registration
    game = pyspiel.load_game("scrabble")
    
    # Configuration with ALL required parameters
    config = alpha_zero.Config(
        game="scrabble",
        path="data/scrabble_az_checkpoints",
        learning_rate=0.0001,
        weight_decay=1e-5,
        train_batch_size=64, # Was 64
        replay_buffer_size=10000, # Was 200
        replay_buffer_reuse=8, # Was 3
        max_steps=10000,
        checkpoint_freq=10,
        
        # MCTS Config
        uct_c=3,
        max_simulations=200, # Was 50
        
        # Network Config
        nn_model="resnet",
        nn_width=64, # Was 128
        nn_depth=3, # Was 6
        observation_shape=[35, 15, 15],
        output_size=452,
        
        # --- MISSING PARAMETERS ADDED BELOW ---
        actors=8,               # Number of parallel processes playing games
        evaluators=1,           # Number of parallel processes evaluating strength
        evaluation_window=50,   # Sliding window size for evaluation stats
        eval_levels=1,          # MCTS simulations for the reference opponent (Training vs Simple MCTS)
        policy_alpha=0.5,       # Noise parameter (1.0 is standard for many moves)
        policy_epsilon=0.25,    # Exploration noise fraction
        temperature=1.0,        # Initial softmax temperature
        temperature_drop=10,    # Step number to drop temperature to 0 (deterministic)
        
        quiet=False
    )
    
    print("Starting AlphaZero training for Scrabble...")
    alpha_zero.alpha_zero(config)

if __name__ == "__main__":
    with spawn.main_handler():
        sys.exit(main(sys.argv))