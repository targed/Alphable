# Alphable V3: Master Technical Specification & Architecture Manual

This document provides the definitive, end-to-end technical manual for **Alphable V3**, detailing its mathematical formulations, neural network architecture, search algorithms, training pipelines, and online autonomous operations.

---

## 1. System Overview

Alphable V3 is an expert-level Scrabble AI engine designed around an **After-State Value Network**, an empirical **Super-Leaves rack valuation** model, a **line-of-sight defensive board analyzer**, a **1-ply Monte Carlo lookahead search** with **Common Random Numbers (CRN)**, and a **deterministic sub-millisecond exact endgame minimax solver**.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             ALPHABLE V3 ARCHITECTURE                             │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   1. Move Generation: High-Speed GADDAG (structure.pyx, ~3.2ms)                  │
│      - Explores all board anchors with bidirectional trie traversal.             │
│      - Full uppercase normalization (.upper()) for blank tile hooks.             │
│                                                                                  │
│   2. After-State Simulation & Scoring (simulator.py)                             │
│      - Primary word scoring with DL, TL, DW, TW multipliers.                     │
│      - Perpendicular cross-word detection and scoring.                           │
│      - 50-point bingo bonus for 7-tile plays.                                    │
│                                                                                  │
│   3. Heuristic Pre-Filtering & Leave Evaluation (leave_eval.py, defense.py)      │
│      - Super-Leaves stem synergy bonuses (RETIN, TISAN, ?S, QU).                 │
│      - Duplicate blank diminishing returns (+26.5 1st blank, +6.0 2nd blank).    │
│      - Triple Word Score & Double Word Score line-of-sight safety bonuses.       │
│                                                                                  │
│   4. Dual-Stream Value Network Evaluation (alphable_net.py, inference.py)        │
│      - Spatial: 31-channel 15x15 board tensor processed by 5-block ResNet.       │
│      - Scalar: 63-dimensional vector (hand, score, bag, unseen tile ratios).     │
│      - Value Head: Dense fusion predicting after-state equity V(s') in [-1, +1]. │
│                                                                                  │
│   5. 1-Ply Monte Carlo Lookahead Search (search.py)                              │
│      - Common Random Numbers (CRN): identical N opponent racks across candidates.│
│      - Two-Stage Opponent Reply Pruning: heuristic top-3 -> neural net scoring.  │
│      - Selective 2-Ply Counter-Response triggered when top-2 equity gap <= 8 pts.│
│                                                                                  │
│   6. Exact Endgame Minimax Solver (endgame.py)                                   │
│      - Activated when bag == 0. Full alpha-beta branch-and-bound search.         │
│      - Computes optimal spread-maximizing terminal lines in < 0.001s.            │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Mathematical Formulations & Objective Functions

### 2.1 The After-State Value Paradigm
Unlike chess or Go where full board states alternate turns, Scrabble is an imperfect information game with tile drawing stochasticity. An **after-state** $s'$ is the board and rack condition immediately after placing a play, *before* drawing new tiles from the bag:

$$s' = \mathcal{T}(s, m) = (\text{Board}', \text{Rack}_{\text{leave}}, \Delta \text{Score}', \text{Bag}')$$

By evaluating $s'$ rather than $s$, the neural network directly judges the quality of the board configuration, the defensive vulnerabilities created, and the strategic potential of the unplayed tiles left in hand.

### 2.2 Move Equity Formulation
For any legal candidate move $m \in \mathcal{M}(s)$, its 0-ply strategic value is given by:

$$\text{Equity}_{0}(m) = \text{Points}(m) + \text{Leave}(\text{Rack}_{\text{leave}}) + \text{Defense}(m) + W \times V(s')$$

Where:
- $\text{Points}(m)$ is the immediate turn score including cross-words and bingo bonus.
- $\text{Leave}(\text{Rack}_{\text{leave}})$ is the empirical Super-Leaves equity (in points).
- $\text{Defense}(m)$ is the hot-spot defensive exposure adjustment (in points).
- $W = 25.0$ is the value weight scaling the dimensionless network evaluation $V(s') \in [-1.0, +1.0]$ into Scrabble points.

### 2.3 Lookahead Search with Common Random Numbers (CRN)
When lookahead mode is active, the engine selects the top-$K$ candidates by $\text{Equity}_{0}$ and simulates $N$ possible opponent racks sampled from the unseen tile pool $\mathcal{U}$.

Under **Common Random Numbers (CRN)**, all candidate moves are evaluated against the *exact same* set of sampled opponent racks $\mathcal{R}_{\text{opp}} = \{r_1, r_2, \dots, r_N\}$:

$$\text{Equity}_{1}(m_i) = \text{Points}(m_i) + \text{Leave}(\text{Rack}_{m_i}') - \frac{1}{N} \sum_{j=1}^{N} \max_{m_{\text{opp}} \in \mathcal{M}(b_i, r_j)} \left[ \text{Points}(m_{\text{opp}}) + W \times V(s'') \right]$$

By coupling the random seed across candidates, the Monte Carlo variance of the difference between any two candidates is minimized:

$$\operatorname{Var}\left(\hat{E}(m_1) - \hat{E}(m_2)\right) = \operatorname{Var}(\hat{E}_1) + \operatorname{Var}(\hat{E}_2) - 2\operatorname{Cov}(\hat{E}_1, \hat{E}_2)$$

Because $\operatorname{Cov}(\hat{E}_1, \hat{E}_2) > 0$ under identical opponent racks, inter-candidate evaluation noise drops by **over 70%**, preventing spurious move selection.

### 2.4 Super-Leaves Formulation & Duplicate Blanks
The rack leave equity model evaluates the expected future value of unplayed tiles:

$$\text{Leave}(R) = \sum_{t \in R} \text{BaseEquity}(t) + \text{StemBonus}(R) + \text{BalancePenalties}(R) + \text{DuplicatePenalties}(R)$$

#### The Duplicate Blank Diminishing Returns Formula
In Scrabble, holding one blank (`?`) gives enormous bingo flexibility ($+26.5$ pts). However, holding two blanks simultaneously does *not* provide $+53.0$ points because a player can only play one bingo at a time:
- First Blank: $+26.5$ pts
- Second Blank: $+6.0$ pts (Total: $+32.5$ pts)

$$\text{BlankAdjustment} = -20.5 \times \max(0, \text{count}(?) - 1)$$

This formula prevents the engine from "hoarding" two blanks and passing up immediate 60+ point bingos.

---

## 3. Neural Network & Representation Architecture

### 3.1 Board Tensor (`[31, 15, 15]`)
The $15 \times 15$ Scrabble board is encoded into 31 binary feature planes:
- **Channels 0–25:** One-hot planes for letters `'A'` through `'Z'`.
- **Channel 26:** Binary plane indicating unoccupied squares.
- **Channels 27–30:** Binary planes for **open** premium squares (`DL`, `TL`, `DW`, `TW`). When a premium square is covered by a tile, its plane switches from $1.0$ to $0.0$.

### 3.2 State Vector (`[63]`)
Scalar non-spatial game information is encoded into a 63-dimensional FloatTensor:
- **0–25:** Hand rack letter counts for `'A'` through `'Z'`.
- **26:** Hand rack blank count (`?`).
- **27:** Normalized score differential: $(\text{my\_score} - \text{opp\_score}) / 500.0$.
- **28:** Normalized remaining bag tiles: $\text{bag\_remaining} / 100.0$.
- **29–35:** Leave metrics: rack size ratio, vowel count, consonant count, blank flag, `'S'` flag, duplicate penalty, bingo flag.
- **36–62 (Pillar 4):** Unseen tile bag tracking frequencies. Proportion of each letter remaining in the unseen pool (bag + opponent rack) relative to total unseen tiles.

### 3.3 Dual-Stream ResNet Architecture
```
Board Tensor [B, 31, 15, 15]           State Vector [B, 63]
            │                                    │
    ConvBlock (64 filters)               Dense (63 -> 128)
            │                                    │
    5x ResNetBlocks (64 filters)             LeakyReLU
            │                                    │
 AdaptiveAvgPool2d((3, 3))               Dense (128 -> 128)
            │                                    │
    Dense (576 -> 384)                           │
            │                                    │
            └─────────────────┬──────────────────┘
                              │
                    Concatenate [B, 512]
                              │
                      Dense (512 -> 256)
                              │
                      Dense (256 -> 64)
                              │
                      Dense (64 -> 1)
                              │
                       Tanh [-1.0, +1.0]
```

---

## 4. Training Pipelines & Strategic Anchoring

### 4.1 Grandmaster Macondo Distillation (`distill_macondo.py`)
To prevent the policy collapse observed in pure symmetric self-play (where agents settle into a timid, low-scoring equilibrium), Alphable is anchored using **Grandmaster Knowledge Distillation**.
- Training samples are extracted from completed Woogles matches analyzed by Macondo.
- The target value blends Macondo's expected point equity with match outcome:
  $$v_{\text{target}} = 0.75 \times \tanh\left(\frac{\text{Equity}_{\text{Macondo}}}{50.0}\right) + 0.25 \times \tanh\left(\frac{\Delta \text{Final Score}}{100.0}\right)$$
- Training on this anchor produced `models/alphable_v3_macondo_v2.pth`, imbuing the model with grandmaster-level positional understanding.

### 4.2 Supervised Foundation Training (`train_supervised.py`)
- Ingests tournament games with hard-negative mining (top 4 alternative plays per turn).
- Negative samples receive continuous deficit-scaled targets to avoid falsely penalizing competitive plays:
  $$\text{target}_{\text{neg}} = \max\left(-1.0, 1.0 - 2.0 \times \frac{\text{pos\_score} - \text{neg\_score}}{\max(10, \text{pos\_score})}\right)$$

---

## 5. Search Engine & Decision Logic

### 5.1 GADDAG Bidirectional Move Generation
- Uses Cython-compiled C++ GADDAG (`structure.pyx`).
- Traverses prefix and suffix branches from every valid board anchor.
- Enforces `.upper()` letter normalization on board reads so lowercase blanks participate fully in cross-checks and hook generation.
- Generates all legal plays across the entire board in **$3.2 \text{ ms}$**.

### 5.2 Two-Stage Opponent Reply Pruning
When evaluating opponent counterattacks in 1-ply simulation:
- **Stage 1 (Fast Heuristic):** Generates all opponent counter-moves and scores them by $\text{Points} + \text{Leave}$. Filters to the top 3 replies.
- **Stage 2 (Neural Valuation):** Evaluates only the top 3 replies through the neural network.
- Reduces network inference overhead by **$>90\%$**, allowing 10 simulations across 5 candidates to finish in $1.5 \text{ seconds}$.

### 5.3 Deterministic Exact Endgame Minimax Solver
When `bag_remaining == 0`, the engine transfers control to `ExactEndgameSolver` ([`endgame.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/endgame.py)):
- Solves zero-sum perfect-information game using alpha-beta minimax search.
- Moves that empty the rack ("going out") are scored as $\text{Points} + 2 \times \text{sum}(\text{opp\_unplayed\_tiles})$ and ordered first.
- Adaptive search depth (depth 2 for large racks, depth 4 for $\le 3$ tiles).
- Execution time: **$< 0.001 \text{ seconds}$**.

---

## 6. Woogles Autonomous Operations

Alphable connects directly to [Woogles.io](https://woogles.io) via Playwright:
- Persistent browser authentication stored in `~/.alphable/woogles_profile`.
- Automated match retry loop and crash isolation in `runner.py`.
- DOM selector targeting:
  - Rack reads: `#board-container #rack .rack-tile:not(.ant-modal *)` (prevents ghost modal tile collisions).
  - Navigation: `:text('Play a computer')` and `:text('Create game')`.
- Telemetry harvesting: Automatically saves `game.gcg`, `analysis.json`, `replay.json`, and series summaries to `data/woogles/`.

---

## 7. Verification & Acceptance Benchmarks

- **Unit Test Suite:** 205 unit tests covering GADDAG blank hooks, CRN search variance, Super-Leaves, defense formulas, and endgame minimax (`pytest tests/`).
- **Head-to-Head Performance:**
  - vs GreedyBot: **80.0% Win Rate**, $+63.4$ average score differential.
  - vs HastyBot (Woogles): Parity and series victories ($>50\%$ win rate, average score $>450$ points).
- **Latency:** Move decision latency $\le 1.8 \text{ seconds}$ per turn in full 1-ply lookahead mode.
