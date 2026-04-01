import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import pyspiel
import numpy as np
from open_spiel.python.algorithms.alpha_zero import model as model_lib
import scrabble

def evaluate():
    print(f"--- EVALUATING RAW NETWORK ---")
    game = pyspiel.load_game("scrabble")
    
    # Load Model
    checkpoint_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "scrabble_az_checkpoints"))
    model = model_lib.Model.build_model(
        "resnet", [35,15,15], 452, 64, 3,  # MUST MATCH YOUR TRAIN CONFIG (width=64, depth=3)
        path=checkpoint_path,
        learning_rate=0.001, weight_decay=1e-4
    )
    model.load_checkpoint(f"{checkpoint_path}/checkpoint-2000")
    print("Loaded Checkpoint 2000")
    
    # 1. Raw Policy Bot (The "Student")
    def raw_policy_bot(state):
        # Get legal moves
        legal = state.legal_actions()
        if not legal: return 450
        
        # Get Network Prediction
        obs = state.observation_tensor()
        outputs = model.inference([obs], [state.legal_actions_mask()])
        # inference returns (value, policy) - we want policy
        policy = outputs[1][0] # The raw probabilities
        
        # Pick the legal move with highest probability
        best_action = legal[0]
        best_prob = -1.0
        
        for action in legal:
            if policy[action] > best_prob:
                best_prob = policy[action]
                best_action = action
                
        return best_action

    # 2. Random Bot (The "Baseline")
    def random_bot(state):
        legal = state.legal_actions()
        return np.random.choice(legal) if legal else 450

    # Play Games
    wins = 0
    total_games = 10
    
    for i in range(total_games):
        state = game.new_initial_state()
        p0_is_network = (i % 2 == 0)
        
        while not state.is_terminal():
            current = state.current_player()
            if (current == 0 and p0_is_network) or (current == 1 and not p0_is_network):
                action = raw_policy_bot(state)
            else:
                action = random_bot(state)
            state.apply_action(action)
            
        # Check Winner
        score = state.returns()
        net_score = score[0] if p0_is_network else score[1]
        rnd_score = score[1] if p0_is_network else score[0]
        
        if net_score > rnd_score:
            wins += 1
            print(f"Game {i+1}: Network WINS ({net_score} vs {rnd_score})")
        else:
            print(f"Game {i+1}: Network LOST ({net_score} vs {rnd_score})")

    print(f"FINAL WIN RATE: {wins}/{total_games}")

if __name__ == "__main__":
    evaluate() # Or your latest checkpoint