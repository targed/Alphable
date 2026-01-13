import os
import sys
# 1. FORCE TensorFlow to use legacy Keras
os.environ["TF_USE_LEGACY_KERAS"] = "1"

os.environ["TF_FORCE_GPU_ALLOW_GROWTH"] = "true"

# 3. Suppress Info Logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import pyspiel
from open_spiel.python.algorithms.alpha_zero import alpha_zero
from open_spiel.python.algorithms.alpha_zero import model as model_lib
from open_spiel.python.utils import spawn
import scrabble 

# --- THE MONKEY PATCH ---
# We intercept the "build_model" function to inject our checkpoint
_original_build_model = model_lib.Model.build_model

def _resuming_build_model(*args, **kwargs):
    # 1. Build the fresh model as usual
    model = _original_build_model(*args, **kwargs)
    
    # 2. Force load the checkpoint
    # UPDATE THIS NUMBER to your latest checkpoint (e.g., 80)
    CHECKPOINT_STEP = 530
    
    # Construct path (handles Colab vs Local)
    # If you are on Colab, ensure this path matches where you saved it!
    # If local, "./scrabble_az_checkpoints" is likely correct.
    base_path = kwargs.get("path", "data/scrabble_az_checkpoints")
    ckpt_path = os.path.join(base_path, f"checkpoint-{CHECKPOINT_STEP}")
    
    try:
        print(f"--> ATTEMPTING TO RESUME FROM: {ckpt_path}")
        model.load_checkpoint(ckpt_path)
        print("--> RESUME SUCCESSFUL!")
    except Exception as e:
        print(f"--> RESUME FAILED (Starting from scratch): {e}")
        
    return model

# Apply the patch
model_lib.Model.build_model = _resuming_build_model
# ------------------------

def main(unused_argv):
    game = pyspiel.load_game("scrabble")
    
    # Configuration
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
    
    print(f"Starting Resume Training from Checkpoint...")
    alpha_zero.alpha_zero(config)

if __name__ == "__main__":
    with spawn.main_handler():
        sys.exit(main(sys.argv))