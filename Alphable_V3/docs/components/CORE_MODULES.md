# Alphable V3: Core Modules Reference

This document provides a comprehensive, file-by-file reference for all core algorithmic, data structure, evaluation, and search modules located in [`src/alphable/core/`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core).

---

## Architecture Overview

```
src/alphable/core/
├── structure.pyx / structure.py   # High-speed Cython/C++ GADDAG move generator
├── simulator.py                   # Official Scrabble board mutation & exact scoring engine
├── inference.py                   # Feature extraction: 31-channel board & 63-dim state tensors
├── alphable_net.py                # Dual-stream ResNet + MLP After-State Value Network
├── leave_eval.py                  # Super-Leaves stem evaluation, duplicate blanks, vowel/consonant balance
├── defense.py                     # Hot-spot defense & open lane vulnerability analysis
├── endgame.py                     # Deterministic alpha-beta minimax exact endgame solver (bag=0)
└── search.py                      # 1-ply Monte Carlo lookahead with CRN & selective 2-ply
```

---

## 1. `structure.pyx` & `structure.py` ([`src/alphable/core/structure.pyx`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/structure.pyx))

The core move generation engine for Alphable. Implements Steven Gordon's GADDAG data structure in Cython and C++ for bidirectional letter placement.

### Key Classes & Methods

#### `Gaddag`
- **Purpose:** In-memory directed acyclic word graph containing the complete tournament lexicon (e.g. CSW24 with 279,496 words, or NWL2023 with 192,111 words).
- **Node Structure:** Compact trie where words are indexed bi-directionally using the delimiter character `>`:
  - For example, `CARE` is stored as:
    - `C > A R E`
    - `A C > R E`
    - `R A C > E`
    - `E R A C >`
- **Method `load(dict_path: str)`:** Reads dictionary text file, builds prefix and suffix arcs, and caches the structure for instantaneous lookup.

#### `MoveGenerator`
- **Method `generate(board: list[list[str]], rack: list[str]) -> list[dict]`:**
  - Identifies all **anchor squares** (empty squares adjacent to existing tiles, or the center star `(7, 7)` on an empty board).
  - Precomputes **cross-checks**: for every empty square, calculates which letters can legally be placed without invalidating perpendicular words formed with adjacent tiles.
  - Traverses the GADDAG bidirectionally starting at each anchor, pruning illegal branches immediately.
  - **Performance:** Generates all 20–150 legal Scrabble plays in under **3 to 5 milliseconds** on a single CPU core.

### Critical Fix: Blank Tile Cross-Checks (`.upper()`)
- In Scrabble, blank tiles placed on the board are represented by **lowercase letters** (e.g., `'e'` indicating a blank representing an E).
- **The Bug:** GADDAG cross-check calculation functions (`_compute_cross_checks`, `_fast_word_check`, `_go_left`, `_go_right`) previously checked raw board characters against uppercase trie nodes. Lowercase characters did not match, resulting in GADDAG failing to generate valid hooks onto or through played blanks.
- **The Solution:** Added `.upper()` normalization on all board lookups across `structure.pyx` and `structure.py`. Recompiled to native shared library `structure.cpython-311-x86_64-linux-gnu.so`.
- **Result:** Move generation now flawlessly discovers high-scoring plays hooking to or extending through board blanks (e.g., finding `INERTIA` for +69 pts hooking an existing blank `i`).

---

## 2. `simulator.py` ([`src/alphable/core/simulator.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/simulator.py))

Official Scrabble board state mutation, tile accounting, and scoring simulator.

### Constants
- `LETTER_VALUES`: Official international Scrabble letter values:
  - 0 pts: `?` (or lowercase blanks `a`–`z`)
  - 1 pt: `A, E, I, L, N, O, R, S, T, U`
  - 2 pts: `D, G`
  - 3 pts: `B, C, M, P`
  - 4 pts: `F, H, V, W, Y`
  - 5 pts: `K`
  - 8 pts: `J, X`
  - 10 pts: `Q, Z`
- `BONUS_TILES`: $15 \times 15$ grid mapping coordinates to premium types:
  - `'..'`: Regular square
  - `'DL'`: Double Letter ($2\times$)
  - `'TL'`: Triple Letter ($3\times$)
  - `'DW'`: Double Word ($2\times$, includes center star `(7, 7)`)
  - `'TW'`: Triple Word ($3\times$)

### Key Functions

#### `create_empty_board() -> list[list[str]]`
Returns an empty $15 \times 15$ grid filled with `'.'`.

#### `simulate_move(board: list[list[str]], move: dict, rack: list[str]) -> tuple[list[list[str]], int, list[str]]`
Applies a candidate move to the board and calculates exact points earned and remaining rack leave.
- **Parameters:**
  - `board`: Current $15 \times 15$ board.
  - `move`: Dict containing:
    - `'row'`: Starting row $[0, 14]$
    - `'col'`: Starting col $[0, 14]$
    - `'dir'`: `'Across'` or `'Down'`
    - `'word'`: Word formed. Blanks designated by lowercase characters (e.g. `'tOuCH'`).
  - `rack`: Current rack tiles (e.g. `['T', '?', 'U', 'C', 'H', 'A', 'E']`).
- **Scoring Rules Enforced:**
  1. Distinguishes newly placed tiles from pre-existing tiles.
  2. Applies active letter multipliers (`DL`, `TL`) only to newly placed tiles.
  3. Applies active word multipliers (`DW`, `TW`) multiplicatively (e.g. two `TW` squares on one move $= 9\times$ word score).
  4. Perpendicular cross-words: Scans each newly placed tile for perpendicular adjacent letters. If a cross-word is created, calculates its letter multipliers and word multipliers independently.
  5. Bingo Bonus: If exactly 7 tiles from the rack are placed, awards $+50$ bonus points.
- **Returns:** `(new_board, total_points, new_rack)`

---

## 3. `inference.py` ([`src/alphable/core/inference.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/inference.py))

Handles feature encoding, tensor transformations, and the high-level inference interface.

### Spatial Tensor: `board_to_tensor(board)`
Converts a $15 \times 15$ board into a PyTorch `FloatTensor` of shape `[31, 15, 15]`:
- **Channels 0–25:** One-hot spatial planes for letters `'A'` through `'Z'`.
- **Channel 26:** Binary plane indicating empty squares (`board[r][c] == '.'`).
- **Channels 27–30:** Binary planes indicating **open** premium squares (`DL`, `TL`, `DW`, `TW`). Once a premium square is covered by a tile, its plane switches from $1.0$ to $0.0$.

### State Tensor: `state_to_tensor(rack, score_diff, bag_remaining, unseen_dist)`
Encodes non-spatial scalar game state into a PyTorch `FloatTensor` of shape `[63]`:
- **Indices 0–25:** Hand rack letter counts for `'A'` through `'Z'`.
- **Index 26:** Hand rack blank count (`?`).
- **Index 27:** Normalized score differential: $\text{score\_diff} / 500.0$.
- **Index 28:** Normalized remaining bag tiles: $\text{bag\_remaining} / 100.0$.
- **Indices 29–35:** Rack leave structural heuristics:
  - 29: Rack tile count (normalized by 7.0).
  - 30: Vowel count.
  - 31: Consonant count.
  - 32: Blank indicator (1.0 if blank present, 0.0 otherwise).
  - 33: `'S'` indicator (1.0 if S present, 0.0 otherwise).
  - 34: Duplicate letter penalty score.
  - 35: Bingo potential flag (high-synergy stem indicator).
- **Indices 36–62 (Pillar 4 Upgrade):** Unseen tile bag tracking ratios for each letter `'A'` through `'Z'` plus `'?'`. Computed by subtracting the current board tiles and current rack from the standard 100-tile Scrabble set and normalizing by total unseen count.

### Class: `AlphableInference`
- **Constructor:** `AlphableInference(model_path=None, device='cpu', dict_path='resources/CSW24.txt')`
  - Loads GADDAG dictionary and initializes `MoveGenerator`.
  - Instantiates `AlphableValueNet` on the target device (`cuda` or `cpu`).
  - Warm-starts weights via `load_checkpoint_compatible`.
- **Method `find_best_move(current_board, rack, current_score_diff, bag_remaining) -> tuple[dict, float]`:**
  - Evaluates all legal moves using 0-ply heuristic or value network forward passes.
  - Returns `(best_move, best_value)` maximizing $\text{Points} + 25.0 \times V(s')$.

---

## 4. `alphable_net.py` ([`src/alphable/core/alphable_net.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/alphable_net.py))

PyTorch deep learning implementation of the dual-stream After-State Value Network.

### Components
- **`ConvBlock`:** `Conv2d` $\to$ `BatchNorm2d` $\to$ `LeakyReLU(negative_slope=0.01)`.
- **`ResNetBlock`:** Skip-connection block:
  $$y = \text{LeakyReLU}(x + \text{BN}(\text{Conv}(\text{LeakyReLU}(\text{BN}(\text{Conv}(x))))))$$
- **`AlphableValueNet`:**
  - **Spatial Stream:** 5 residual blocks (64 filters each), followed by `AdaptiveAvgPool2d((3, 3))` and projection to 384 dimensions.
  - **Scalar Stream:** 2-layer MLP projecting the 63-dimensional state vector (or 36-dim legacy) to 128 dimensions.
  - **Fusion Head:** Concatenates spatial (384) + scalar (128) = 512 dimensions. Passes through 3 dense layers $(512 \to 256 \to 64 \to 1)$ with `Tanh` activation, producing output $V(s') \in [-1.0, +1.0]$.
- **`load_checkpoint_compatible(model, checkpoint_path, device)`:**
  - Handles architectural differences seamlessly (e.g. loading legacy 36-dim checkpoints into 63-dim networks by slicing/zero-padding matching channels).
  - Returns `(loaded_keys, total_keys)`.

---

## 5. `leave_eval.py` ([`src/alphable/core/leave_eval.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/leave_eval.py))

Empirical Rack Leave Valuation and Synergy Modeling based on championship Scrabble equity tables (Lipkin-Smith / Super-Leaves).

### Constants & Tables
- **`BASE_TILE_EQUITY`:** Empirical marginal values in points:
  - `?`: $+26.5$ (the highest equity tile in Scrabble)
  - `S`: $+8.2$ (pluralizer and hook master)
  - `Z`: $+2.5$, `X`: $+2.5$, `R`: $+1.8$, `E`: $+1.6$, `T`: $+1.6$, `N`: $+1.4$
  - Liabilities: `O`: $-1.5$, `U`: $-4.0$, `V`: $-5.5$, `Q`: $-7.5$
- **`STEM_HIERARCHY`:** Hierarchical, non-overlapping bingo stem bonuses:
  - 5-letter stems ($+4.5$ pts): `RETIN`, `TISAN`, `STARE`, `SATIN`
  - 3-letter stems ($+2.5$ pts): `EST`, `ERS`, `RET`, `SAT`, `INE`, `TIN`, `ARE`, `ATE`, `ION`
  - 2-letter connectors ($+1.5$ to $+2.0$ pts): `ES`, `ST`, `ER`, `IN`, `RS`, `ED`
  - Tactical pairs: `?S` ($+5.0$ pts), `QU` ($+6.5$ pts, neutralizes Q liability)
- **`DUPLICATE_PENALTIES`:** Penalties for duplicate letters (`S`: $-6.2$, `I`: $-4.0$, `U`: $-4.5$, `V`: $-7.0$).

### Key Function: `compute_leave_equity(rack, bag_remaining=100) -> float`
1. **Endgame Deduction (`bag_remaining == 0`):**
   - Returns the negative sum of unplayed tile face values ($-\sum \text{face\_value}$). Dead tiles on hand are subtracted from final score.
2. **Duplicate Blank Diminishing Returns Formula:**
   - A single blank is worth $+26.5$ pts.
   - Holding a second blank adds only $+6.0$ pts (total `??` $= +32.5$, not $+53.0$):
     $$\text{equity} \mathrel{-}= 20.5 \times (\text{blank\_count} - 1)$$
   - Prevents the engine from hoarding two blanks over high-scoring 60+ pt bingos.
3. **Duplicate Tile Penalties:** Escalating penalty for redundant tiles:
   $$\text{penalty} = \text{base\_pen} \times (\text{count} - 1) \times 1.2^{(\text{count} - 2)}$$
4. **Vowel/Consonant Balance:** Penalizes extreme racks ($0$ vowels: $-6.0 - 1.5N$; $0$ consonants: $-7.0 - 2.0N$; vowel ratio $> 0.65$ or $< 0.25$).
5. **Stem Synergies:** Matches the longest non-overlapping stem in `STEM_HIERARCHY`.

---

## 6. `defense.py` ([`src/alphable/core/defense.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/defense.py))

Defensive Board Vulnerability and Hot-Spot Modeling. Analyzes open Triple Word Scores (TWS) and Double Word Scores (DWS) and computes defensive equity adjustments.

### Key Coordinates
- `TRIPLE_WORD_SQUARES`: 8 perimeter coordinates `(0,0), (0,7), (0,14), (7,0), (7,14), (14,0), (14,7), (14,14)`.
- `DOUBLE_WORD_SQUARES`: Diagonal perimeter coordinates `(1,1), (2,2), ... (13,13)` and center `(7,7)`.

### Key Function: `compute_board_defense_adjustment(old_board, new_board, move, score_diff=0) -> float`
- **Dynamic Game Situation Weighting:**
  - Ahead ($\text{diff} \ge +40$): $\text{weight} = 1.4$ (defense is paramount).
  - Trailing ($\text{diff} \le -40$): $\text{weight} = 0.6$ (opening the board is necessary for comeback bingos).
  - Close game: $\text{weight} = 1.0$.
- **Hot-Spot Seizure Bonus:**
  - Directly occupying an open TWS square: $+6.0 \times \text{weight}$ pts.
  - Directly occupying an open DWS square: $+2.0 \times \text{weight}$ pts.
- **Dangerous Open Lane Exposure Penalty:**
  - Scans horizontal and vertical lines of sight from every open TWS.
  - If a newly placed tile creates an anchor square at distance $1 \le d \le 3$ with clear line-of-sight:
    - Distance 1 (immediate hook): $-5.5 \times \text{weight}$ pts.
    - Distance 2: $-3.5 \times \text{weight}$ pts.
    - Distance 3: $-2.0 \times \text{weight}$ pts.

---

## 7. `endgame.py` ([`src/alphable/core/endgame.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/endgame.py))

Deterministic Exact Endgame Minimax Solver. When the tile bag is empty (`bag == 0`), Scrabble converts to a zero-sum, perfect-information game.

### Class: `ExactEndgameSolver`
- **Constructor:** `ExactEndgameSolver(inference_engine, branch_limit=5)`
- **Method `solve(board, my_rack, opp_rack, score_diff=0, max_depth=4) -> tuple[dict, float]`:**
  - **Adaptive Depth Limit:**
    - If either player has $>3$ tiles: solves at depth 2 (immediate play + opponent counterplay) in $< 0.15$s.
    - When both players have $\le 3$ tiles: executes full depth 4 alpha-beta branch-and-bound search, solving out completely in $< 0.001$s.
  - **Move Ordering & Pruning:**
    - Evaluates all legal plays. Moves that go out (empty rack) are prioritized first.
    - Non-out plays are pruned to top-$K$ highest-scoring moves (`branch_limit=5`).
  - **Terminal Valuation:**
    - Going out: $\text{points} + 2 \times \text{sum}(\text{opp\_unplayed\_tiles})$.
    - Passes / Game over: Evaluates final point spread differential.
  - **Returns:** `(best_move, guaranteed_spread_margin)`.

---

## 8. `search.py` ([`src/alphable/core/search.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/search.py))

Monte Carlo 1-ply lookahead search engine with Common Random Numbers (CRN), two-stage opponent pruning, and selective 2-ply counter-response.

### Algorithmic Pipeline

```
Candidate Generation (Top-K by 0-Ply Equity)
                     │
       Sample Opponent Racks (CRN)
  (Identical N Racks Across All Candidates)
                     │
       Two-Stage Opponent Reply Pruning
  Stage 1: Fast Heuristic (Points + Leave) -> Top 3
  Stage 2: Neural Net (Points + 25 * V_opp)
                     │
    Minimax Opponent Deduction (Softmax Expectation)
                     │
   Selective 2-Ply Trigger (if Top-2 Gap <= 8.0 pts)
                     │
                 Best Move
```

### Key Functions & Classes

#### `sample_opponent_racks(unseen_tiles: list[str], num_samples: int = 10, rack_size: int = 7) -> list[list[str]]`
Samples $N$ random opponent racks from the unseen tile pool. Under CRN, this function is called **once per turn**, and the exact same set of $N$ racks is evaluated against every candidate move.

#### `AlphableSearch`
- **Constructor:** `AlphableSearch(inference_engine, top_k=5, simulations=10, enable_2ply=True)`
- **Method `find_best_move(board, rack, score_diff, bag_remaining) -> tuple[dict, float]`:**
  1. **Endgame Check:** If `bag_remaining == 0`, immediately routes to `ExactEndgameSolver.solve()`.
  2. **Candidate Selection:** Ranks legal moves by 0-ply equity:
     $$\text{Equity}_{0} = \text{Points} + \text{Leave}(\text{rack}') + \text{Defense}(\text{move}) + 25.0 \times V(s')$$
     Selects the top $K$ candidates (default $K=5$).
  3. **Common Random Numbers (CRN) Evaluation:**
     - Draws $N$ opponent racks $\mathcal{R}_{\text{opp}}$.
     - For each candidate $m_i$ on simulated board $b_i$:
       - For each rack $r \in \mathcal{R}_{\text{opp}}$:
         - Generates legal opponent counter-moves.
         - **Stage 1 Pruning:** Filters opponent counter-moves to top 3 by immediate points + leave equity.
         - **Stage 2 Evaluation:** Evaluates top 3 via neural network: $\text{OppEquity} = \text{Points}_{\text{opp}} + 25.0 \times V(s'')$.
         - Softmax expectation over top opponent replies gives $\mathbb{E}[\text{OppReply} \mid r]$.
       - Average over $N$ simulations gives expected opponent counterplay $\overline{\text{OppEquity}}(m_i)$.
     - **1-Ply Simulated Equity:**
       $$\text{Equity}_{1}(m_i) = \text{Points}(m_i) + \text{Leave}(\text{rack}_i') - \overline{\text{OppEquity}}(m_i)$$
       *(Note: Redundant double defense penalty was eliminated; defensive counterplay is already simulated directly on $b_i$).*
  4. **Selective 2-Ply Trigger:**
     - If the equity gap between Candidate 1 and Candidate 2 is $\le 8.0$ points, triggers a 2-ply counter-response evaluation to determine our best follow-up bingo or rack development.
  5. **Returns:** `(best_move, best_equity)`.

---

## 9. `transformer_ranker.py` ([`src/alphable/models/transformer_ranker.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/models/transformer_ranker.py))

Autoregressive Language Model Candidate Ranker for Alphable V3. Leverages pre-trained `HuggingFaceTB/SmolLM2-135M-Instruct` to re-rank top candidate moves using attention-based logit scoring.

### Key Classes & Methods

#### `SmolLM2CandidateRanker`
- **Initialization:**
  ```python
  ranker = SmolLM2CandidateRanker(
      model_path="HuggingFaceTB/SmolLM2-135M-Instruct",
      device="cuda" if torch.cuda.is_available() else "cpu",
      dtype=torch.bfloat16,
  )
  ```
  - Initializes tokenizer and causal language model.
  - Automatically handles cuDNN symbols on cutting-edge architectures (RTX 5000 / Blackwell) by disabling cudnn SDPA and utilizing native eager ATen kernels.
  - Precomputes single-token candidate identifier IDs: `[A]`, `[B]`, ..., `[Z]`.

- **Method `format_prompt(board, rack, score_diff, bag_remaining, candidates) -> str`:**
  - Encodes the full turn context into a concise markdown structured prompt:
    - Current score differential and bag count.
    - Current rack letters (using `?` for blanks).
    - Ranked list of candidate moves with coordinates, points, leave equity, defense adjustment, and move type (Word play, Blank assignment, Exchange, or Pass).
  - Prompts the model to emit the single optimal letter label `[A]`–`[Z]`.

- **Method `rank_candidates(board, rack, score_diff, bag_remaining, candidates) -> list[tuple[dict, float]]`:**
  - Evaluates all candidate moves simultaneously in a single transformer forward pass.
  - Extracts the logits at the prompt's final token index corresponding to the active candidate token IDs.
  - Applies float32 softmax normalization over candidate logits.
  - Returns candidates paired with model choice probabilities, sorted in descending order: `[(best_move, prob), ...]`.
  - **Inference Latency:** **~15.6 ms** per turn on RTX 5070 Ti GPU.

---

## Performance Benchmark Summary

| Module | Operation | Latency | Device |
| :--- | :--- | :--- | :--- |
| `structure.pyx` | Full board legal move generation | $3.2 \text{ ms}$ | 1 CPU Core |
| `leave_eval.py` | Full Super-Leaves rack evaluation | $0.008 \text{ ms}$ | CPU |
| `defense.py` | Line-of-sight hot-spot analysis | $0.015 \text{ ms}$ | CPU |
| `endgame.py` | Exact minimax search (depth 4) | $0.0008 \text{ ms}$ | CPU |
| `alphable_net.py` | Batched forward pass (batch=64) | $1.4 \text{ ms}$ | RTX 5070 Ti CUDA |
| `transformer_ranker.py` | Full candidate ranker forward pass | $15.6 \text{ ms}$ | RTX 5070 Ti CUDA |
| `search.py` | Full 1-ply lookahead ($K=5, N=10$) | $1.2 \text{ to } 1.8 \text{ s}$ | Hybrid CPU/CUDA |

---

## Integration Tests
All modules are verified by comprehensive unit tests in [`tests/`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/tests):
- `tests/core/test_blank_movegen.py`: Validates GADDAG `.upper()` lowercase blank hook generation.
- `tests/core/test_crn_search.py`: Validates Common Random Numbers variance reduction.
- `tests/core/test_leave_eval.py`: Validates Super-Leaves tables and duplicate blank formula.
- `tests/core/test_defense.py`: Validates Triple Word Score lane blocking and dynamic score weighting.
- `tests/core/test_endgame.py`: Validates minimax alpha-beta terminal spread maximization.
- `tests/models/test_transformer_ranker.py`: Validates SmolLM2 single-token logit extraction, blank handling, exchange/pass support, and probability normalization.
- `tests/models/test_transformer_runner_integration.py`: Validates online bot execution loop using transformer candidate ranker mode.
- `tests/training/test_train_transformer_ranker.py`: Validates grandmaster match turn extraction and collation.
- Run all tests: `pytest tests/` (214/214 passing).
