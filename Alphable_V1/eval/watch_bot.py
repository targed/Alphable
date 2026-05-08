import os
import sys
# Add parent directory to path to import scrabble module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
# 1. FORCE TensorFlow to use legacy Keras
os.environ["TF_USE_LEGACY_KERAS"] = "1"

import pyspiel
import numpy as np
from open_spiel.python.algorithms.alpha_zero import alpha_zero
from open_spiel.python.algorithms import mcts
import scrabble
from eval.game_logger import GameLogger, MoveEntry

# 2. Configuration
base_path = os.path.join(os.path.dirname(__file__), "..")
CONFIG = alpha_zero.Config(
    game="scrabble",
    path=os.path.join(base_path, "data", "scrabble_az_checkpoints"),
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
    max_simulations=200, # Was 20
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
    
    # Change to project root directory so scrabble.py can find resources/
    project_root = os.path.join(os.path.dirname(__file__), "..")
    original_dir = os.getcwd()
    os.chdir(project_root)
    
    try:
        game = pyspiel.load_game("scrabble")
    finally:
        os.chdir(original_dir)
    
    # Create output directory
    from datetime import datetime
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "results")
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = f"{output_dir}/self_play_{timestamp}.json"
    
    print("Loading neural network from checkpoint-100...")
    from open_spiel.python.algorithms.alpha_zero import model as model_lib
    
    # FIXED: Added weight_decay and learning_rate arguments
    checkpoint_base = os.path.join(os.path.dirname(__file__), "..", "data", "scrabble_az_checkpoints")
    model = model_lib.Model.build_model(
        "resnet", 
        [35,15,15], 
        452, 
        64, 
        2, 
        weight_decay=1e-4,   # <--- Added
        learning_rate=0.01,  # <--- Added
        path=checkpoint_base
    )
    
    model.load_checkpoint(os.path.join(checkpoint_base, "checkpoint-50"))
    
    from open_spiel.python.algorithms.alpha_zero import evaluator as az_evaluator
    az_eval = az_evaluator.AlphaZeroEvaluator(game, model)
    
    # Increase simulations so the bot thinks longer and plays better words
    bot = mcts.MCTSBot(
        game, 
        uct_c=2.0, 
        max_simulations=50, 
        evaluator=az_eval
    )
    
    # Initialize game logger
    game_logger = GameLogger("Alphable", "Alphable")
    game_logger.set_metadata(
        checkpoint=50,
        match_type="Self-Play",
        simulations=50
    )

    state = game.new_initial_state()
    print("\n--- STARTING MATCH ---")
    
    prev_board_str = str(state) # Snapshot board
    turn_index = 0
    
    while not state.is_terminal():
        player_id = state.current_player()
        
        # Capture state before move
        rack_before = state.racks[player_id].copy() if hasattr(state, 'racks') else []
        tiles_in_bag = len(state.bag) if hasattr(state, 'bag') else 0
        
        try:
            action = bot.step(state)
            action_desc = get_action_string(state, action)
            
            # Parse action details
            action_type = "PASS"
            word = None
            position = None
            direction = None
            
            if action == 450:
                action_type = "PASS"
            elif action == 451:
                action_type = "EXCHANGE"
            else:
                action_type = "PLAY"
                try:
                    state._legal_actions(state.current_player())
                    if hasattr(state, "_current_move_map") and action in state._current_move_map:
                        move = state._current_move_map[action]
                        word = move['word']
                        position = (move['row'], move['col'])
                        direction = move['dir']
                except:
                    pass
            
            # Get score before applying
            score_before = state.scores[player_id] if hasattr(state, 'scores') else 0
            
            # Apply
            state.apply_action(action)
            
            # Get score after applying
            score_after = state.scores[player_id] if hasattr(state, 'scores') else 0
            score_delta = score_after - score_before
            
            # Capture state after move
            rack_after = state.racks[player_id].copy() if hasattr(state, 'racks') else []
            board_state = str(state)
            consecutive_passes = state.consecutive_passes if hasattr(state, 'consecutive_passes') else 0
            
            # Log to JSON
            game_logger.log_move(MoveEntry(
                turn_index=turn_index,
                player=player_id,
                action_type=action_type,
                action_id=action,
                word=word,
                position=position,
                direction=direction,
                score=score_delta,
                rack_before=rack_before,
                rack_after=rack_after,
                board_state=board_state,
                tiles_in_bag=tiles_in_bag,
                consecutive_passes=consecutive_passes
            ))
            
            turn_index += 1
            
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
    
    # Finalize and save JSON log
    game_logger.set_final_score([state.scores[0], state.scores[1]])
    game_logger.save_json(json_file)
    
    # Print statistics
    stats = game_logger.get_statistics()
    print(f"\nGame Statistics:")
    for p_id in [0, 1]:
        print(f"  Player {p_id}:")
        print(f"    Bingos: {stats['player_stats'][p_id]['bingos']}")
        print(f"    Average Score/Move: {stats['player_stats'][p_id]['average_score_per_move']}")
        print(f"    Highest Scoring Move: {stats['player_stats'][p_id]['highest_scoring_move']}")

if __name__ == "__main__":
    play_match()