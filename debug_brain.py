import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import pyspiel
import numpy as np
from open_spiel.python.algorithms.alpha_zero import model as model_lib
import scrabble

def get_action_string(state, action_id):
    """Convert action ID to readable string."""
    if action_id == 450: return "PASS"
    if action_id == 451: return "EXCHANGE"
    
    try:
        if hasattr(state, "_current_move_map") and action_id in state._current_move_map:
            m = state._current_move_map[action_id]
            return f"'{m['word']}' at ({m['row']},{m['col']}) {m['dir']}"
    except Exception:
        pass
        
    return f"Action {action_id}"

class GreedyBot:
    def __init__(self, game): self.game = game
    def select_action(self, state):
        # Ensure map is populated
        if not hasattr(state, "_current_move_map") or not state._current_move_map:
            state._legal_actions(state.current_player())
            
        legal = state.legal_actions()
        if not legal: return 450
        
        best_action = legal[0]
        max_score = -1.0
        
        for aid in legal:
            if aid >= 450: continue
            if aid in state._current_move_map:
                m = state._current_move_map[aid]
                try:
                    s, _ = state._score_move(m['row'], m['col'], m['word'], m['dir'])
                    if s > max_score:
                        max_score = s
                        best_action = aid
                except: pass
        return best_action

def debug(checkpoint_num):
    game = pyspiel.load_game("scrabble")
    checkpoint_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "scrabble_az_checkpoints"))
    model = model_lib.Model.build_model(
        "resnet", [35,15,15], 452, 64, 3,  # MUST MATCH YOUR TRAIN CONFIG (width=64, depth=3)
        path=checkpoint_path,
        learning_rate=0.001, weight_decay=1e-4
    )
    model.load_checkpoint(f"data/scrabble_az_checkpoints/checkpoint-{checkpoint_num}")
    greedy = GreedyBot(game)
    
    state = game.new_initial_state()
    
    # Fast forward a few random moves to get a mid-game state
    for _ in range(4):
        state.apply_action(np.random.choice(state.legal_actions()))
    
    # Ensure move map is populated for action descriptions
    state._legal_actions(state.current_player())
    
    print(f"\n--- BRAIN SCAN (Turn {state.turn_count}) ---")
    print(f"\nCurrent Board:")
    print(state)
    print(f"\nPlayer {state.current_player()} Rack: {state.racks[state.current_player()]}")
    print(f"Scores: P0={state.scores[0]:.0f}, P1={state.scores[1]:.0f}")
    
    # 1. Ask Greedy
    greedy_move = greedy.select_action(state)
    greedy_desc = get_action_string(state, greedy_move)
    print(f"\nGreedy Bot Choice: {greedy_desc}")
    
    # 2. Ask Network
    obs = state.observation_tensor()
    outputs = model.inference([obs], [state.legal_actions_mask()])
    policy = outputs[1][0] # The raw probabilities
    
    # Get top 10 Network moves
    top_indices = np.argsort(policy)[-10:][::-1]
    
    print(f"\nNetwork Top 10 Moves:")
    for i, idx in enumerate(top_indices, 1):
        prob = policy[idx]
        action_desc = get_action_string(state, idx)
        is_greedy = " ⭐ GREEDY CHOICE" if idx == greedy_move else ""
        print(f"  {i}. [{prob:.4f}] {action_desc}{is_greedy}")

if __name__ == "__main__":
    debug(2000)