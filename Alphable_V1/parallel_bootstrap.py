import time
import os
import sys

# --- CRITICAL GPU CONFIGURATION (Same as train.py) ---
os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TF_FORCE_GPU_ALLOW_GROWTH"] = "true"
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import pyspiel
import numpy as np
import tensorflow as tf
from open_spiel.python.algorithms.alpha_zero import model as model_lib
from open_spiel.python.algorithms.alpha_zero.model import TrainInput
from open_spiel.python.utils import spawn
import scrabble 
import random
from collections import deque
import multiprocessing as mp

# --- CONFIGURATION ---
BATCH_SIZE = 256
BUFFER_SIZE = 10000
TRAIN_STEPS = 20000  # How many updates to perform
GAMES_PER_STEP = 10   # How many games to play before training
UPDATES_PER_STEP = 50 # Train 50 times on the data before moving on
CHECKPOINT_DIR = "data/scrabble_az_checkpoints"
NUM_WORKERS = 8       # Number of parallel game-playing workers

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

def play_game_worker(worker_id, games_to_play, result_queue):
    """Worker process that plays greedy vs greedy games and returns training data."""
    # Load game in worker process
    game = pyspiel.load_game("scrabble")
    bot = GreedyBot(game)
    
    for game_num in range(games_to_play):
        state = game.new_initial_state()
        game_history = []
        
        while not state.is_terminal():
            player = state.current_player()
            action = bot.select_action(state)
            obs = state.observation_tensor(player)
            game_history.append((obs, action, player))
            state.apply_action(action)
        
        returns = state.returns()
        
        # Package training data
        training_examples = []
        for obs, action, player in game_history:
            policy_target = one_hot_action(action, 452)
            value_target = returns[player]
            training_examples.append((obs, policy_target, value_target))
        
        # Send back to main process
        result_queue.put(training_examples)
    
    # Signal completion
    result_queue.put(None)

def main(unused_argv):
    print(f"--- PARALLEL BOOTSTRAP TRAINING ---")
    print(f"Workers: {NUM_WORKERS} | Batch: {BATCH_SIZE} | Updates/Step: {UPDATES_PER_STEP}")
    print(f"Goal: Mimic Greedy Bot with {NUM_WORKERS}x parallelization")
    
    game = pyspiel.load_game("scrabble")
    
    # 1. Initialize Model (in main process only)
    model = model_lib.Model.build_model(
        "resnet", 
        [35,15,15], 
        452, 
        64, 3, 
        learning_rate=0.0001, 
        weight_decay=1e-4,
        path=CHECKPOINT_DIR
    )
    
    buffer = deque(maxlen=BUFFER_SIZE)
    start_time = time.time()
    
    for step in range(TRAIN_STEPS):
        step_start = time.time()
        
        # A. GENERATE DATA IN PARALLEL
        games_per_worker = GAMES_PER_STEP // NUM_WORKERS
        remainder = GAMES_PER_STEP % NUM_WORKERS
        
        # Create result queue for collecting data
        result_queue = mp.Queue()
        
        # Spawn worker processes
        workers = []
        for worker_id in range(NUM_WORKERS):
            # Distribute remainder games among first few workers
            games_for_this_worker = games_per_worker + (1 if worker_id < remainder else 0)
            
            p = mp.Process(
                target=play_game_worker,
                args=(worker_id, games_for_this_worker, result_queue)
            )
            p.start()
            workers.append(p)
        
        # Collect results from all workers
        new_data_count = 0
        completed_workers = 0
        
        while completed_workers < NUM_WORKERS:
            result = result_queue.get()
            if result is None:
                completed_workers += 1
            else:
                # Add training examples to buffer
                for example in result:
                    buffer.append(example)
                    new_data_count += 1
        
        # Wait for all workers to finish
        for p in workers:
            p.join()
        
        generation_time = time.time() - step_start
        
        # B. TRAIN NETWORK (Aggressive Loop)
        if len(buffer) >= BATCH_SIZE:
            train_start = time.time()
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
            
            train_time = time.time() - train_start
            elapsed = time.time() - start_time
            
            print(f"Step {step+1}/{TRAIN_STEPS} | Time: {elapsed:.0f}s | "
                  f"Gen: {generation_time:.1f}s | Train: {train_time:.1f}s | "
                  f"Buffer: {len(buffer)} | New: {new_data_count} | "
                  f"Loss: {avg_loss:.4f} (Pol: {p_loss:.4f}, Val: {v_loss:.4f})")
            
            # C. SAVE CHECKPOINT
            if (step + 1) % 50 == 0:
                print(f"   >>> Saving checkpoint-{step+1}...")
                model.save_checkpoint(step + 1)
        else:
            elapsed = time.time() - start_time
            print(f"Step {step+1}: Filling buffer ({len(buffer)}/{BATCH_SIZE}) | "
                  f"Time: {elapsed:.0f}s | Gen: {generation_time:.1f}s")

if __name__ == "__main__":
    with spawn.main_handler():
        sys.exit(main(sys.argv))
