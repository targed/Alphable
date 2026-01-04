import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TF_FORCE_GPU_ALLOW_GROWTH"] = "true"
import pyspiel
from open_spiel.python.algorithms.alpha_zero import model as model_lib
from open_spiel.python.algorithms.alpha_zero import evaluator as az_evaluator
from open_spiel.python.algorithms import mcts
import scrabble

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
    game = pyspiel.load_game("scrabble")
    
    # Load AZ Model
    checkpoint_path = "./data/scrabble_az_checkpoints"
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
    
    print(f"--- AlphaZero vs Greedy Bot ---")

    for i in range(games_to_play):
        state = game.new_initial_state()
        
        # Alternate who goes first
        if i % 2 == 0:
            p0, p1 = az_bot, greedy_bot
            p0_name, p1_name = "AlphaZero", "Greedy"
        else:
            p0, p1 = greedy_bot, az_bot
            p0_name, p1_name = "Greedy", "AlphaZero"
            
        print(f"Game {i+1}: {p0_name} goes first")
        
        while not state.is_terminal():
            player_id = state.current_player()
            bot = p0 if player_id == 0 else p1
            
            try:
                action = bot.step(state)
                state.apply_action(action)
            except Exception as e:
                print(f"Crash: {e}")
                break
            
        # Results
        score = state.returns()
        # Returns are now [+1, -1] or raw scores depending on your fix.
        # Let's check raw scores from state.scores directly to be sure.
        raw_scores = state.scores
        
        az_idx = 0 if i % 2 == 0 else 1
        greedy_idx = 1 - az_idx
        
        s_az = raw_scores[az_idx]
        s_gr = raw_scores[greedy_idx]
        
        if s_az > s_gr:
            az_wins += 1
            print(f"  Result: AZ Wins ({s_az:.0f} vs {s_gr:.0f})")
        else:
            print(f"  Result: Greedy Wins ({s_gr:.0f} vs {s_az:.0f})")

    print(f"Final Win Rate: {az_wins}/{games_to_play}")

if __name__ == "__main__":
    # Update this to your latest checkpoint
    evaluate(530)