import os
import sys
# 1. FORCE TensorFlow to use legacy Keras
os.environ["TF_USE_LEGACY_KERAS"] = "1"

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
    CHECKPOINT_STEP = 100
    
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
        # Ensure this matches your folder
        path="data/scrabble_az_checkpoints", 
        # path="/content/drive/My Drive/Alphable_Checkpoints", # Use this if on Colab!
        
        learning_rate=0.01,
        weight_decay=1e-4,
        train_batch_size=16,
        replay_buffer_size=64,
        replay_buffer_reuse=4,
        
        # WE WANT 100 MORE STEPS
        max_steps=100, 
        
        checkpoint_freq=10,
        actors=2,
        evaluators=1,
        evaluation_window=50,
        eval_levels=1,
        uct_c=2,
        max_simulations=10,
        policy_alpha=1.0,
        policy_epsilon=0.25,
        temperature=1.0,
        temperature_drop=10,
        
        nn_model="resnet",
        nn_width=64,
        nn_depth=2,
        observation_shape=[35, 15, 15],
        output_size=452,
        quiet=False
    )
    
    print(f"Starting Resume Training from Checkpoint...")
    alpha_zero.alpha_zero(config)

if __name__ == "__main__":
    with spawn.main_handler():
        sys.exit(main(sys.argv))