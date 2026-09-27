# Alphable V3: Technical Bugs & Post-Mortems

This document provides in-depth technical post-mortems for the ten critical bugs identified, root-caused, and resolved across the development of **Alphable V3**.

---

## Table of Contents
1. [Bug 1: Unweighted Perpendicular Cross-Word Scoring](#bug-1-unweighted-perpendicular-cross-word-scoring)
2. [Bug 2: Pre-Move Observation Leak in After-State Trajectories](#bug-2-pre-move-observation-leak-in-after-state-trajectories)
3. [Bug 3: Blackwell GPU (RTX 5070 Ti) CUDA 13 `cudnnGetVersion` Abort](#bug-3-blackwell-gpu-rtx-5070-ti-cuda-13-cudnngetversion-abort)
4. [Bug 4: Woogles Player Username KeyError & Static Bag Depletion](#bug-4-woogles-player-username-keyerror--static-bag-depletion)
5. [Bug 5: Minimax Zero-Sum Opponent Move Points Omission in Search](#bug-5-minimax-zero-sum-opponent-move-points-omission-in-search)
6. [Bug 6: Ghost Tile Exchange Modal Collision](#bug-6-ghost-tile-exchange-modal-collision)
7. [Bug 7: Woogles Lobby Click Timeout Crash & Match Isolation](#bug-7-woogles-lobby-click-timeout-crash--match-isolation)
8. [Bug 8: Blank Tile Board Blindness in MoveGenerator](#bug-8-blank-tile-board-blindness-in-movegenerator)
9. [Bug 9: Double-Blank Heuristic Hoarding Trap](#bug-9-double-blank-heuristic-hoarding-trap)
10. [Bug 10: Playwright CSS Selector Syntax Parsing Error](#bug-10-playwright-css-selector-syntax-parsing-error)

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
The network was trained to predict the outcome of a move given the board *before* the move was played, rather than evaluating the state *created* by the move.

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

## Bug 4: Woogles Player Username KeyError & Static Bag Depletion

### Symptoms
Running `prepare_dataset.py` on `data/woogles/data/training_dataset.jsonl` crashed on every game with `Error: 'BestBot'`, emitting 0 samples.

### Root Cause
1. **Username String Indexing:** Woogles replay files record player names as strings (e.g. `'BestBot'`, `'CarlSagan121520'`). `player_scores[player_idx]` (which only had integer keys `{0: 0, 1: 0}`) threw a `KeyError`.
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

## Bug 5: Minimax Zero-Sum Opponent Move Points Omission in Search

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
opp_equities = [float(p) + 25.0 * v for p, v in zip(opp_move_points, opp_vals)]
topk_equities = sorted(opp_equities, reverse=True)[:k]

exp_weights = [math.exp((eq - topk_equities[0]) / 5.0) for eq in topk_equities]
expected_opp_equity = sum(w * eq for w, eq in zip(exp_weights, topk_equities)) / sum(exp_weights)

sim_value = -expected_opp_equity / 25.0
total_simulation_value += sim_value
```

### Verification
In live match benchmarks against `GreedyBot`, win rate jumped from **16.7% to 60.0% to 80.0%**.

---

## Bug 6: Ghost Tile Exchange Modal Collision

### Symptoms
During match series on Woogles, the bot froze on Turn 1 with `Generated 0 legal moves`, unable to place any tiles despite having tiles in hand.

### Root Cause
In [`src/alphable/platform/woogles/adapter.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/platform/woogles/adapter.py):
When Woogles renders an exchange modal (`.ant-modal.exchange`), it creates a hidden `#rack` inside the modal with empty `.tile` elements.
In `wait_for_my_turn()`, the selector `page.locator(".rack-container .tile, #rack .tile")` matched the hidden modal rack elements first, returning an empty list `[]` for the player's rack.

### The Fix
Scoped all rack tile lookups strictly to the active player rack:
```python
# Disregard any tiles inside hidden modals
active_rack = self.page.locator(".board-container #rack .tile, .rack-container:not(.exchange) .tile")
```

### Verification
Simulated open and closed modal DOM fixtures in `tests/platform/test_woogles_adapter.py`. Confirmed active player rack tiles extract correctly regardless of modal visibility.

---

## Bug 7: Woogles Lobby Click Timeout Crash & Match Isolation

### Symptoms
During long overnight series (e.g. 90 games), a single timeout in the lobby (`Waiting for .bot`) crashed the entire runner process, losing the remainder of the series.

### Root Cause
In [`src/alphable/platform/runner.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/platform/runner.py), `create_game()` exceptions were unhandled inside the series loop, propagating directly to the top-level CLI and terminating execution.

### The Fix
Wrapped match execution in per-match isolation with automated exponential backoff and lobby navigation reset:
```python
for match_num in range(1, total_games + 1):
    try:
        self._execute_single_game(config)
    except Exception as e:
        print(f"Match {match_num} encountered error: {e}. Resetting to lobby...")
        self.adapter.reset_to_lobby()
```

### Verification
Tested runner fault-tolerance with mock disconnects. The runner successfully navigated back to the lobby and initiated the next scheduled match.

---

## Bug 8: Blank Tile Board Blindness in MoveGenerator

### Symptoms
In Match `dZHivErkZo` (Turn 4), Alphable held `AEIINRT`. Macondo identified `B1 INERTIA` (+69 pts bingo) hooking onto `e` in `eTHANOL`. Alphable could not find `INERTIA` and played `AI` (+10 pts) instead, losing 42.6 points of equity.

### Root Cause
In [`src/alphable/core/structure.pyx`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/structure.pyx):
When a blank tile is played on the board, it is recorded as a lowercase character (e.g. `'e'`).
In `_compute_cross_checks`, cross-word candidates like `Ae` were passed to `_fast_word_check(word)`.
GADDAG dictionary keys are strictly uppercase (`'A'`–`'Z'`). Lowercase `'e'` is not in the tree, so `_fast_word_check("Ae")` returned `False`.
Consequently, cross-checks for all squares adjacent to an existing blank evaluated to `set()` (empty). Moves could neither hook onto blanks nor extend through blanks.

### The Fix
Added `.upper()` normalization across cross-check extraction and recursive traversal in `structure.pyx` and `structure.py`:
```python
up_part = board[curr][c].upper() + up_part
down_part += board[curr][c].upper()
candidate = up_part + char + down_part
if self._fast_word_check(candidate.upper()):
    valid_chars.add(char)
```
Recompiled the Cython binary `structure.cpython-311-x86_64-linux-gnu.so`.

### Verification
Created `tests/core/test_blank_movegen.py`. Legal move generation on the `dZHivErkZo` board increased from 802 to 966 moves (+164 moves). `INERTIA` at (0, 1) Down (+69 pts) was generated and chosen with a +43.4 equity lead.

---

## Bug 9: Double-Blank Heuristic Hoarding Trap

### Symptoms
In Match `iehwTxMUyb` (Turn 1), Alphable held `??AEINO`. Instead of playing a 62-point opening bingo (`DOMAINE` / `ELATION`), it played `NAOI` (+8 pts) to hoard both blanks.

### Root Cause
In [`src/alphable/core/leave_eval.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/leave_eval.py):
`compute_leave_equity` added $+26.5$ points per blank tile with zero duplicate penalty:
$$\text{Leave}(?) = +26.5 \quad \Longrightarrow \quad \text{Leave}(??) = +53.0$$
A small 4-point play leaving `??` was credited with $4 + 53 = 57$ heuristic points, rivaling a 62-point bingo!

### The Fix
Implemented duplicate blank diminishing returns matching Super-Leaves equity tables:
```python
if blank_count > 1:
    # First blank = +26.5; second blank adds +6.0 (total ~+32.5)
    equity -= 20.5 * (blank_count - 1)
```

### Verification
Added `test_duplicate_blank_diminishing_returns` in `tests/core/test_leave_eval.py`. Re-running Turn 1 with `??AEINO` showed opening bingos winning by nearly 40 points of equity over short plays; Alphable chose `ADONISE` (+62 pts).

---

## Bug 10: Playwright CSS Selector Syntax Parsing Error

### Symptoms
When starting a Woogles match series, the bot crashed immediately on lobby navigation:
```
playwright._impl._errors.Error: Locator.wait_for: Unexpected token "=" while parsing css selector ".bot, button:has-text('Play a computer'), text='Play a computer'". Did you mean to CSS.escape it?
```

### Root Cause
In [`adapter.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/platform/woogles/adapter.py) and [`selectors.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/platform/woogles/selectors.py):
When a selector string contains commas (e.g. `.bot, button:has-text('...'), text='...'`), Playwright treats the entire string as a standard CSS selector list. In CSS, `text='...'` is invalid syntax.

### The Fix
Replaced standalone engine prefix `text=...` with Playwright's CSS pseudo-class `:text(...)`:
```python
"btn_play_computer": ".bot, button:has-text('Play a computer'), :text('Play a computer')"
"btn_create_game_lobby": "button:has-text('Create a game'), :text('Create a game')"
```

### Verification
Validated selector parsing against live Playwright DOM instances (0 syntax errors). Verified all 19 tests in `tests/platform/test_woogles_adapter.py` passing.
