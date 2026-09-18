# Architectural Pivot: Explicit Equity Formulation & Enriched Representations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the architectural pivot for Alphable V3: enrich tensor representations (dynamic open premium square channels, comprehensive rack leave features), rebalance the value network architecture (remove noisy dropout, balance spatial vs. scalar embeddings), and formulate explicit Move Equity ($\text{Score}(m) + \alpha \cdot V(s')$) across evaluation and search.

**Architecture:**
- **Representation (`inference.py`)**:
  - `board_to_tensor`: dynamic premium square channels (mark premium multiplier only on OPEN squares where `board[r][c] == '.'`, zeroing out consumed squares).
  - `state_to_tensor`: expand state vector to 36 features including leave size, vowel count, consonant count, vowel-consonant balance, blank tile flag, 'S' tile flag, and duplicate letter penalty.
- **Neural Network (`alphable_net.py`)**:
  - Balanced projection: board conv features projected to 256, state vector projected to 128 (combined 384).
  - Remove `Dropout(0.3)` from the value head to ensure stable, low-variance value calibration.
- **Move Selection & Search (`self_play.py`, `search.py`, `evaluate_vs_baseline.py`)**:
  - Formulate move ranking as $\text{Equity}(m) = \text{Score}(m) + \alpha \cdot V(s')$ where $\alpha = 25.0$ points.
  - Anchor both 0-ply argmax and 1-ply lookahead candidate selection to true move equity.

**Tech Stack:** PyTorch 2.14.0, NumPy, pytest.

**Spec:** Architectural design from audit findings and expert Scrabble AI equity formulation (Maven/Quackle framework).

## Global Constraints

- Backwards compatibility: `state_vector_size` and `board_channels` remain configurable arguments in `AlphableValueNet` with defaults matching the enhanced tensor sizes.
- `dataset.py` must compute the expanded state features on-the-fly directly from `sample['rack']`, `sample['score_diff']`, and `sample['bag']` without requiring dataset re-formatting.
- All test suites must continue passing with zero regressions.

---

### Task 1: Enriched Tensor Representations in `inference.py` and `dataset.py`

**Files:**
- Modify: `Alphable_V3/src/alphable/core/inference.py:7-73`
- Modify: `Alphable_V3/src/alphable/data/dataset.py:37-47`
- Create: `Alphable_V3/tests/core/test_enriched_tensors.py`

**Interfaces:**
- Consumes: `board` (15x15 list of lists), `rack` (list of chars), `score_diff` (int), `bag_remaining` (int).
- Produces:
  - `board_to_tensor(board)`: `[31, 15, 15]` tensor where channels 27-30 (DL, TL, DW, TW) are active (1.0) ONLY on open squares (`board[r][c] == '.'`).
  - `state_to_tensor(rack, score_diff, bag_remaining)`: `[36]` tensor with rack counts (27), score diff (1), bag (1), leave size (1), vowel count (1), consonant count (1), has_blank (1), has_S (1), duplicate letter penalty (1), empty leave flag (1).

- [ ] **Step 1: Write unit tests for enriched tensors**

```python
# Alphable_V3/tests/core/test_enriched_tensors.py
import torch
import pytest
from alphable.core import simulator, inference

def test_open_vs_consumed_premium_squares():
    board = simulator.create_empty_board()
    # Center square (7,7) is DW (channel 29)
    t1 = inference.board_to_tensor(board)
    assert t1[29, 7, 7] == 1.0

    # Place a tile on (7,7)
    board[7][7] = 'A'
    t2 = inference.board_to_tensor(board)
    # Letter A is on channel 0
    assert t2[0, 7, 7] == 1.0
    # Consumed premium square must now be 0.0
    assert t2[29, 7, 7] == 0.0

def test_expanded_state_vector_features():
    # Rack with 'S', '?', vowels, consonants, and duplicate 'E's
    rack = ['S', '?', 'E', 'E', 'R', 'T']
    score_diff = 25
    bag = 40
    vec = inference.state_to_tensor(rack, score_diff, bag)
    assert vec.shape == (36,)
    # Rack length: 6 / 7.0
    assert abs(vec[29].item() - 6.0 / 7.0) < 1e-4
    # Has blank (index 32): 1.0
    assert vec[32].item() == 1.0
    # Has S (index 33): 1.0
    assert vec[33].item() == 1.0
    # Duplicate penalty (one extra 'E'): 1.0 / 7.0
    assert abs(vec[34].item() - 1.0 / 7.0) < 1e-4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/targed/Documents/Git/Alphable/venv/bin/pytest tests/core/test_enriched_tensors.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement dynamic premium squares and expanded state features**

In `inference.py`:
1. In `board_to_tensor(board)`: set `arr[prem_idx, r, c] = 1.0` only when `board[r][c] == '.'`.
2. In `state_to_tensor(rack, score_diff, bag_remaining)`: expand array to length 36 and compute the leave equity metrics.
In `dataset.py`:
Ensure `state_to_tensor` is called with the leave rack, score diff, and bag remaining to produce the identical 36-dim tensor.

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/targed/Documents/Git/Alphable/venv/bin/pytest tests/core/test_enriched_tensors.py -v`
Expected: PASS.

---

### Task 2: Rebalance Neural Network Architecture in `alphable_net.py`

**Files:**
- Modify: `Alphable_V3/src/alphable/core/alphable_net.py:21-99`
- Create: `Alphable_V3/tests/core/test_alphable_net_v3.py`

**Interfaces:**
- Consumes: Board tensor `[B, 31, 15, 15]` and State tensor `[B, 36]`.
- Produces: Output tensor `[B, 1]` in `[-1.0, 1.0]`.
- Guarantees:
  - No dropout in value head.
  - Balanced projections: `board_proj` (256 units) + `state_proj` (128 units) $\to$ `combined` (384 units).

- [ ] **Step 1: Write test for new net architecture and forward pass**

```python
# Alphable_V3/tests/core/test_alphable_net_v3.py
import torch
from alphable.core.alphable_net import AlphableValueNet

def test_net_forward_and_no_dropout():
    net = AlphableValueNet(board_channels=31, state_vector_size=36)
    net.train() # In train mode, check no dropout layer exists
    for module in net.modules():
        assert not isinstance(module, torch.nn.Dropout), "Dropout should be removed from value net"

    b = torch.randn(4, 31, 15, 15)
    s = torch.randn(4, 36)
    out = net(b, s)
    assert out.shape == (4, 1)
    assert (out >= -1.0).all() and (out <= 1.0).all()
```

- [ ] **Step 2: Run test to verify failure**

Run: `/home/targed/Documents/Git/Alphable/venv/bin/pytest tests/core/test_alphable_net_v3.py -v`
Expected: FAIL (due to Dropout assertion and state_vector_size).

- [ ] **Step 3: Update `AlphableValueNet` in `alphable_net.py`**

In `alphable_net.py`:
- Update `state_vector_size=36` default.
- In `self.conv_reduce`: reduce channels to 16, flatten to 3600, project with `board_fc = nn.Sequential(nn.Linear(3600, 256), nn.ReLU())`.
- In `self.state_fc`: `Linear(state_vector_size, 128) -> ReLU -> Linear(128, 128) -> ReLU`.
- In `self.fc_final`: `Linear(384, 256) -> ReLU -> Linear(256, 64) -> ReLU -> Linear(64, 1) -> Tanh()`. Remove all `Dropout`.

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/targed/Documents/Git/Alphable/venv/bin/pytest tests/core/test_alphable_net_v3.py -v`
Expected: PASS.

---

### Task 3: Implement Explicit Move Equity ($\text{Score} + \alpha \cdot V(s')$) in Search & Evaluation

**Files:**
- Modify: `Alphable_V3/src/alphable/training/self_play.py:49-88,105-126`
- Modify: `Alphable_V3/src/alphable/core/search.py:127-176`
- Modify: `Alphable_V3/src/alphable/eval/evaluate_vs_baseline.py:105-140`
- Create: `Alphable_V3/tests/core/test_move_equity.py`

**Interfaces:**
- Consumes: Move points $S(m)$ and After-state value $V(s')$.
- Produces: Composite Move Equity:
  $$\text{equity} = S(m) + \alpha \cdot V(s') \quad (\alpha = 25.0)$$
  Rank moves by `equity` across `evaluate_moves()`, `choose_move_with_temperature()`, `find_best_move()`, and `evaluate_vs_baseline.py`.

- [ ] **Step 1: Write test for composite move equity**

```python
# Alphable_V3/tests/core/test_move_equity.py
import pytest
from alphable.training.self_play import evaluate_moves
from alphable.core.inference import AlphableInference
from alphable.core import simulator

def test_evaluate_moves_calculates_equity():
    engine = AlphableInference(device='cpu')
    board = simulator.create_empty_board()
    rack = ['C', 'A', 'B', 'I', 'N', 'E', 'T']
    evals = evaluate_moves(engine, board, rack, score_diff=0, bag_remaining=86)
    assert len(evals) > 0
    # Each evaluation must include points, value, and equity
    top = evals[0]
    assert 'points' in top
    assert 'value' in top
    assert 'equity' in top
    # The highest equity move should be ranked first
    for i in range(len(evals) - 1):
        assert evals[i]['equity'] >= evals[i+1]['equity']
```

- [ ] **Step 2: Run test to verify failure**

Run: `/home/targed/Documents/Git/Alphable/venv/bin/pytest tests/core/test_move_equity.py -v`
Expected: FAIL (missing 'equity' key in evals).

- [ ] **Step 3: Update move evaluation with Equity formulation**

In `self_play.py` and `search.py`:
- In `evaluate_moves`:
  Compute `equity = points + 25.0 * value`.
  Sort candidate moves by `equity` descending.
- In `choose_move_with_temperature`:
  Compute logits over top-k `equity` values (scaled by temperature).
- In `search.py`:
  Sort 0-ply candidates by `equity` descending.

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/targed/Documents/Git/Alphable/venv/bin/pytest tests/core/test_move_equity.py -v`
Expected: PASS.

---

### Task 4: Full Verification and Checkpoint Benchmark

**Files:**
- Run full unit test suite: `pytest tests/ -v`
- Run a 10-game baseline evaluation match: `alphable eval baseline --opponent random --games 6` and `alphable eval baseline --opponent greedy --games 6`

- [ ] **Step 1: Run full pytest suite**
- [ ] **Step 2: Run baseline evaluation against RandomBot**
- [ ] **Step 3: Run baseline evaluation against GreedyBot**
- [ ] **Step 4: Verify test suite and update documentation**
