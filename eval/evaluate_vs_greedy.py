import os
import sys
# Add parent directory to path to import scrabble module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TF_FORCE_GPU_ALLOW_GROWTH"] = "true"
import pyspiel
from open_spiel.python.algorithms.alpha_zero import model as model_lib
from open_spiel.python.algorithms.alpha_zero import evaluator as az_evaluator
from open_spiel.python.algorithms import mcts
import scrabble
from datetime import datetime
from game_logger import GameLogger

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

class GreedyBot:
    """A bot that always plays the highest scoring immediate move."""
    def __init__(self, game):
        self.game = game
    
    def step(self, state):
        # 1. Get Legal Actions
        legal_actions = state.legal_actions()
        if not legal_actions: return 450 # Pass
        if legal_actions == [450]: return 450
        
        # 2. Ensure the Move Map is populated
        # We need this to look up the words and directions
        if not hasattr(state, "_current_move_map") or not state._current_move_map:
            state._legal_actions(state.current_player())
            
        best_action = legal_actions[0]
        max_score = -1.0
        
        for action_id in legal_actions:
            if action_id >= 450: continue # Skip Pass/Exchange if we have moves
            
            if action_id in state._current_move_map:
                move = state._current_move_map[action_id]
                try:
                    # Cheat: Ask the engine to calculate score without applying move
                    score, _ = state._score_move(
                        move['row'], move['col'], move['word'], move['dir']
                    )
                    if score > max_score:
                        max_score = score
                        best_action = action_id
                except:
                    continue
        
        return best_action

def evaluate(checkpoint_num):
    print(f"Loading Checkpoint {checkpoint_num}...")
    
    # Change to project root directory so scrabble.py can find resources/
    project_root = os.path.join(os.path.dirname(__file__), "..")
    original_dir = os.getcwd()
    os.chdir(project_root)
    
    try:
        game = pyspiel.load_game("scrabble")
    finally:
        os.chdir(original_dir)
    
    # Create output directory (relative to project root)
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "vs_greedy")
    os.makedirs(output_dir, exist_ok=True)
    
    # Load AZ Model
    checkpoint_path = os.path.join(os.path.dirname(__file__), "..", "data", "scrabble_az_checkpoints")
    model = model_lib.Model.build_model(
        "resnet", [35,15,15], 452, 64, 3,  # MUST MATCH YOUR TRAIN CONFIG (width=64, depth=3)
        path=checkpoint_path,
        learning_rate=0.001, weight_decay=1e-4
    )
    model.load_checkpoint(f"{checkpoint_path}/checkpoint-{checkpoint_num}")
    
    # Use higher simulations for evaluation (gives AZ time to think)
    az_eval = az_evaluator.AlphaZeroEvaluator(game, model)
    az_bot = mcts.MCTSBot(game, 2.0, 100, evaluator=az_eval) # 100 sims for evaluation
    
    greedy_bot = GreedyBot(game)

    az_wins = 0
    games_to_play = 5 # Play 5 games
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"--- Alphable vs Greedy Bot ---")

    for i in range(games_to_play):
        state = game.new_initial_state()
        
        # Alternate who goes first
        if i % 2 == 0:
            p0, p1 = az_bot, greedy_bot
            p0_name, p1_name = "Alphable", "Greedy"
        else:
            p0, p1 = greedy_bot, az_bot
            p0_name, p1_name = "Greedy", "Alphable"
        
        # Initialize game logger for JSON output
        game_logger = GameLogger(p0_name, p1_name)
        game_logger.set_metadata(
            checkpoint=checkpoint_num,
            opponent="Greedy Bot",
            simulations=100
        )
        
        # Open log file for this game
        log_file = f"{output_dir}/ckpt{checkpoint_num}_game{i+1}_{timestamp}.txt"
        json_file = f"{output_dir}/ckpt{checkpoint_num}_game{i+1}_{timestamp}.json"
        
        with open(log_file, 'w') as f:
            # Redirect output to file
            original_stdout = sys.stdout
            sys.stdout = f
            
            print("======================================================================")
            print(f"Alphable (Checkpoint {checkpoint_num}) vs Greedy Bot")
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
                bot = p0 if player_id == 0 else p1
                
                # Capture state before move
                rack_before = state.racks[player_id].copy() if hasattr(state, 'racks') else []
                tiles_in_bag = len(state.bag) if hasattr(state, 'bag') else 0
                
                try:
                    action = bot.step(state)
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
                        # Try to get move details from move map
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
                    game_logger.log_move(
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
                    )
                    
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
            
            # Results
            raw_scores = state.scores
            az_idx = 0 if i % 2 == 0 else 1
            greedy_idx = 1 - az_idx
            
            s_az = raw_scores[az_idx]
            s_gr = raw_scores[greedy_idx]
            
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
            print(f"Alphable Score: {s_az:.0f}")
            print(f"Greedy Bot Score: {s_gr:.0f}")
            print(f"Alphable Bingos: {stats['player_stats'][az_idx]['bingos']}")
            print(f"Greedy Bot Bingos: {stats['player_stats'][greedy_idx]['bingos']}")
            
            if s_az > s_gr:
                print(f"Winner: Alphable (by {s_az - s_gr:.0f} points)")
            elif s_gr > s_az:
                print(f"Winner: Greedy Bot (by {s_gr - s_az:.0f} points)")
            else:
                print("Result: TIE")
            print(f"======================================================================")
            
            # Restore stdout
            sys.stdout = original_stdout
        
        # Save JSON log
        game_logger.save_json(json_file)
        
        # Print to console
        if s_az > s_gr:
            az_wins += 1
            print(f"Game {i+1}: AZ Wins ({s_az:.0f} vs {s_gr:.0f}) - Saved to {log_file}")
        else:
            print(f"Game {i+1}: Greedy Wins ({s_gr:.0f} vs {s_az:.0f}) - Saved to {log_file}")

    print(f"\nFinal Win Rate: {az_wins}/{games_to_play}")
    print(f"All game logs saved to {output_dir}/")

if __name__ == "__main__":
    # Update this to your latest checkpoint
    evaluate(1080)