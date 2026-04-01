import pyspiel
from open_spiel.python.algorithms import mcts
import random

class GreedyBot:
    def __init__(self, game):
        self.game = game
        
    def step(self, state):
        # Generate all legal actions
        legal_actions = state.legal_actions()
        if not legal_actions: return 450 # Pass
        
        best_action = legal_actions[0]
        max_score = -1.0
        
        # Access the internal move map to simulate scores
        # Note: This relies on your ScrabbleState implementation having _current_move_map
        # We might need to trigger generation if it's empty
        if not hasattr(state, "_current_move_map") or not state._current_move_map:
            state._legal_actions(state.current_player())
            
        for action_id in legal_actions:
            if action_id >= 450: continue # Ignore Pass/Exchange if we have moves
            
            if action_id in state._current_move_map:
                move = state._current_move_map[action_id]
                # We calculate raw score potential
                # We can cheat and use the state's internal score function non-destructively
                try:
                    score, _ = state._score_move(move['row'], move['col'], move['word'], move['dir'])
                    if score > max_score:
                        max_score = score
                        best_action = action_id
                except:
                    continue
                    
        return best_action