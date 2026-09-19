# Alphable V3: Neural Network & Representation Architecture

This document provides the complete, authoritative specification of the neural network architecture, tensor representation, and feature engineering used in **Alphable V3**.

---

## 1. High-Level Paradigm: The After-State Value Network

In traditional two-player board games like Chess or Go, AlphaZero uses a two-headed network $(P, V)$ where the policy head $P(a|s)$ outputs a probability distribution over the legal actions $a$.

In Scrabble, this approach fails because:
1. **Branching Factor:** A Scrabble rack often has $1000$ to $5000+$ distinct legal plays, each defined by coordinate $(r, c)$, orientation (Across/Down), word string, and blank assignment. A fixed categorical policy head is computationally intractable.
2. **Hidden Information:** The opponent's rack and remaining bag are partially observable.

**Alphable solves this via After-State Value Modeling:**
- The engine uses a high-performance C++ GADDAG move generator (via Cython) to generate all legal moves $M = \{m_1, m_2, \dots, m_k\}$ in under 5 milliseconds.
- For each candidate move $m_i$, the engine applies deterministic Scrabble transition rules to construct the **After-State** $s'_{m_i} = (B', R', \Delta S', \text{bag})$:
  - $B'$: Resulting $15 \times 15$ board state.
  - $R'$: Player's remaining leave rack (unplayed tiles).
  - $\Delta S'$: Updated score differential ($\text{Score}_{\text{player}} + \text{Points}(m_i) - \text{Score}_{\text{opp}}$).
  - $\text{bag}$: Number of tiles remaining in the bag.
- The neural network evaluates $V(s'_{m_i}) \in [-1, 1]$, estimating the mover's long-term expected game value from this post-move state.

---

## 2. Input Representation

The network consumes two input tensors:
1. **Board Spatial Tensor:** Shape `[B, 31, 15, 15]`
2. **Scalar State Vector:** Shape `[B, 36]`

```
+-------------------------------------------------------------------+
|                     Input Representations                         |
+-------------------------------------------------------------------+
|                                                                   |
|   1. Board Tensor: [B, 31, 15, 15]                                |
|      - Channels 0-25:  One-hot letter planes (A-Z)                |
|      - Channel 26:     Empty squares plane                        |
|      - Channels 27-30: Open Premium Squares (DL, TL, DW, TW)      |
|                                                                   |
|   2. Scalar State Vector: [B, 36]                                 |
|      - Dims 0-25:  Rack letter frequencies (A-Z)                  |
|      - Dim 26:     Rack blank count                               |
|      - Dim 27:     Normalized score diff (score_diff / 500.0)     |
|      - Dim 28:     Normalized bag count (bag_remaining / 100.0)   |
|      - Dim 29:     Leave length ratio (leave_len / 7.0)           |
|      - Dim 30:     Vowel ratio (vowels / 7.0)                     |
|      - Dim 31:     Consonant ratio (consonants / 7.0)             |
|      - Dim 32:     Has blank flag (1.0 or 0.0)                    |
|      - Dim 33:     Has 'S' flag (1.0 or 0.0)                      |
|      - Dim 34:     Duplicate letter penalty ratio                 |
|      - Dim 35:     Empty leave flag (1.0 if bingo/out, else 0.0)  |
|                                                                   |
+-------------------------------------------------------------------+
```

### A. Board Tensor Channel Layout (31 Channels)
The $15 \times 15$ Scrabble board is encoded into 31 float planes:

| Channels | Meaning | Description |
| :--- | :--- | :--- |
| **0 – 25** | Letter Planes | Binary planes for letters `A` through `Z`. If board square $(r, c)$ contains `'C'`, channel 2 has $1.0$ at $(r, c)$, and all other letter planes have $0.0$. Blanks placed on the board are marked with their designated letter. |
| **26** | Empty Squares | Binary plane: $1.0$ if board square $(r, c)$ is empty (`' '` or `'.'`), $0.0$ if occupied. |
| **27** | Double Letter (DL) | **Open** DL premium squares. If square $(r, c)$ is a Double Letter square AND is currently unoccupied, value is $1.0$; once covered by a tile, it becomes $0.0$. |
| **28** | Triple Letter (TL) | **Open** TL premium squares. $1.0$ if open TL, $0.0$ once covered. |
| **29** | Double Word (DW) | **Open** DW premium squares. $1.0$ if open DW, $0.0$ once covered. |
| **30** | Triple Word (TW) | **Open** TW premium squares. $1.0$ if open TW, $0.0$ once covered. |

> [!IMPORTANT]
> **V3 Architectural Pivot:** In V2, premium channels 27–30 were static throughout the game. In V3, they represent **open premium squares only**. Once a premium square is covered, it cannot be used again; updating channels 27–30 to zero prevents the network from falsely assuming a covered Triple Word is still accessible.

### B. Scalar State Vector Layout (36 Dimensions)
The scalar vector encodes tactical, strategic leave, and game-clock state:

| Index | Feature | Calculation / Formula | Range |
| :--- | :--- | :--- | :---: |
| **0 – 25** | Rack Letter Counts | Count of each letter `A`–`Z` remaining on rack | $[0, 7]$ |
| **26** | Rack Blank Count | Count of wildcards (`?`) on rack | $[0, 2]$ |
| **27** | Score Differential | `(score_mover - score_opponent) / 500.0` | $[-1.0, 1.0]$ |
| **28** | Bag Remaining | `bag_tiles_remaining / 100.0` | $[0.0, 1.0]$ |
| **29** | Leave Length Ratio | `len(rack) / 7.0` | $[0.0, 1.0]$ |
| **30** | Vowel Ratio | `vowel_count / 7.0` (vowels: A, E, I, O, U) | $[0.0, 1.0]$ |
| **31** | Consonant Ratio | `consonant_count / 7.0` | $[0.0, 1.0]$ |
| **32** | Has Blank Indicator | $1.0$ if `'?'` in rack, else $0.0$ | $\{0.0, 1.0\}$ |
| **33** | Has 'S' Indicator | $1.0$ if `'S'` in rack, else $0.0$ | $\{0.0, 1.0\}$ |
| **34** | Duplicate Penalty | $\sum_{\text{letter}} \max(0, \text{count} - 1) / 7.0$ | $[0.0, 1.0]$ |
| **35** | Empty Leave Flag | $1.0$ if rack is empty (bingo played / out of tiles), else $0.0$ | $\{0.0, 1.0\}$ |

---

## 3. Network Architecture: `AlphableValueNet`

Implemented in [`src/alphable/core/alphable_net.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/alphable_net.py).

### Visual Architecture Flowchart
```
Board Tensor: [B, 31, 15, 15]                      State Vector: [B, 36]
             │                                              │
             ▼                                              ▼
    Conv2d(31 -> 64, 3x3)                          Linear(36 -> 128)
             │                                              │
     BatchNorm2d + LeakyReLU                               BatchNorm1d + LeakyReLU
             │                                              │
      ResBlock 1 (64 -> 64)                         Linear(128 -> 128)
             │                                              │
      ResBlock 2 (64 -> 64)                         BatchNorm1d + LeakyReLU
             │                                              │
      ResBlock 3 (64 -> 64)                                 │
             │                                              │
      ResBlock 4 (64 -> 64)                                 │
             │                                              │
      ResBlock 5 (64 -> 64)                                 │
             │                                              │
    Conv2d(64 -> 32, 1x1)                                   │
             │                                              │
     BatchNorm2d + LeakyReLU                                │
             │                                              │
   AdaptiveAvgPool2d((3, 3))                                │
             │                                              │
     Flatten -> [B, 288]                                    │
             │                                              │
     Linear(288 -> 384)                                     │
             │                                              │
     BatchNorm1d + LeakyReLU                                │
             │                                              │
             └──────────────────────┬───────────────────────┘
                                    │
                                    ▼
                         Concatenation: [B, 512]
                                    │
                            Linear(512 -> 256)
                                    │
                           BatchNorm1d + LeakyReLU
                                    │
                            Linear(256 -> 64)
                                    │
                           BatchNorm1d + LeakyReLU
                                    │
                            Linear(64 -> 1)
                                    │
                                  Tanh
                                    │
                                    ▼
                         After-State Value V(s') in [-1.0, 1.0]
```

### A. Convolutional Spatial Trunk
1. **Initial Conv Block:** `Conv2d(31, 64, kernel_size=3, padding=1)` $\to$ `BatchNorm2d(64)` $\to$ `LeakyReLU(0.01)`.
2. **Residual Blocks (5 Blocks):**
   - Each residual block consists of:
     - `Conv2d(64, 64, kernel_size=3, padding=1)` $\to$ `BatchNorm2d(64)` $\to$ `LeakyReLU(0.01)`
     - `Conv2d(64, 64, kernel_size=3, padding=1)` $\to$ `BatchNorm2d(64)`
     - Residual skip connection: $y = \text{LeakyReLU}(x + F(x))$
3. **Spatial Compression:**
   - `Conv2d(64, 32, kernel_size=1)` $\to$ `BatchNorm2d(32)` $\to$ `LeakyReLU(0.01)`.
   - `AdaptiveAvgPool2d((3, 3))` pools the $15 \times 15$ grid down to $3 \times 3$.
   - Flattened dimension: $32 \times 3 \times 3 = 288$.
   - Spatial Dense Projection: `Linear(288, 384)` $\to$ `BatchNorm1d(384)` $\to$ `LeakyReLU(0.01)`.

### B. Scalar Dense Stream
1. `Linear(36, 128)` $\to$ `BatchNorm1d(128)` $\to$ `LeakyReLU(0.01)`.
2. `Linear(128, 128)` $\to$ `BatchNorm1d(128)` $\to$ `LeakyReLU(0.01)`.

### C. Fusion & Output Head
1. **Concatenation:** Concat spatial stream (384) + scalar stream (128) = **512 dimensions**.
2. **Dense MLP:**
   - `Linear(512, 256)` $\to$ `BatchNorm1d(256)` $\to$ `LeakyReLU(0.01)`.
   - `Linear(256, 64)` $\to$ `BatchNorm1d(64)` $\to$ `LeakyReLU(0.01)`.
   - `Linear(64, 1)`.
3. **Activation:** `Tanh()` output activation bounding values strictly within $[-1.0, 1.0]$.

---

## 4. Backwards Compatibility & Weight Remapping

To allow new model architectures to seamlessly warm-start from older checkpoints (such as legacy V2 models or models trained with different input dimensions), [`src/alphable/core/alphable_net.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/alphable_net.py) provides:

```python
def load_checkpoint_compatible(model, checkpoint_path, device='cpu'):
    """
    Loads model checkpoint weights with shape-safe filtering:
    - Exactly matching tensors are loaded directly.
    - If conv1 input channels differ (e.g. 27 channels in V2 vs 31 in V3),
      slices overlapping channels and randomly initializes new channels.
    - Skips mismatching dense layers, allowing deep trunk transfer learning.
    """
```

This ensures zero wasted compute: every new iteration preserves all learned convolutional spatial representations from earlier generations while adapting immediately to enriched inputs.
