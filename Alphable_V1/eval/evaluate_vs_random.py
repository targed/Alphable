import os
import sys
# Add parent directory to path to import scrabble module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ["TF_USE_LEGACY_KERAS"] = "1"
import pyspiel
import numpy as np
from open_spiel.python.algorithms.alpha_zero import model as model_lib
from open_spiel.python.algorithms.alpha_zero import evaluator as az_evaluator
from open_spiel.python.algorithms import mcts
import scrabble
from datetime import datetime
from eval.game_logger import GameLogger, MoveEntry

def get_action_string(state, action_id):
    """Convert action ID to readable string."""
    if action_id == 450: return "PASS"
    if action_id == 451: return "EXCHANGE"
    
    try:
        state._legal_actions(state.current_player())
        if hasattr(state, "_current_move_map") and action_id in state._current_move_map:
            m = state._current_move_map[action_id]
            return f"Plays '{m['word']}' at {m['row']},{m['col']} {m['dir']}"
    except Exception:
        pass
        
    return f"Action {action_id}"

def evaluate(checkpoint_num):
    # Change to project root directory so scrabble.py can find resources/
    project_root = os.path.join(os.path.dirname(__file__), "..")
    original_dir = os.getcwd()
    os.chdir(project_root)
    
    try:
        game = pyspiel.load_game("scrabble")
    finally:
        os.chdir(original_dir)
    
    # Create output directory (relative to project root)
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "vs_random")
    os.makedirs(output_dir, exist_ok=True)
    
    # Load YOUR bot
    checkpoint_base = os.path.join(os.path.dirname(__file__), "..", "data", "scrabble_az_checkpoints")
    model = model_lib.Model.build_model("resnet", [35,15,15], 452, 64, 2,
                                        weight_decay=1e-4, learning_rate=0.001,
                                        path=checkpoint_base)
    checkpoint_path = os.path.join(checkpoint_base, f"checkpoint-{checkpoint_num}")
    model.load_checkpoint(checkpoint_path)
    az_eval = az_evaluator.AlphaZeroEvaluator(game, model)
    
    # 10 simulations for speed
    az_bot = mcts.MCTSBot(game, 2.0, 10, evaluator=az_eval)
    
    # Random Bot (0 simulations = pure rollouts, or just random picker)
    # Using MCTS with low sims and Random Rollout Evaluator acts like a "Weak" bot
    random_bot = mcts.MCTSBot(game, 2.0, 10, evaluator=mcts.RandomRolloutEvaluator())

    az_wins = 0
    games_to_play = 5
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"--- Evaluator: Alphable (Ckpt {checkpoint_num}) vs Random ---")

    for i in range(games_to_play):
        state = game.new_initial_state()
        # Swap who goes first
        p0 = az_bot if i % 2 == 0 else random_bot
        p1 = random_bot if i % 2 == 0 else az_bot
        p0_name = "Alphable" if i % 2 == 0 else "Random"
        p1_name = "Random" if i % 2 == 0 else "Alphable"
        
        # Initialize game logger for JSON output
        game_logger = GameLogger(p0_name, p1_name)
        game_logger.set_metadata(
            checkpoint=checkpoint_num,
            opponent="Random Bot",
            simulations=10
        )
        
        # Open log file for this game
        log_file = f"{output_dir}/ckpt{checkpoint_num}_game{i+1}_{timestamp}.txt"
        json_file = f"{output_dir}/ckpt{checkpoint_num}_game{i+1}_{timestamp}.json"
        
        with open(log_file, 'w') as f:
            # Redirect output to file
            original_stdout = sys.stdout
            sys.stdout = f
            
            print("======================================================================")
            print(f"Alphable (Checkpoint {checkpoint_num}) vs Random Bot")
            print("======================================================================")
            print(f"Game {i+1}/{games_to_play}")
            print(f"Player 0: {p0_name}")
            print(f"Player 1: {p1_name}")
            print(f"Timestamp: {timestamp}")
            print("======================================================================\n")
            print("--- STARTING MATCH ---\n")
            
            prev_board_str = str(state)
            move_count = 0
            turn_index = 0
            
            while not state.is_terminal():
                player_id = state.current_player()
                
                # Capture state before move
                rack_before = state.racks[player_id].copy() if hasattr(state, 'racks') else []
                tiles_in_bag = len(state.bag) if hasattr(state, 'bag') else 0
                
                try:
                    if player_id == 0:
                        action = p0.step(state)
                    else:
                        action = p1.step(state)
                    
                    action_desc = get_action_string(state, action)
                    
                    # Parse action details before applying
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
                    
                    state.apply_action(action)
                    move_count += 1
                    
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
                    
                    new_board_str = str(state)
                    
                    if "PASS" in action_desc or "EXCHANGE" in action_desc:
                        print(f"Player {player_id}: {action_desc}")
                    elif new_board_str == prev_board_str:
                        print(f"Player {player_id}: TRIED {action_desc} -> FAILED (Invalid/Disallowed)")
                    else:
                        print(f"Player {player_id}: {action_desc}")
                        # Print rack for next player
                        next_p = 1 - player_id
                        print(f"   Rack P{next_p}: {state.racks[next_p]}")
                    
                    prev_board_str = new_board_str
                    
                except Exception as e:
                    print(f"CRASH: {e}")
                    break
            
            # Score
            score = state.returns()
            raw_scores = state.scores
            # If i%2==0, AZ is P0 (index 0). If score[0] > score[1], AZ won.
            az_idx = 0 if i % 2 == 0 else 1
            rand_idx = 1 - az_idx
            
            az_score = raw_scores[az_idx]
            rand_score = raw_scores[rand_idx]
            
            # Finalize JSON log
            game_logger.set_final_score([raw_scores[0], raw_scores[1]])
            
            # Get statistics
            stats = game_logger.get_statistics()
            
            print("\n--- GAME OVER ---\n")
            print(state)
            print(f"\n======================================================================")
            print(f"FINAL RESULTS")
            print(f"======================================================================")
            print(f"Total Moves: {move_count}")
            print(f"Alphable Score: {az_score:.0f}")
            print(f"Random Bot Score: {rand_score:.0f}")
            print(f"Alphable Bingos: {stats['player_stats'][az_idx]['bingos']}")
            print(f"Random Bot Bingos: {stats['player_stats'][rand_idx]['bingos']}")
            
            if az_score > rand_score:
                print(f"Winner: Alphable (by {az_score - rand_score:.0f} points)")
            elif rand_score > az_score:
                print(f"Winner: Random Bot (by {rand_score - az_score:.0f} points)")
            else:
                print("Result: TIE")
            print(f"======================================================================")
            
            # Restore stdout
            sys.stdout = original_stdout
        
        # Save JSON log
        game_logger.save_json(json_file)
        
        # Print to console
        if az_score > rand_score:
            az_wins += 1
            print(f"Game {i+1}: AZ Wins ({az_score:.0f} vs {rand_score:.0f}) - Saved to {log_file}")
        else:
            print(f"Game {i+1}: Random Wins ({rand_score:.0f} vs {az_score:.0f}) - Saved to {log_file}")

    print(f"\nWin Rate: {az_wins}/{games_to_play}")
    print(f"All game logs saved to {output_dir}/")

if __name__ == "__main__":
    # Change 1000 to whatever your latest checkpoint is
    evaluate(3600)