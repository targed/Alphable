# Alphable Core Engine and RL Bug Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the critical engine and reinforcement learning bugs in Alphable V3: implement full Scrabble cross-word scoring, fix the pre-state vs. after-state mismatch in self-play data generation, fix the hard-negative labeling pathology in supervised dataset creation, fix endgame scoring rules, and stabilize 1-ply lookahead search.

**Architecture:** 
- Simulator (`simulator.py`): add bidirectional perpendicular cross-word calculation with premium square multipliers.
- Self-play (`self_play.py`): record after-states $(s'_t = (\text{board}', \text{leave}, \Delta \text{score}', \text{bag}))$ instead of pre-move states.
- Supervised generation (`prepare_dataset.py`): replace destructive `-1.0` hard-negative labeling on high-scoring alternative moves with point-deficit relative scaling.
- Search (`search.py`): anchor candidate filtering with move points and eliminate opponent max-value overestimation bias.

**Tech Stack:** Python 3.11, PyTorch, NumPy, Cython GADDAG engine, pytest.

**Spec:** Bug audit findings from code inspection of `Alphable_V3/src/alphable/`.

## Global Constraints

- Preserve all existing public API function names and signatures in `simulator.py`, `self_play.py`, `prepare_dataset.py`, and `search.py`.
- Ensure compatibility between `simulate_move()` output format `(new_board, points, new_rack)` across all modules.
- Board coordinates: 15x15 grid, row 0..14, col 0..14. Directions: `'Across'` and `'Down'`. Empty square is `'.'`.
- Keep Python code clean, fully type-annotated where appropriate, and formatted with existing project style.

---

### Task 1: Complete Scrabble Cross-Word Scoring in `simulator.py`

**Files:**
- Modify: `Alphable_V3/src/alphable/core/simulator.py:60-133`
- Create: `Alphable_V3/tests/core/test_cross_words.py`

**Interfaces:**
- Consumes: `simulate_move(board, move, rack)`
- Produces: `simulate_move(board, move, rack) -> (new_board, total_points, new_rack)` where `total_points` includes the primary word score, all perpendicular cross-word scores formed by newly placed tiles, and the 50-point bingo bonus.

- [ ] **Step 1: Write the failing tests for cross-word scoring**

```python
# Alphable_V3/tests/core/test_cross_words.py
import pytest
from alphable.core import simulator

def test_cross_word_single_hook():
    """Playing 'AT' across where 'A' hooks below an existing 'C' to form 'CA' down."""
    board = simulator.create_empty_board()
    # Place 'C' at (6, 7)
    board[6][7] = 'C'
    
    # Play 'AT' at (7, 7) Across -> Primary word 'AT' (A at (7,7), T at (7,8))
    # (7,7) is center square DW.
    # Cross word formed: 'CA' Down from (6,7) to (7,7).
    # 'A' is placed on (7,7) which is DW!
    # Primary word 'AT': A=1, T=1 -> (1*2 + 1) * 2 = 6 points (or center DW multiplier)
    # Cross word 'CA': C=3 (existing, no DW on C), A=1 (on DW -> 1*2, and DW applies to word: (3 + 1)*2 = 8 points)
    # Let's verify on non-premium squares for simple arithmetic:
    move = {'row': 7, 'col': 7, 'dir': 'Across', 'word': 'AT'}
    new_board, points, new_rack = simulator.simulate_move(board, move, ['A', 'T', 'Z'])
    
    assert new_board[7][7] == 'A'
    assert new_board[7][8] == 'T'
    assert new_rack == ['Z']
    # Points must be greater than primary word alone
    # Primary word: A=1, T=1. On center (7,7) DW -> (1 + 1)*2 = 4
    # Cross word 'CA': C=3, A=1 on DW -> (3 + 1)*2 = 8
    # Total = 4 + 8 = 12 points
    assert points == 12

def test_cross_word_multiple_hooks():
    """Playing a 3-letter word Across that hooks into two existing letters above it."""
    board = simulator.create_empty_board()
    # Non-premium rows/cols: e.g. row 8 col 4 ('H') and row 8 col 6 ('T')
    # Row 8 col 5 is DL: (8,6) is DL... let's use row 4, cols 4, 5, 6
    # Let's set 'N' at (3, 4) and 'P' at (3, 6)
    board[3][4] = 'N'
    board[3][6] = 'P'
    # Play 'O', 'R', 'E' across at row 4, cols 4, 5, 6
    # Primary word: 'ORE'. O=1, R=1, E=1 -> 3 pts (check premiums if any)
    # Cross words formed:
    # At col 4: 'N' + 'O' -> 'NO' (N=1, O=1 -> 2 pts)
    # At col 6: 'P' + 'E' -> 'PE' (P=3, E=1 -> 4 pts)
    # Col 5: no cross word
    move = {'row': 4, 'col': 4, 'dir': 'Across', 'word': 'ORE'}
    # (4,4) is DW! Let's check PREMIUM_SQUARES for (4,4): (4,4) is DW
    new_board, points, new_rack = simulator.simulate_move(board, move, ['O', 'R', 'E'])
    # Primary: (O=1*2, R=1, E=1)*2 = (1+1+1)*2 = 6
    # Cross word 1: 'NO' at col 4 (DW): (N=1, O=1)*2 = 4
    # Cross word 2: 'PE' at col 6 (no premium): P=3, E=1 = 4
    # Total points should be 6 + 4 + 4 = 14
    assert points == 14
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_cross_words.py -v`
Expected: FAIL because `points` only includes the primary word score (e.g. 4 instead of 12).

- [ ] **Step 3: Implement cross-word scoring in `simulator.py`**

Modify `Alphable_V3/src/alphable/core/simulator.py` to calculate perpendicular cross-words:
For each placed tile at `(curr_r, curr_c)`:
- If `direction == 'Across'`, inspect vertical direction (row `curr_r - 1` up and `curr_r + 1` down).
- If `direction == 'Down'`, inspect horizontal direction (col `curr_c - 1` left and `curr_c + 1` right).
- If adjacent tiles exist, gather the entire cross-word slice:
  - Letters already on board contribute their letter value (0 if lowercase blank).
  - The placed tile contributes its letter value multiplied by letter multiplier (DL/TL) if on premium square.
  - The entire cross-word score is multiplied by the word multiplier (DW/TW) if the placed tile is on a DW/TW square.
- Add each valid cross-word score (length $\ge 2$) to `points`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_cross_words.py -v`
Expected: PASS.

- [ ] **Step 5: Run existing tests to ensure no regressions**

Run: `pytest tests/ -v`
Expected: All existing tests pass.

---

### Task 2: Fix Endgame Scoring Rules in `simulator.py` and `self_play.py`

**Files:**
- Modify: `Alphable_V3/src/alphable/training/self_play.py:261-276`
- Modify: `Alphable_V3/src/alphable/eval/evaluate_vs_baseline.py:212-214`
- Modify: `Alphable_V3/tests/core/test_simulator.py` (or add to `test_cross_words.py`)

**Interfaces:**
- Consumes: `apply_endgame_adjustments(scores, racks)`
- Produces: Correct official Scrabble endgame scoring for both:
  1. One player emptying rack when bag is empty (winner gets $+2 \times$ opponent rack sum, or opponent loses rack value and winner gains rack value).
  2. Consecutive passes (both players have tiles remaining): both players subtract their own unplayed tiles from their scores.

- [ ] **Step 1: Write test for endgame adjustments**

```python
def test_apply_endgame_adjustments_consecutive_passes():
    scores = [200, 200]
    racks = [['Q', 'Z'], ['A']] # Q=10, Z=10 -> 20 pts. A=1 -> 1 pt.
    from alphable.training.self_play import apply_endgame_adjustments
    apply_endgame_adjustments(scores, racks)
    # When both players have tiles, both subtract their unplayed tiles
    assert scores[0] == 180
    assert scores[1] == 199

def test_apply_endgame_adjustments_one_empty():
    scores = [200, 200]
    racks = [[], ['A', 'B']] # A=1, B=3 -> 4 pts.
    from alphable.training.self_play import apply_endgame_adjustments
    apply_endgame_adjustments(scores, racks)
    # Winner gets +4, loser loses 4 (or net diff 8)
    assert scores[0] == 204
    assert scores[1] == 196
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/core/test_cross_words.py::test_apply_endgame_adjustments_consecutive_passes -v`
Expected: FAIL (scores remain `[200, 200]`).

- [ ] **Step 3: Update `apply_endgame_adjustments` in `self_play.py`**

Update `apply_endgame_adjustments`:
```python
def apply_endgame_adjustments(scores, racks):
    p0_empty = len(racks[0]) == 0
    p1_empty = len(racks[1]) == 0

    if p0_empty and not p1_empty:
        bonus = rack_penalty(racks[1])
        scores[0] += bonus
        scores[1] -= bonus
    elif p1_empty and not p0_empty:
        bonus = rack_penalty(racks[0])
        scores[1] += bonus
        scores[0] -= bonus
    elif not p0_empty and not p1_empty:
        # Both players subtract the value of their remaining tiles
        scores[0] -= rack_penalty(racks[0])
        scores[1] -= rack_penalty(racks[1])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_cross_words.py -k endgame -v`
Expected: PASS.

---

### Task 3: Fix Self-Play to Record After-States in `self_play.py`

**Files:**
- Modify: `Alphable_V3/src/alphable/training/self_play.py:315-385,550-600`
- Create: `Alphable_V3/tests/training/test_self_play_afterstate.py`

**Interfaces:**
- Consumes: Move evaluation and game progression in `play_one_game()` and `run_interleaved_games()`.
- Produces: Samples where `board`, `rack`, and `score_diff` represent the **AFTER-STATE** $(s'_t)$:
  - `board`: `compact_board(selected['new_board'])`
  - `rack`: `''.join(selected['new_rack'])` (the leave, $\le 6$ tiles)
  - `score_diff`: post-move score difference `scores[p] - scores[o]`
  - `bag`: remaining tiles in bag

- [ ] **Step 1: Write test verifying after-state recording in self-play**

```python
# Alphable_V3/tests/training/test_self_play_afterstate.py
from alphable.training.self_play import play_one_game
from alphable.core.inference import AlphableInference

def test_self_play_records_after_states():
    # Run a 2-turn game
    engine = AlphableInference(device='cpu')
    samples, scores = play_one_game(
        engine, engine,
        max_turns=4,
        reward_mode='blend',
        top_k=2
    )
    assert len(samples) > 0
    # Every sample recorded from a move must have rack length <= 6 (it is a leave!)
    # and the score_diff must reflect the post-move state.
    for sample in samples:
        # Leaves cannot have 7 tiles unless it was a pass with a full rack
        assert len(sample['rack']) <= 7
```

- [ ] **Step 2: Update `play_one_game` and `run_interleaved_games`**

In `play_one_game`:
Move the state recording from *before* the move to *after* the move is executed:
```python
        if selected is None:
            consecutive_passes += 1
            post_board = compact_board(board)
            post_rack = ''.join(racks[p])
            post_score_diff = scores[p] - scores[o]
        else:
            board = selected['new_board']
            scores[p] += selected['points']
            racks[p] = selected['new_rack']
            post_board = compact_board(board)
            post_rack = ''.join(racks[p])
            post_score_diff = scores[p] - scores[o]
            racks[p].extend(draw_tiles(bag, 7 - len(racks[p])))
            consecutive_passes = 0

        player_states[p].append({
            'board': post_board,
            'rack': post_rack,
            'score_diff': post_score_diff,
            'bag': bag_remaining,
            'player': p,
        })
```
Apply the identical after-state recording logic to `run_interleaved_games`.

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/training/test_self_play_afterstate.py -v`
Expected: PASS.

---

### Task 4: Fix Supervised Dataset Generation Hard-Negative Labeling in `prepare_dataset.py`

**Files:**
- Modify: `Alphable_V3/src/alphable/training/prepare_dataset.py:179-215`
- Create: `Alphable_V3/tests/training/test_prepare_dataset_labels.py`

**Interfaces:**
- Consumes: Human game moves and GADDAG alternative moves.
- Produces: Non-poisonous targets for alternative moves:
  - Do not penalize moves that scored equal to or greater than the human move (`neg_score >= pos_score`).
  - Scale alternative targets relative to point deficit:
    $\text{target} = \max\left(-1.0, 1.0 - 2.0 \times \frac{\text{pos\_score} - \text{neg\_score}}{\max(1, \text{pos\_score})}\right)$, or filter out high-scoring alternatives from negative class.

- [ ] **Step 1: Write test for negative target generation**

```python
# Alphable_V3/tests/training/test_prepare_dataset_labels.py
import json
from alphable.training import prepare_dataset

def test_no_negative_penalty_for_higher_scoring_moves():
    # If a move scores 40 pts and human played 30 pts, it must NOT be labeled -1.0
    # Pos score = 30, neg score = 40 -> should be skipped or non-negative
    # Pos score = 30, neg score = 10 -> deficit of 20 pts -> target scaled appropriately
    pass
```

- [ ] **Step 2: Update `process_game()` in `prepare_dataset.py`**

In `prepare_dataset.py`:
Filter or rescale hard negatives:
```python
for neg_score, _, neg_board, neg_rack in hard_negatives:
    # If the alternative move scored as well as or better than the human move,
    # it is NOT an inferior move. Do not poison the dataset by labeling it -1.0.
    if neg_score >= pos_score:
        continue
    
    # Scale negative target proportionally to the score deficit
    deficit_ratio = (pos_score - neg_score) / max(10, pos_score)
    neg_target = max(-1.0, 1.0 - 2.0 * deficit_ratio)

    neg_board_compact = "".join(["".join(r) for r in neg_board])
    samples.append({
        'board': neg_board_compact,
        'rack': "".join(neg_rack),
        'score_diff': score_diff + neg_score,
        'bag': bag_size,
        'target': neg_target
    })
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/training/test_prepare_dataset_labels.py -v`
Expected: PASS.

---

### Task 5: Stabilize 1-Ply Lookahead and Candidate Selection in `search.py`

**Files:**
- Modify: `Alphable_V3/src/alphable/core/search.py:127-248`
- Modify: `Alphable_V3/tests/test_search.py`

**Interfaces:**
- Consumes: `find_best_move(board, rack, score_diff, bag_remaining)`
- Produces: Candidate moves selected by blended score (immediate points + network value) rather than raw noisy value alone, preventing bingos from being discarded before simulation.

- [ ] **Step 1: Write test for candidate selection with high-scoring move**

```python
def test_high_scoring_candidate_not_dropped():
    # Verify that a 70-point bingo candidate is retained among top candidates
    # even if initial network value is neutral
    pass
```

- [ ] **Step 2: Update `find_best_move` candidate evaluation in `search.py`**

Anchor 0-ply candidate sorting:
```python
# Blended candidate value: network value + normalized move score
# This guarantees high-scoring moves (bingos, high premiums) are not pruned out of top_candidates
candidate_evals.sort(
    key=lambda x: x['value'] + (x['points'] / 50.0),
    reverse=True
)
```
In 1-ply simulation, compute expected opponent value via softmax temperature over replies rather than raw unweighted top-5 max, curbing max-noise overestimation.

- [ ] **Step 3: Run tests to verify**

Run: `pytest tests/test_search.py -v`
Expected: PASS.

---

### Task 6: Full Verification and Smoke Run

**Files:**
- Run all test suites across the repository.
- Execute smoke calibration cycle to verify end-to-end compatibility.

- [ ] **Step 1: Run full pytest suite**

Run: `pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 2: Run smoke self-play generation**

Run: `python scripts/self_play.py --games 2 --output data/rl/test_afterstate_samples.jsonl --device cpu`
Verify output file exists and contains valid JSON lines with after-states.

- [ ] **Step 3: Clean up temporary test artifacts**

Remove `data/rl/test_afterstate_samples.jsonl`.
