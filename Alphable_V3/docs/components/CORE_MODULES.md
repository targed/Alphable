# Alphable V3: Core Modules Reference

This document provides a comprehensive, file-by-file reference for all modules in [`src/alphable/core/`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core).

---

## 1. `simulator.py` ([`src/alphable/core/simulator.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/simulator.py))

The Scrabble board state transition and move evaluation simulator. Implements official international Scrabble scoring and word validation mechanics.

### Constants
- `LETTER_VALUES`: Standard dictionary mapping uppercase letters `A`–`Z` to their face point values (`E=1, Q=10, Z=10, etc.`). Blanks (`?` or lowercase letters) map to `0`.
- `BONUS_TILES`: $15 \times 15$ grid mapping coordinates to premium types:
  - `'..'`: Regular square
  - `'DL'`: Double Letter
  - `'TL'`: Triple Letter
  - `'DW'`: Double Word (includes center star at (7, 7))
  - `'TW'`: Triple Word

### Key Functions

#### `create_empty_board()`
- **Returns:** $15 \times 15$ list of lists initialized with `'.'` (or `' '`).

#### `simulate_move(board, move, rack)`
Applies a candidate move to the board and calculates exact points earned and remaining leave rack.
- **Parameters:**
  - `board` (`list[list[str]]`): Current $15 \times 15$ board.
  - `move` (`dict`): Candidate move with keys:
    - `'row'` (`int`): Starting row index $[0, 14]$.
    - `'col'` (`int`): Starting column index $[0, 14]$.
    - `'dir'` (`str`): `'Across'` or `'Down'`.
    - `'word'` (`str`): Word placed (blanks designated as lowercase characters or `?`).
  - `rack` (`list[str]`): Player's current rack.
- **Scoring Mechanics:**
  1. Identifies which tiles are newly placed from the rack vs pre-existing on the board.
  2. Main Word Score: Sum of letter values multiplied by active letter premiums (`DL`, `TL`), then multiplied by active word premiums (`DW`, `TW`). Pre-existing tiles on the board retain letter value but do *not* trigger square multipliers.
  3. Cross-Words Scoring (`_score_cross_word`): Scans perpendicularly for every newly placed tile. If adjacent tiles form a perpendicular cross-word, calculates perpendicular letter multipliers and word multipliers.
  4. Bingo Bonus: If exactly 7 tiles from the rack are placed, awards an additional $+50$ points.
- **Returns:** `(new_board, total_points, new_rack)`
  - `new_board` (`list[list[str]]`): Updated $15 \times 15$ board.
  - `total_points` (`int`): Total points scored.
  - `new_rack` (`list[str]`): Leave rack remaining after played tiles are subtracted.

---

## 2. `inference.py` ([`src/alphable/core/inference.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/inference.py))

Handles feature encoding, tensor transformations, and the high-level inference interface.

### Key Functions & Classes

#### `board_to_tensor(board)`
Converts a $15 \times 15$ board into a PyTorch FloatTensor of shape `[31, 15, 15]`.
- Channels 0–25: One-hot planes for `'A'` through `'Z'`.
- Channel 26: Binary plane for empty squares.
- Channels 27–30: Binary planes for **open** premium squares (`DL`, `TL`, `DW`, `TW`). Only unoccupied premium squares have $1.0$; once covered, they switch to $0.0$.

#### `state_to_tensor(rack, score_diff, bag_remaining)`
Converts scalar game features into a PyTorch FloatTensor of shape `[36]`.
- Letter counts, vowel/consonant counts, blank and `'S'` presence indicators, duplicate penalty, score difference normalized by 500, and bag size normalized by 100.

#### `AlphableInference`
High-level inference engine wrapping the neural network and GADDAG move generator.
- **Constructor:** `AlphableInference(model_path=None, device='cpu', dict_path='resources/CSW24.txt')`
  - Loads GADDAG dictionary into memory.
  - Initializes `AlphableValueNet` on the requested device (`cuda` or `cpu`).
  - Warm-starts weights via `load_checkpoint_compatible`.
- **Method:** `find_best_move(current_board, rack, current_score_diff, bag_remaining)`
  - Generates legal moves via GADDAG.
  - Simulates all after-states in batch.
  - Evaluates via neural network.
  - Returns `(best_move, best_value)` maximizing $\text{Points} + 25.0 \times V(s')$.

---

## 3. `alphable_net.py` ([`src/alphable/core/alphable_net.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/alphable_net.py))

PyTorch deep learning implementation of the dual-stream After-State Value Network.

### Modules & Classes
- `ConvBlock`: Basic convolutional block (`Conv2d` $\to$ `BatchNorm2d` $\to$ `LeakyReLU(0.01)`).
- `ResNetBlock`: Residual block with skip-connection:
  $$y = \text{LeakyReLU}(x + \text{BN}(\text{Conv}(\text{LeakyReLU}(\text{BN}(\text{Conv}(x))))))$$
- `AlphableValueNet`: Complete dual-stream architecture:
  - Spatial Stream: 5 residual blocks, adaptive pooling to $3 \times 3$, dense projection to 384 dims.
  - Scalar Stream: 2-layer MLP projecting 36 dims $\to$ 128 dims.
  - Head: Concatenates spatial (384) and scalar (128) = 512 dims, followed by 3 dense layers $(512 \to 256 \to 64 \to 1)$ with `Tanh` activation.
- `load_checkpoint_compatible(model, checkpoint_path, device)`:
  - Intelligently reloads weights across different architecture versions.
  - Slices matching channels if input tensor shapes vary between generations.
  - Returns `(loaded_tensors, total_tensors)`.

---

## 4. `search.py` ([`src/alphable/core/search.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/search.py))

Monte Carlo 1-ply lookahead search engine with zero-sum minimax opponent reply equity deduction.

### Functions & Classes
- `get_unseen_distribution(board, my_rack)`:
  - Subtracts all board tiles and current rack tiles from the standard 100-tile Scrabble set.
  - Returns the list of unseen tiles.
- `sample_opponent_rack(unseen_tiles, sample_size=7)`:
  - Randomly samples 7 tiles from unseen tiles to simulate an opponent rack.
- `AlphableSearch`:
  - `find_best_move(board, rack, score_diff, bag_remaining)`:
    - Filters top-K candidates by 0-ply equity.
    - For each candidate, simulates $N$ random opponent racks.
    - Generates opponent replies, evaluates opponent reply equity ($\text{Points} + 25 \times V_{\text{opp}}$), and computes the softmax expectation over top counterattacks.
    - Deducts opponent reply equity to determine true net candidate equity.

---

## 5. `structure.py` ([`src/alphable/core/structure.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/structure.py))

Python/Cython bridge connecting the high-level Python engine to the high-speed C++ GADDAG move generator.

### Classes
- `Gaddag`: In-memory directed acyclic word graph optimized for bi-directional letter generation.
  - `load(dict_path)`: Loads CSW24 or NWL2023 text dictionary into a compiled GADDAG structure.
- `MoveGenerator`: High-speed move generator.
  - `generate(board, rack)`: Explores all valid board anchor squares and returns a Python list of dictionaries representing legal Scrabble plays in under 5 ms.
