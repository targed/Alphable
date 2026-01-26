import time
import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import pyspiel
import numpy as np
import tensorflow as tf
from open_spiel.python.algorithms.alpha_zero import model as model_lib
from open_spiel.python.algorithms.alpha_zero.model import TrainInput
import scrabble 
import random
from collections import deque

# --- CONFIGURATION ---
BATCH_SIZE = 256
BUFFER_SIZE = 10000
TRAIN_STEPS = 2000  # How many updates to perform
GAMES_PER_STEP = 10 # How many games to play before training
UPDATES_PER_STEP = 50     # CRITICAL: Train 50 times on the data before moving on
CHECKPOINT_DIR = "data/scrabble_az_checkpoints"

class GreedyBot:
    def __init__(self, game):
        self.game = game
    
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

def one_hot_action(action, num_actions):
    policy = np.zeros(num_actions)
    policy[action] = 1.0
    return policy

def main():
    print(f"--- SUPERCHARGED BOOTSTRAP TRAINING ---")
    print(f"Goal: Mimic Greedy Bot | Batch: {BATCH_SIZE} | Updates/Step: {UPDATES_PER_STEP}")
    
    game = pyspiel.load_game("scrabble")
    
    # 1. Initialize Model
    # Using the same architecture as your target AlphaZero run
    model = model_lib.Model.build_model(
        "resnet", 
        [35,15,15], 
        452, 
        64, 3, 
        learning_rate=0.001, 
        weight_decay=1e-4,
        path=CHECKPOINT_DIR
    )
    
    buffer = deque(maxlen=BUFFER_SIZE)
    bot = GreedyBot(game)
    
    start_time = time.time()
    
    for step in range(TRAIN_STEPS):
        # A. GENERATE DATA (Greedy vs Greedy)
        new_data_count = 0
        for _ in range(GAMES_PER_STEP):
            state = game.new_initial_state()
            game_history = [] 
            
            while not state.is_terminal():
                player = state.current_player()
                action = bot.select_action(state)
                obs = state.observation_tensor(player)
                game_history.append((obs, action, player))
                state.apply_action(action)
            
            returns = state.returns()
            
            for obs, action, player in game_history:
                policy_target = one_hot_action(action, 452)
                value_target = returns[player]
                buffer.append((obs, policy_target, value_target))
                new_data_count += 1
        
        # B. TRAIN NETWORK (Aggressive Loop)
        if len(buffer) >= BATCH_SIZE:
            losses = []
            
            # Train repeatedly on the buffer to force memorization
            for _ in range(UPDATES_PER_STEP): 
                batch = random.sample(buffer, BATCH_SIZE)
                
                # Create TrainInput objects for the batch
                train_inputs = [
                    TrainInput(
                        observation=b[0],
                        legals_mask=np.ones(452),  # All actions considered legal for training
                        policy=b[1],
                        value=b[2]
                    ) for b in batch
                ]
                
                loss = model.update(train_inputs)
                losses.append(loss)
            
            avg_loss = sum(l.total for l in losses) / len(losses)
            p_loss = sum(l.policy for l in losses) / len(losses)
            v_loss = sum(l.value for l in losses) / len(losses)
            
            elapsed = time.time() - start_time
            print(f"Step {step+1}/{TRAIN_STEPS} | Time: {elapsed:.0f}s | Buffer: {len(buffer)} | Loss: {avg_loss:.4f} (Pol: {p_loss:.4f}, Val: {v_loss:.4f})")
            
            # C. SAVE CHECKPOINT
            if (step + 1) % 50 == 0:
                print(f"   >>> Saving checkpoint-{step+1}...")
                model.save_checkpoint(step + 1)
        else:
            print(f"Step {step+1}: Filling buffer ({len(buffer)}/{BATCH_SIZE})...")

if __name__ == "__main__":
    main()