import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"
import pyspiel
import numpy as np
from open_spiel.python.algorithms.alpha_zero import model as model_lib
from open_spiel.python.algorithms.alpha_zero import evaluator as az_evaluator
from open_spiel.python.algorithms import mcts
import scrabble

def evaluate(checkpoint_num):
    game = pyspiel.load_game("scrabble")
    
    # Load YOUR bot
    model = model_lib.Model.build_model("resnet", [35,15,15], 452, 64, 2,
                                        weight_decay=1e-4, learning_rate=0.001,
                                        path="./data/scrabble_az_checkpoints")
    checkpoint_path = f"./data/scrabble_az_checkpoints/checkpoint-{checkpoint_num}"
    model.load_checkpoint(checkpoint_path)
    az_eval = az_evaluator.AlphaZeroEvaluator(game, model)
    
    # 10 simulations for speed
    az_bot = mcts.MCTSBot(game, 2.0, 10, evaluator=az_eval)
    
    # Random Bot (0 simulations = pure rollouts, or just random picker)
    # Using MCTS with low sims and Random Rollout Evaluator acts like a "Weak" bot
    random_bot = mcts.MCTSBot(game, 2.0, 10, evaluator=mcts.RandomRolloutEvaluator())

    az_wins = 0
    games_to_play = 5
    
    print(f"--- Evaluator: AlphaZero (Ckpt {checkpoint_num}) vs Random ---")

    for i in range(games_to_play):
        state = game.new_initial_state()
        # Swap who goes first
        p0 = az_bot if i % 2 == 0 else random_bot
        p1 = random_bot if i % 2 == 0 else az_bot
        p0_name = "AlphaZero" if i % 2 == 0 else "Random"
        
        while not state.is_terminal():
            if state.current_player() == 0:
                action = p0.step(state)
            else:
                action = p1.step(state)
            state.apply_action(action)
            
        # Score
        score = state.returns()
        # If i%2==0, AZ is P0 (index 0). If score[0] > score[1], AZ won.
        az_score = score[0] if i % 2 == 0 else score[1]
        rand_score = score[1] if i % 2 == 0 else score[0]
        
        if az_score > rand_score:
            az_wins += 1
            print(f"Game {i+1}: AZ Wins ({az_score} vs {rand_score})")
        else:
            print(f"Game {i+1}: Random Wins ({rand_score} vs {az_score})")

    print(f"Win Rate: {az_wins}/{games_to_play}")

if __name__ == "__main__":
    # Change 1000 to whatever your latest checkpoint is
    evaluate(530)