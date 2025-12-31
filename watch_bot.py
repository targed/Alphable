import os
# 1. FORCE TensorFlow to use legacy Keras
os.environ["TF_USE_LEGACY_KERAS"] = "1"

import pyspiel
import numpy as np
from open_spiel.python.algorithms.alpha_zero import alpha_zero
from open_spiel.python.algorithms import mcts
import scrabble 

# 2. Configuration 
CONFIG = alpha_zero.Config(
    game="scrabble",
    path="./scrabble_az_checkpoints",
    nn_model="resnet",
    nn_width=64,
    nn_depth=2,
    observation_shape=[35, 15, 15],
    output_size=452,
    learning_rate=0.01,
    weight_decay=1e-4,
    train_batch_size=16,
    replay_buffer_size=20,
    replay_buffer_reuse=1,
    max_steps=100,
    checkpoint_freq=10,
    actors=1,
    evaluators=1,
    evaluation_window=50,
    eval_levels=1,
    uct_c=2,
    max_simulations=20, 
    policy_alpha=1.0,
    policy_epsilon=0.25,
    temperature=1.0,
    temperature_drop=10,
    quiet=True
)

def get_action_string(state, action_id):
    if action_id == 450: return "PASS"
    if action_id == 451: return "EXCHANGE"
    
    # Force regeneration of move map to ensure lookup succeeds
    try:
        state._legal_actions(state.current_player())
        if hasattr(state, "_current_move_map") and action_id in state._current_move_map:
            m = state._current_move_map[action_id]
            return f"Plays '{m['word']}' at {m['row']},{m['col']} {m['dir']}"
    except Exception:
        pass
        
    return f"Action {action_id}"

def play_match():
    print("Loading game...")
    game = pyspiel.load_game("scrabble")
    
    print("Loading neural network from checkpoint-100...")
    from open_spiel.python.algorithms.alpha_zero import model as model_lib
    
    # FIXED: Added weight_decay and learning_rate arguments
    model = model_lib.Model.build_model(
        "resnet", 
        [35,15,15], 
        452, 
        64, 
        2, 
        weight_decay=1e-4,   # <--- Added
        learning_rate=0.01,  # <--- Added
        path="./scrabble_az_checkpoints"
    )
    
    model.load_checkpoint("./scrabble_az_checkpoints/checkpoint-100")
    
    from open_spiel.python.algorithms.alpha_zero import evaluator as az_evaluator
    az_eval = az_evaluator.AlphaZeroEvaluator(game, model)
    
    # Increase simulations so the bot thinks longer and plays better words
    bot = mcts.MCTSBot(
        game, 
        uct_c=2.0, 
        max_simulations=50, 
        evaluator=az_eval
    )

    state = game.new_initial_state()
    print("\n--- STARTING MATCH ---")
    
    prev_board_str = str(state) # Snapshot board
    
    while not state.is_terminal():
        player_id = state.current_player()
        
        try:
            action = bot.step(state)
            action_desc = get_action_string(state, action)
            
            # Apply
            state.apply_action(action)
            
            # Check if it was a real move or a failure-pass
            new_board_str = str(state)
            
            if "PASS" in action_desc or "EXCHANGE" in action_desc:
                print(f"Player {player_id}: {action_desc}")
            elif new_board_str == prev_board_str:
                # Board didn't change = Invalid Move treated as Pass
                print(f"Player {player_id}: TRIED {action_desc} -> FAILED (Invalid/Disallowed)")
            else:
                # Success
                print(f"Player {player_id}: {action_desc}")
                # Print rack for next player
                next_p = 1 - player_id
                print(f"   Rack P{next_p}: {state.racks[next_p]}")

            prev_board_str = new_board_str

        except Exception as e:
            print(f"CRASH: {e}")
            break

    print("\n--- GAME OVER ---")
    print(state)
    print(f"Final Score: {state.scores}")

if __name__ == "__main__":
    play_match()