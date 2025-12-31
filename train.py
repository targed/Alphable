import os
# FORCE TensorFlow to use the legacy Keras 2 interface
os.environ["TF_USE_LEGACY_KERAS"] = "1"

import sys
import pyspiel
from open_spiel.python.algorithms.alpha_zero import alpha_zero
from open_spiel.python.utils import spawn

# Import your game module so it is registered
import scrabble 

def main(unused_argv):
    # Load game to verify registration
    game = pyspiel.load_game("scrabble")
    
    # Configuration with ALL required parameters
    config = alpha_zero.Config(
        game="scrabble",
        path="./scrabble_az_checkpoints",
        learning_rate=0.01,
        weight_decay=1e-4,
        train_batch_size=16, # Was 64
        replay_buffer_size=64, # Was 200
        replay_buffer_reuse=4, # Was 3
        max_steps=100,
        checkpoint_freq=10,
        
        # MCTS Config
        uct_c=2,
        max_simulations=10, # Was 50
        
        # Network Config
        nn_model="resnet",
        nn_width=64,
        nn_depth=2,
        observation_shape=[35, 15, 15],
        output_size=452,
        
        # --- MISSING PARAMETERS ADDED BELOW ---
        actors=2,               # Number of parallel processes playing games
        evaluators=1,           # Number of parallel processes evaluating strength
        evaluation_window=50,   # Sliding window size for evaluation stats
        eval_levels=1,          # MCTS simulations for the reference opponent (Training vs Simple MCTS)
        policy_alpha=1.0,       # Noise parameter (1.0 is standard for many moves)
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