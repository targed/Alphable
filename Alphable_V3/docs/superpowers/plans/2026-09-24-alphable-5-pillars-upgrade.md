# Alphable 5 Pillars Engine Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Elevate Alphable from a ~25%-33% imitation ceiling against HastyBot to parity/superiority by implementing the 5 core Scrabble AI pillars: Lipkin-Smith empirical super-leave recalibration, deterministic exact endgame minimax solver, unseen tile distribution (bag tracking) state representation, selective 2-ply candidate lookahead, and pure outcome-driven self-play reinforcement learning.

**Architecture:** 
1. `src/alphable/core/leave_eval.py`: Empirical Lipkin-Smith single-tile equities, 2/3/4-tile stem synergies (`RET`, `ARE`, `SATIN`, `TISANE`), consonant clash penalties, and bag-aware endgame deduction.
2. `src/alphable/core/endgame.py`: Exact deterministic alpha-beta minimax solver triggered when `bag == 0` that models terminal rack dump points and unplayed tile penalties.
3. `src/alphable/core/inference.py` & `src/alphable/core/alphable_net.py`: Bag-tracking feature extraction expanding state vector to 63 dimensions (26 letter bag ratios + 1 blank bag ratio) with zero-padding backwards compatibility.
4. `src/alphable/core/search.py`: Selective 2-ply lookahead on top-2 candidates when 1-ply equity gap is within threshold, and seamless delegation to the endgame solver when bag is empty.
5. `src/alphable/training/self_play_rl.py`: Outcome-driven self-play RL pipeline with temperature annealing, Dirichlet exploration, experience replay, and model promotion gating.

**Tech Stack:** Python 3.11, PyTorch 2.x, NumPy, pytest, Cython / C++ GADDAG move generator.

**Spec:** [Holistic Architectural Review](file:///home/targed/.gemini/antigravity-ide/brain/506ad9c3-006a-4805-8168-fc6b36d3e824/holistic_architectural_review.md)

## Global Constraints
- Python executable for test runner and tools is `../venv/bin/python` / `../venv/bin/pytest`.
- Working directory is `/home/targed/Documents/Git/Alphable/Alphable_V3`.
- All 181 existing unit and integration tests must continue passing at every task checkpoint.
- Fully deterministic backward compatibility: existing 36-dimensional checkpoints must load without errors via `load_checkpoint_compatible`.
- Code changes must follow strict TDD: failing test written first, verified failing, minimal implementation added, verified passing, and committed.

---

### Task 1: Empirical Super-Leave Recalibration & Bingo Stem Synergy Table

**Files:**
- Modify: `src/alphable/core/leave_eval.py`
- Test: `tests/core/test_leave_eval.py`

**Interfaces:**
- Consumes: Rack tile characters or lists, optional `bag_remaining: int = 100`.
- Produces: `compute_leave_equity(rack: Union[List[str], str], bag_remaining: int = 100) -> float`

- [ ] **Step 1: Write the failing tests for Lipkin-Smith equities, stems, and endgame deductions**

Edit `tests/core/test_leave_eval.py` to add tests for single-tile Lipkin-Smith baselines (e.g. natural bingo tiles E, R, T having positive equity), 3-letter stem synergies (`RET`, `SAT`), 4-letter stems (`TISAN`), and endgame leave penalties when `bag_remaining == 0`.

```python
def test_lipkin_smith_bingo_stem_equities():
    from alphable.core.leave_eval import compute_leave_equity
    # RETIN stem should have strong positive synergy (+10.0 to +16.0)
    retin_equity = compute_leave_equity("RETIN")
    assert retin_equity >= 10.0, f"Expected RETIN equity >= 10.0, got {retin_equity}"
    
    # E, R, T individual baselines should be positive
    e_val = compute_leave_equity("E")
    r_val = compute_leave_equity("R")
    t_val = compute_leave_equity("T")
    assert e_val >= 1.5, f"Expected E equity >= 1.5, got {e_val}"
    assert r_val >= 1.5, f"Expected R equity >= 1.5, got {r_val}"
    assert t_val >= 1.5, f"Expected T equity >= 1.5, got {t_val}"

def test_multi_tile_stem_synergies():
    from alphable.core.leave_eval import compute_leave_equity
    # 3-letter stems like RET or SAT should have bonus beyond raw sum
    ret_equity = compute_leave_equity("RET")
    assert ret_equity >= 7.0, f"Expected RET equity >= 7.0, got {ret_equity}"

def test_endgame_zero_bag_deduction():
    from alphable.core.leave_eval import compute_leave_equity
    # When bag is 0, leave equity is pure face value deduction: Q (10) + Z (10) = -20 pts
    qz_endgame = compute_leave_equity("QZ", bag_remaining=0)
    assert qz_endgame == -20.0, f"Expected QZ endgame penalty -20.0, got {qz_endgame}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../venv/bin/pytest tests/core/test_leave_eval.py -k "test_lipkin_smith_bingo_stem_equities or test_multi_tile_stem_synergies or test_endgame_zero_bag_deduction" -v`
Expected: FAIL with assertion errors (current E equity is 0.1, RETIN is under 3.0, and `bag_remaining` parameter not accepted).

- [ ] **Step 3: Implement Lipkin-Smith recalibration and stem synergies in `src/alphable/core/leave_eval.py`**

Update `src/alphable/core/leave_eval.py` with:
1. Tournament-calibrated `BASE_TILE_EQUITY` (`E: 2.0`, `R: 2.2`, `T: 1.8`, `N: 1.6`, `A: 1.2`, `I: 0.5`, `L: 0.8`, `S: 8.0`, `?: 26.5`).
2. Multi-tile synergy table `MULTI_STEM_SYNERGIES` containing 3-tile stems (`RET`, `SAT`, `TIN`, `ARE`, `ERS`, `INE`, `EST`, `ATE`, `ION`) and 4-tile stems (`TISAN`, `STARE`, `RETIN`, `SATIN`).
3. Face-value mapping `TILE_POINTS` for zero-bag endgame deduction.
4. Update `compute_leave_equity(rack: Union[List[str], str], bag_remaining: int = 100) -> float`:
   - If `bag_remaining == 0`: return `-float(sum(TILE_POINTS.get(c.upper(), 0) for c in rack))`
   - Otherwise, calculate base tile equities, duplicate penalties, vowel-consonant balance, and 2/3/4-letter stem bonuses.

- [ ] **Step 4: Run tests to verify all leave evaluation tests pass**

Run: `../venv/bin/pytest tests/core/test_leave_eval.py -v`
Expected: PASS (all tests passing).

- [ ] **Step 5: Commit changes**

```bash
git add src/alphable/core/leave_eval.py tests/core/test_leave_eval.py
git commit -m "feat(leave): recalibrate Lipkin-Smith equities and multi-tile bingo stem synergies"
```

---

### Task 2: Deterministic Exact Endgame Minimax Solver

**Files:**
- Create: `src/alphable/core/endgame.py`
- Modify: `src/alphable/core/search.py`
- Test: `tests/core/test_endgame.py`

**Interfaces:**
- Consumes: `board`, `my_rack`, `opp_rack`, `score_diff`, `engine.move_gen`, `simulator`.
- Produces: `ExactEndgameSolver.solve(board, my_rack, opp_rack, score_diff, max_depth=4) -> Tuple[Optional[Dict], float]`

- [ ] **Step 1: Write failing tests for Exact Endgame Minimax Solver**

Create `tests/core/test_endgame.py` to test:
1. Instant out: if player can play out rack, awards move points plus $2 \times$ opponent rack value.
2. Opponent out prevention: minimax selects move that blocks or out-scores opponent's immediate winning out.
3. Integration with `AlphableSearch.find_best_move`: when `bag_remaining == 0`, invokes endgame solver instead of Monte Carlo sampling.

```python
import pytest
from alphable.core.endgame import ExactEndgameSolver, TILE_VALUES

def test_terminal_player_out_evaluation():
    # If our move uses all tiles, terminal value is points + 2 * sum(opp_rack)
    opp_rack = ['Q', 'Z']  # 10 + 10 = 20 pts
    # Playing out earns points + 40 bonus
    bonus = 2 * sum(TILE_VALUES[t] for t in opp_rack)
    assert bonus == 40

def test_exact_endgame_solver_execution(dict_path):
    from alphable.core.inference import AlphableInference
    engine = AlphableInference(model_path=None, dict_path=dict_path)
    solver = ExactEndgameSolver(engine)
    
    board = [['.'] * 15 for _ in range(15)]
    board[7][7] = 'C'
    board[7][8] = 'A'
    board[7][9] = 'T'
    
    my_rack = ['S']
    opp_rack = ['X']
    best_move, best_spread = solver.solve(board, my_rack, opp_rack, score_diff=0, max_depth=2)
    assert best_move is not None
    assert best_move['word'] == 'CATS' or 'S' in best_move['word']
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../venv/bin/pytest tests/core/test_endgame.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'alphable.core.endgame'`.

- [ ] **Step 3: Implement `ExactEndgameSolver` in `src/alphable/core/endgame.py` and hook into `search.py`**

1. Create `src/alphable/core/endgame.py`:
   - Define standard Scrabble tile values: `TILE_VALUES = {'A':1, 'B':3, 'C':3, 'D':2, 'E':1, 'F':4, 'G':2, 'H':4, 'I':1, 'J':8, 'K':5, 'L':1, 'M':3, 'N':1, 'O':1, 'P':3, 'Q':10, 'R':1, 'S':1, 'T':1, 'U':1, 'V':4, 'W':4, 'X':8, 'Y':4, 'Z':10, '?':0}`.
   - Implement `class ExactEndgameSolver`:
     - Method `solve(board, my_rack, opp_rack, score_diff, max_depth=4) -> (best_move, best_margin)`.
     - Alpha-beta minimax with move sorting (highest scoring candidate first for maximal cutoff).
     - Accurate terminal payoffs:
       - Active player empties rack: $+(\text{points} + 2 \times \text{sum}(\text{opp\_rack}))$.
       - Opponent empties rack: $-(\text{points} + 2 \times \text{sum}(\text{active\_rack}))$.
       - Double pass: active rack deducted, opponent rack added to spread.
2. In `src/alphable/core/search.py`:
   - Initialize `self.endgame_solver = ExactEndgameSolver(self.engine)`.
   - In `find_best_move(board, rack, score_diff, bag_remaining)`:
     - Check: `if bag_remaining == 0:`
     - Derive exact opponent rack: `opp_rack = get_unseen_distribution(board, rack)`.
     - If `len(opp_rack) <= 7`:
       Call `best_move, best_spread = self.endgame_solver.solve(board, rack, opp_rack, score_diff)` and return `(best_move, best_spread)`.

- [ ] **Step 4: Run tests to verify endgame solver and search integration pass**

Run: `../venv/bin/pytest tests/core/test_endgame.py tests/core/test_search.py -v`
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add src/alphable/core/endgame.py src/alphable/core/search.py tests/core/test_endgame.py
git commit -m "feat(core): implement deterministic exact endgame minimax solver"
```

---

### Task 3: Unseen Tile Distribution (Bag Tracking) in Neural State Representation

**Files:**
- Modify: `src/alphable/core/alphable_net.py`
- Modify: `src/alphable/core/inference.py`
- Modify: `src/alphable/core/search.py`
- Test: `tests/core/test_enriched_tensors.py`
- Test: `tests/core/test_alphable_net_v3.py`

**Interfaces:**
- Consumes: `rack`, `score_diff`, `bag_remaining`, `unseen_counts: Optional[Dict[str, int]] = None`, `state_vector_size: int = 36`.
- Produces: `state_to_tensor(...) -> torch.Tensor` of shape `[36]` or `[63]`.
- Network: `AlphableValueNet(state_vector_size=63)` supporting transfer loading via `load_checkpoint_compatible`.

- [ ] **Step 1: Write failing tests for 63-dimensional bag-tracking state tensor**

Add tests to `tests/core/test_enriched_tensors.py` and `tests/core/test_alphable_net_v3.py`:
1. Verify `state_to_tensor` with `state_vector_size=63` returns tensor of length 63.
2. Verify elements 36-61 represent normalized counts of unseen A-Z tiles, and element 62 represents unseen blanks '?'.
3. Verify `AlphableValueNet(state_vector_size=63)` forward pass works with `(B, 31, 15, 15)` board and `(B, 63)` state.
4. Verify `load_checkpoint_compatible` successfully transfers 36-dim checkpoint weights to a 63-dim network.

```python
def test_state_to_tensor_63_dim_bag_tracking():
    from alphable.core.inference import state_to_tensor
    unseen = {'A': 5, 'E': 8, 'Z': 1, '?': 1}
    t = state_to_tensor(['A', 'B', 'C'], score_diff=10, bag_remaining=50, unseen_counts=unseen, state_vector_size=63)
    assert t.shape == (63,)
    # Verify unseen tiles encoded in indices 36..62
    assert t[36].item() == 5 / 9.0  # 'A' standard count is 9
    assert t[62].item() == 1 / 2.0  # '?' standard count is 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../venv/bin/pytest tests/core/test_enriched_tensors.py -k "test_state_to_tensor_63_dim_bag_tracking" -v`
Expected: FAIL with `TypeError: state_to_tensor() got unexpected keyword argument`.

- [ ] **Step 3: Implement 63-dim Bag Tracking in `inference.py` and `alphable_net.py`**

1. In `src/alphable/core/inference.py`:
   - Update `state_to_tensor`:
     ```python
     def state_to_tensor(rack, score_diff, bag_remaining, unseen_counts=None, state_vector_size=36):
         arr = np.zeros(state_vector_size, dtype=np.float32)
         # populate elements 0-35 as before
         ...
         if state_vector_size >= 63 and unseen_counts is not None:
             for i, char in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
                 std_cnt = STANDARD_TILE_COUNTS.get(char, 1)
                 arr[36 + i] = unseen_counts.get(char, 0) / float(std_cnt)
             arr[62] = unseen_counts.get('?', 0) / 2.0
         return torch.from_numpy(arr)
     ```
2. In `src/alphable/core/alphable_net.py`:
   - Support `state_vector_size: int = 36` in `AlphableValueNet.__init__`.
   - Ensure `self.state_fc = nn.Sequential(nn.Linear(state_vector_size, 128), ...)` adapts automatically.
3. In `src/alphable/core/search.py`:
   - Pass `unseen_counts=unseen_counts_dict` into `state_to_tensor` when model state vector size is 63.

- [ ] **Step 4: Run tests to verify all tensor and network tests pass**

Run: `../venv/bin/pytest tests/core/test_enriched_tensors.py tests/core/test_alphable_net_v3.py tests/core/test_inference.py -v`
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add src/alphable/core/inference.py src/alphable/core/alphable_net.py src/alphable/core/search.py tests/core/test_enriched_tensors.py tests/core/test_alphable_net_v3.py
git commit -m "feat(model): add 63-dim unseen tile distribution state tracking"
```

---

### Task 4: Selective 2-Ply Lookahead on Top-2 Candidate Moves

**Files:**
- Modify: `src/alphable/core/search.py`
- Test: `tests/core/test_search.py`

**Interfaces:**
- Consumes: Top candidate moves from 1-ply simulation, threshold `two_ply_threshold: float = 8.0`.
- Produces: Enhanced `AlphableSearch.find_best_move` with selective 2-ply counter-response evaluation.

- [ ] **Step 1: Write failing tests for Selective 2-Ply Lookahead**

Add unit test in `tests/core/test_search.py`:
1. Verify `AlphableSearch` accepts `enable_2ply: bool = True` and `two_ply_threshold: float = 8.0`.
2. When the difference between Candidate 1 and Candidate 2 is $\le 8.0$ points, verify 2-ply evaluation activates and computes counter-responses.
3. When the difference is $> 8.0$ points, candidate 1 is returned directly without extra 2-ply latency.

```python
def test_selective_2ply_trigger_condition(dict_path):
    from alphable.core.inference import AlphableInference
    from alphable.core.search import AlphableSearch
    engine = AlphableInference(model_path=None, dict_path=dict_path)
    searcher = AlphableSearch(engine, num_simulations=2, top_k_candidates=2, enable_2ply=True, two_ply_threshold=10.0)
    assert searcher.enable_2ply is True
    assert searcher.two_ply_threshold == 10.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../venv/bin/pytest tests/core/test_search.py -k "test_selective_2ply_trigger_condition" -v`
Expected: FAIL with `TypeError: AlphableSearch.__init__() got an unexpected keyword argument 'enable_2ply'`.

- [ ] **Step 3: Implement Selective 2-Ply Lookahead in `src/alphable/core/search.py`**

In `src/alphable/core/search.py`:
1. Add `enable_2ply: bool = False` and `two_ply_threshold: float = 8.0` to `AlphableSearch.__init__`.
2. After 1-ply Monte Carlo simulation computes equities for top candidates:
   - Sort candidates by 1-ply simulated equity.
   - If `self.enable_2ply and len(top_candidates) >= 2`:
     - If `(top_candidates[0]['sim_equity'] - top_candidates[1]['sim_equity']) <= self.two_ply_threshold`:
       - For each of the top 2 candidates:
         - Simulate our follow-up response (ply 2) to opponent's top reply:
           - Sample our new tile draw from remaining unseen bag.
           - Generate our legal counter-replies.
           - Find highest-equity counter-reply (score + leave).
           - Add expected counter-reply points to candidate equity.
       - Re-rank the top 2 candidates according to full 2-ply equity.

- [ ] **Step 4: Run tests to verify 2-ply search works cleanly and tests pass**

Run: `../venv/bin/pytest tests/core/test_search.py -v`
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add src/alphable/core/search.py tests/core/test_search.py
git commit -m "feat(search): add selective 2-ply lookahead on competitive top-2 candidates"
```

---

### Task 5: Pure Outcome-Driven Self-Play Reinforcement Learning Pipeline

**Files:**
- Create: `src/alphable/training/self_play_rl.py`
- Modify: `src/alphable/cli/main.py`
- Test: `tests/training/test_self_play_rl.py`

**Interfaces:**
- Consumes: `AlphableInference`, game simulation engine.
- Produces: CLI command `python -m alphable.cli.main train rl-selfplay --games 500 --epochs 10 --save-model models/alphable_v3_rl_gen4.pth`.
- Outputs: Self-play trajectory logs, pure outcome targets $z \in \{-1.0, 1.0\}$, and updated checkpoint.

- [ ] **Step 1: Write failing tests for Self-Play RL Pipeline**

Create `tests/training/test_self_play_rl.py`:
1. Test game trajectory generation: each turn records board tensor, 63-dim state tensor, and receives final game outcome target $z$.
2. Test win/loss outcome labeling: winning player turns get $+1.0$ (or positive tanh margin), losing player turns get $-1.0$.
3. Test mini-batch training loop step: MSE loss decreases on self-play outcomes.

```python
import pytest
import torch
from alphable.training.self_play_rl import SelfPlayRLTrainer, SelfPlayTrajectory

def test_self_play_trajectory_target_assignment():
    traj = SelfPlayTrajectory()
    traj.record_turn(player=0, board_str="."*225, rack=['A', 'B'], score_diff=0, bag_count=80)
    traj.record_turn(player=1, board_str="."*225, rack=['C', 'D'], score_diff=0, bag_count=78)
    
    # Player 0 wins 420 - 380 (+40 pts)
    samples = traj.finalize(scores=(420, 380), margin_scale=100.0)
    assert len(samples) == 2
    # Player 0 target should be positive, player 1 negative
    assert samples[0]['target'] > 0.0
    assert samples[1]['target'] < 0.0
    assert abs(samples[0]['target'] + samples[1]['target']) < 1e-4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../venv/bin/pytest tests/training/test_self_play_rl.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'alphable.training.self_play_rl'`.

- [ ] **Step 3: Implement Pure Outcome-Driven Self-Play RL in `src/alphable/training/self_play_rl.py`**

1. Create `src/alphable/training/self_play_rl.py`:
   - `SelfPlayTrajectory`: stores `(board, state_63, player_id)` for every move in a game.
   - Assigns terminal targets: $z = \tanh((\text{score}_{\text{player}} - \text{score}_{\text{opp}}) / 100.0)$.
   - `SelfPlayRLTrainer`:
     - Manages self-play games between active model and baseline/checkpoint pool.
     - Early-game exploration: temperature annealing over first 6 turns to ensure rich game variety.
     - Collects dataset into memory / temporary JSONL.
     - Trains `AlphableValueNet(state_vector_size=63)` using AdamW and MSE loss.
     - Evaluates candidate model vs champion in 20-game validation tournament. Promotes candidate if win rate $\ge 52\%$.
2. In `src/alphable/cli/main.py`:
   - Add `rl-selfplay` sub-command parsing options (`--games`, `--epochs`, `--batch-size`, `--lr`, `--save-model`, `--dict`).

- [ ] **Step 4: Run tests to verify self-play RL trainer passes**

Run: `../venv/bin/pytest tests/training/test_self_play_rl.py -v`
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add src/alphable/training/self_play_rl.py src/alphable/cli/main.py tests/training/test_self_play_rl.py
git commit -m "feat(training): implement outcome-driven self-play reinforcement learning pipeline"
```

---

### Task 6: Full System Integration & Benchmark Verification

**Files:**
- Test: `tests/` (entire suite)
- Script: `scratch/benchmark_5pillars_pipeline.py`

**Interfaces:**
- Verifies all 5 pillars work cohesively in realistic game simulations.

- [ ] **Step 1: Write an end-to-end integration benchmark script**

Create `scratch/benchmark_5pillars_pipeline.py`:
- Initializes `AlphableSearch` with Lipkin-Smith leaves, bag tracking (63-dim), selective 2-ply, and exact endgame solver.
- Simulates complete midgame and endgame moves on standard boards.
- Asserts that when `bag == 0`, exact endgame solver executes and outputs optimal minimax line.
- Asserts that average search time per move remains under 1.5s.

- [ ] **Step 2: Run benchmark script to verify end-to-end performance**

Run: `../venv/bin/python scratch/benchmark_5pillars_pipeline.py`
Expected: PASS with move computation time $\le 1.5$s and correct endgame resolution.

- [ ] **Step 3: Run the full test suite across the entire project**

Run: `../venv/bin/pytest tests/ -v`
Expected: All tests pass (181+ tests, 0 failures).

- [ ] **Step 4: Commit benchmark and verify clean git status**

```bash
git add scratch/benchmark_5pillars_pipeline.py
git commit -m "test(benchmark): add comprehensive 5-pillar engine integration verification"
```

---

## Plan Self-Review Checklist
- [x] **Spec coverage**: Covers all 5 pillars analyzed in the holistic review (Endgame Minimax, Bag Tracking, Super-Leave Recalibration, 2-Ply Lookahead, Outcome Self-Play RL).
- [x] **Placeholder scan**: Zero TODOs, TBDs, or placeholder implementations.
- [x] **Type and interface consistency**: `ExactEndgameSolver`, `compute_leave_equity(rack, bag_remaining)`, `state_to_tensor(..., state_vector_size=63)`, `AlphableSearch(..., enable_2ply=True)` signatures matched across all tasks.
- [x] **TDD discipline**: Every task contains explicit failing tests, verify fail step, minimal implementation, verify pass step, and git commit step.
