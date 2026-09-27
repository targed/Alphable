# Alphable V3: Neural Network & Representation Architecture

This document provides the authoritative specification of the neural network architecture, tensor representation, and feature engineering used in **Alphable V3**.

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
2. **Scalar State Vector:** Shape `[B, 63]` (or backward-compatible `[B, 36]`)

```
+-------------------------------------------------------------------+
|                     Input Representations                         |
+-------------------------------------------------------------------+
|                                                                   |
|   1. Board Tensor: [B, 31, 15, 15]                                |
|      - Channels 0-25:  One-hot letter planes (A-Z)                |
|      - Channel 26:     Blank tiles placed on board                |
|      - Channels 27-30: Open Premium Squares (DL, TL, DW, TW)      |
|                                                                   |
|   2. Scalar State Vector: [B, 63]                                 |
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
|      - Dims 36-61: Unseen A-Z ratios (bag tracking)               |
|      - Dim 62:     Unseen blank '?' ratio (unseen_count / 2.0)    |
|                                                                   |
+-------------------------------------------------------------------+
```

### A. Board Tensor Channel Layout (31 Channels)
The $15 \times 15$ Scrabble board is encoded into 31 float planes:

| Channels | Meaning | Description |
| :--- | :--- | :--- |
| **0 – 25** | Letter Planes | Binary planes for letters `A` through `Z`. If board square $(r, c)$ contains `'C'`, channel 2 has $1.0$ at $(r, c)$, and all other letter planes have $0.0$. Blanks placed on the board are marked with their designated letter and also activate channel 26. |
| **26** | Blank Tile Placed | Binary plane: $1.0$ if board square $(r, c)$ contains a played blank tile (0 point value), distinguishing it from natural letter tiles. |
| **27** | Double Letter (DL) | **Open** DL premium squares. If square $(r, c)$ is a Double Letter square AND is currently unoccupied, value is $1.0$; once covered by a tile, it becomes $0.0$. |
| **28** | Triple Letter (TL) | **Open** TL premium squares. $1.0$ if open TL, $0.0$ once covered. |
| **29** | Double Word (DW) | **Open** DW premium squares. $1.0$ if open DW, $0.0$ once covered. |
| **30** | Triple Word (TW) | **Open** TW premium squares. $1.0$ if open TW, $0.0$ once covered. |

### B. Enriched State Vector (63 Dimensions)

| Indices | Feature | Formula / Value | Strategic Purpose |
| :--- | :--- | :--- | :--- |
| **0 – 25** | Rack Tile Counts | `count('A')` ... `count('Z')` | Exact remaining unplayed rack composition. |
| **26** | Rack Blank Count | `count('?')` | Critical: blanks are the most powerful tiles in Scrabble. |
| **27** | Score Differential | `score_diff / 500.0` | Positional context (leading vs trailing). |
| **28** | Bag Remaining | `bag_remaining / 100.0` | Game clock (opening vs mid-game vs endgame). |
| **29** | Leave Length | `len(rack) / 7.0` | Number of unplayed tiles retained. |
| **30** | Vowel Ratio | `vowel_count / 7.0` | Rack vowel balance. |
| **31** | Consonant Ratio | `consonant_count / 7.0` | Rack consonant balance. |
| **32** | Has Blank | `1.0` if `?` in rack else `0.0` | Binary indicator for bingo potential. |
| **33** | Has 'S' | `1.0` if `'S'` in rack else `0.0` | Binary indicator for hook potential. |
| **34** | Duplicate Penalty | $\sum \max(0, \text{count}-1) / 7.0$ | Clunker / duplicate tile redundancy metric. |
| **35** | Empty Leave (Bingo) | `1.0` if `len(rack) == 0` else `0.0` | Indicates 7-letter bingo or going out. |
| **36 – 61** | **Unseen Tile Distribution** | `unseen_count[char] / standard_count[char]` | Bag tracking: ratio of remaining unseen tiles A-Z. |
| **62** | **Unseen Blank Distribution** | `unseen_count['?'] / 2.0` | Bag tracking: ratio of remaining unseen blanks. |

---

## 3. Network Architecture: `AlphableValueNet`

The model consists of a **Dual-Stream Residual Network**:
- **Spatial Stream:** 5 Residual Convolutional blocks processing board spatial context.
- **State Stream:** Fully-connected MLP processing strategic leave and unseen tile counts.
- **Fusion Head:** Combines spatial and scalar embeddings to predict scalar equity in $[-1, 1]$.

```
 Board Tensor [B, 31, 15, 15]                     State Vector [B, 63]
            │                                              │
      Conv2d 3x3 (64)                               Linear(63 -> 64)
       BatchNorm2d                                        ReLU
          ReLU                                      Linear(64 -> 64)
            │                                             ReLU
     5x ResNet Blocks                                      │
  ┌──────────────────────┐                                 │
  │ Conv 3x3 (64) + BN   │                                 │
  │ ReLU                 │                                 │
  │ Conv 3x3 (64) + BN   │                                 │
  │ Skip Connection (+)  │                                 │
  │ ReLU                 │                                 │
  └──────────────────────┘                                 │
            │                                              │
    Conv2d 1x1 (2)                                         │
      BatchNorm2d                                          │
         ReLU                                              │
       Flatten                                             │
   Linear(450 -> 128)                                      │
         ReLU                                              │
            │                                              │
            └───────────────┬──────────────────────────────┘
                            ▼
                  Concatenate [B, 192]
                            │
                   Linear(192 -> 128)
                          ReLU
                   Linear(128 -> 64)
                          ReLU
                    Linear(64 -> 1)
                          Tanh
                            │
                            ▼
                   Value V(s') in [-1, 1]
```

### Flexible Weight Loading (`load_checkpoint_compatible`)
To support seamless migration between older 36-dimensional checkpoints and newer 63-dimensional models, [`inference.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/inference.py) implements `load_checkpoint_compatible()`:
- Automatically maps overlapping layers while initializing newly added unseen-distribution weights cleanly.
- Preserves backwards compatibility with legacy models.
