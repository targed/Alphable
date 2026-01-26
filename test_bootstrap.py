import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"
import pyspiel
from open_spiel.python.algorithms.alpha_zero import model as model_lib
from open_spiel.python.algorithms.alpha_zero import evaluator as az_evaluator
from open_spiel.python.algorithms import mcts
import scrabble
from datetime import datetime

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

def evaluate():
    game = pyspiel.load_game("scrabble")
    
    # Load the BOOTSTRAP checkpoint
    # Note: Use the same architecture params you used in bootstrap.py
    checkpoint_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "scrabble_az_checkpoints"))
    model = model_lib.Model.build_model(
        "resnet", [35,15,15], 452, 64, 3,  # MUST MATCH YOUR TRAIN CONFIG (width=64, depth=3)
        path=checkpoint_path,
        learning_rate=0.001, weight_decay=1e-4
    )
    
    # Load the latest checkpoint (2000 is the highest from 2000 training steps)
    # Note: load_checkpoint expects the full path with checkpoint prefix
    model.load_checkpoint(f"{checkpoint_path}/checkpoint-2000")
    print("Loaded Checkpoint 2000")
    
    az_eval = az_evaluator.AlphaZeroEvaluator(game, model)
    
    # Use 50 sims. The brain is smarter now, so MCTS can work better.
    az_bot = mcts.MCTSBot(game, 2.0, 50, evaluator=az_eval) 
    
    # Random Bot
    random_bot = mcts.MCTSBot(game, 2.0, 10, evaluator=mcts.RandomRolloutEvaluator())

    az_wins = 0
    games_to_play = 4
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("======================================================================")
    print("Bootstrapped Model (Checkpoint 2000) vs Random Bot")
    print("======================================================================")
    print(f"Timestamp: {timestamp}")
    print(f"Games to Play: {games_to_play}")
    print("======================================================================\n")
    
    for i in range(games_to_play):
        state = game.new_initial_state()
        
        # Alternate who goes first
        if i % 2 == 0:
            p0, p1 = az_bot, random_bot
            p0_name, p1_name = "Alphable", "Random"
        else:
            p0, p1 = random_bot, az_bot
            p0_name, p1_name = "Random", "Alphable"
        
        print(f"\n--- GAME {i+1}/{games_to_play} ---")
        print(f"Player 0: {p0_name}")
        print(f"Player 1: {p1_name}")
        print("--- STARTING MATCH ---\n")
        
        prev_board_str = str(state)
        move_count = 0
        
        while not state.is_terminal():
            player_id = state.current_player()
            bot = p0 if player_id == 0 else p1
            
            try:
                action = bot.step(state)
                action_desc = get_action_string(state, action)
                
                state.apply_action(action)
                move_count += 1
                
                new_board_str = str(state)
                
                if "PASS" in action_desc or "EXCHANGE" in action_desc:
                    print(f"Player {player_id}: {action_desc}")
                elif new_board_str == prev_board_str:
                    print(f"Player {player_id}: TRIED {action_desc} -> FAILED (Invalid/Disallowed)")
                else:
                    print(f"Player {player_id}: {action_desc}")
                    # Print rack for next player
                    next_p = 1 - player_id
                    if hasattr(state, 'racks'):
                        print(f"   Rack P{next_p}: {state.racks[next_p]}")
                
                prev_board_str = new_board_str
                
            except Exception as e:
                print(f"CRASH: {e}")
                break
        
        # Results
        raw_scores = state.scores
        az_idx = 0 if i % 2 == 0 else 1
        random_idx = 1 - az_idx
        
        s_az = raw_scores[az_idx]
        s_rand = raw_scores[random_idx]
        
        print("\n--- GAME OVER ---\n")
        print(state)
        print(f"\n======================================================================")
        print(f"FINAL RESULTS - Game {i+1}")
        print(f"======================================================================")
        print(f"Total Moves: {move_count}")
        print(f"Alphable Score: {s_az:.0f}")
        print(f"Random Bot Score: {s_rand:.0f}")
        
        if s_az > s_rand:
            az_wins += 1
            print(f"Winner: Alphable (by {s_az - s_rand:.0f} points)")
        elif s_rand > s_az:
            print(f"Winner: Random Bot (by {s_rand - s_az:.0f} points)")
        else:
            print("Result: TIE")
        print(f"======================================================================")

    print(f"\n======================================================================")
    print(f"OVERALL RESULTS")
    print(f"======================================================================")
    print(f"Alphable Wins: {az_wins}/{games_to_play}")
    print(f"Win Rate: {az_wins/games_to_play*100:.1f}%")
    print(f"======================================================================")

if __name__ == "__main__":
    evaluate()