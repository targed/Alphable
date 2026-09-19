# Alphable V3: Technical Bugs & Post-Mortems

This document provides in-depth technical post-mortems for the five major bugs identified, root-caused, and resolved during the Alphable V3 development cycle.

---

## Bug 1: Unweighted Perpendicular Cross-Word Scoring

### Symptoms
In game simulations, plays that formed multiple perpendicular cross-words across Double Letter or Triple Word squares were severely under-scored. The simulator often awarded only the unweighted face values of cross-words.

### Root Cause
In [`src/alphable/core/simulator.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/simulator.py), the cross-word scoring loop iterated over adjacent tiles but failed to evaluate:
1. Active square multipliers (DL, TL, DW, TW) on the newly placed tile in the cross-word direction.
2. The immutability of pre-existing board tiles (which must not receive square multipliers again).
3. Zero-point valuation for newly placed blank tiles in cross-words.

### The Fix
Implemented a dedicated perpendicular cross-word extraction function `_score_cross_word`:
```python
def _score_cross_word(board, r, c, tile_char, is_blank, bonus_type):
    # Scan backward and forward in perpendicular direction
    # Compute letter multiplier for newly placed tile:
    # 2x for DL, 3x for TL; 0 pts if is_blank
    # Pre-existing board tiles retain face value only
    # Multiply entire cross-word score by word multiplier (2x for DW, 3x for TW)
```

### Verification
Created unit tests in `tests/core/test_cross_words.py`. Validated multi-word placements with Double Letter, Triple Letter, and Triple Word multipliers (100% pass).

---

## Bug 2: Pre-Move Observation Leak in After-State Trajectories

### Symptoms
In reinforcement learning self-play, the value network converged slowly and struggled to learn accurate positional value from game outcomes.

### Root Cause
In [`src/alphable/training/self_play.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/training/self_play.py), when logging each turn's observation for the training dataset, the code saved the **pre-move** board and pre-move score differential rather than the **after-state** resulting from the move.
- As a consequence, the network was trained to predict the outcome of a move given the board *before* the move was played, rather than evaluating the state *created* by the move.

### The Fix
Updated trajectory recording to record post-action states from the mover's perspective:
```python
player_states[p].append({
    'board': post_board,           # Board AFTER tiles placed
    'rack': post_rack,             # Leave rack remaining
    'score_diff': post_score_diff, # Score diff AFTER points added
    'bag': bag_remaining,
    'player': p,
})
```

### Verification
Created `tests/training/test_self_play_afterstate.py` asserting that all recorded trajectory states reflect post-action boards and leaves.

---

## Bug 3: Blackwell GPU (RTX 5070 Ti) CUDA 13 `cudnnGetVersion` Abort

### Symptoms
Running supervised or RL training on the NVIDIA RTX 5070 Ti (Blackwell / CUDA 13.0) crashed immediately on the first training batch with:
```
Invalid handle. Cannot load symbol cudnnGetVersion
[1] 37451 abort (core dumped) python -m alphable.cli.main train supervised ...
```

### Root Cause
PyTorch 2.6 built against CUDA 12.x had a dynamic symbol mismatch with the system's newer CUDA 13.0 / Blackwell driver when querying cuDNN version symbols.

### The Fix
In [`src/alphable/__init__.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/__init__.py), set:
```python
import torch
# Disable cuDNN to bypass symbol mismatch on Blackwell architecture
torch.backends.cudnn.enabled = False
```
Native ATen CUDA convolution kernels handle all $3 \times 3$ and $1 \times 1$ convolutions seamlessly.

### Performance Verification
Training runs flawlessly without crashes, processing **1,903 samples/second** on CUDA.

---

## Bug 4: Woogles Player Username `KeyError` & Tile Bag Depletion

### Symptoms
Running `prepare_dataset.py` on `data/woogles/data/training_dataset.jsonl` crashed on every game with `Error: 'BestBot'`, emitting 0 samples.

### Root Cause
1. **Username String Indexing:** Woogles replay files record player names as strings (e.g. `'BestBot'`, `'CarlSagan121520'`). Line 104 extracted `player_idx = move_data.get('player')` as a string, causing `player_scores[player_idx]` (which only had integer keys `{0: 0, 1: 0}`) to throw a `KeyError`.
2. **Static Bag Burn:** `bag_size` was decremented by `len(rack)` (~7 tiles) on every turn, completely exhausting the bag by turn 14 and recording all subsequent turns with `bag: 0`.

### The Fix
In [`src/alphable/training/prepare_dataset.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/training/prepare_dataset.py):
1. Built a robust player name mapping resolving usernames, tokens, and numeric IDs to integers `0` and `1`.
2. Replaced static bag burn with exact tile subtraction:
   $$\text{tiles\_used} = \max(0, \text{len}(\text{rack}) - \text{len}(\text{pos\_rack}))$$
   $$\text{bag\_size} = \max(0, \text{bag\_size} - \text{tiles\_used})$$

### Verification
Processed all 580 expert games in `data/woogles/data/training_dataset.jsonl` with 16 parallel workers in 74 seconds, cleanly emitting **9,632 samples**.

---

## Bug 5: Minimax Zero-Sum Opponent Move Points Omission

### Symptoms
In 1-ply lookahead search, Alphable frequently conceded massive 50–60 point plays to `GreedyBot`, resulting in high losses (16.7% win rate).

### Root Cause
In [`src/alphable/core/search.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/search.py), when simulating opponent replies:
```python
# The Bug (Before):
opp_vals = self._batched_forward_values(list(zip(opp_batch_boards, opp_batch_states)))
topk_vals = sorted(opp_vals, reverse=True)[:k]  # Ranked purely by after-state value!
```
The search engine ranked opponent replies purely by raw neural network value `opp_vals`, completely ignoring `opp_points`! Whether the opponent scored 4 points or 80 points, Alphable treated them identically if the after-state values were similar.

### The Fix
Formulated true zero-sum reply equity:
```python
# Opponent move equity: immediate points + 25.0 * after-state value
opp_equities = [float(p) + 25.0 * v for p, v in zip(opp_move_points, opp_vals)]
topk_equities = sorted(opp_equities, reverse=True)[:k]

# Softmax temperature over top replies
exp_weights = [math.exp((eq - topk_equities[0]) / 5.0) for eq in topk_equities]
expected_opp_equity = sum(w * eq for w, eq in zip(exp_weights, topk_equities)) / sum(exp_weights)

# Net equity from our perspective
sim_value = -expected_opp_equity / 25.0
total_simulation_value += sim_value
```

### Verification
1. Added unit test `test_search_penalizes_moves_conceding_high_opponent_equity` in `tests/core/test_search.py`.
2. In live match benchmarks against `GreedyBot`, win rate jumped from **16.7% to 60.0% to 80.0%**.
