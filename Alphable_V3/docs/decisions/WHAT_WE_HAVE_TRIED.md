# Alphable: What We Have Tried & Experiment History

This document chronicles the research trajectory, algorithmic pivots, empirical successes, and discarded approaches across the development of **Alphable**.

---

## 1. Project Genesis & Historical Evolution

### Phase 1: V1 Initial Prototypes
- **Goal:** Establish a working Scrabble board simulator and connect Python to a high-speed GADDAG move generator in C++.
- **Outcome:** Successfully built Cython wrapper over C++ GADDAG. Established board representation and legal move generation in under 5 ms.
- **Limitation:** Simple policy-gradient attempts suffered from the massive discrete action space (thousands of plays per turn).

### Phase 2: V2 After-State Value Baseline
- **Goal:** Bypass the intractable policy action space by shifting to an **After-State Value Network** (evaluating board and rack after a candidate move is simulated).
- **Architecture:** 5-block ResNet with 27-channel board tensor (letter planes + static premium squares) and 29-dimensional state vector.
- **Dataset:** Initial supervised pretraining on early game logs.
- **The Strategic Plateau:**
  - In match play against `GreedyBot`, V2 struggled, winning only **1 out of 6 games (16.7%)**.
  - The model frequently played low-scoring "defensive" moves while conceding massive open Triple Word hooks to the opponent.
  - Value predictions were noisy and unstable.

---

## 2. V3 Architecture & Algorithmic Overhaul

In V3, an exhaustive systemic audit revealed deep foundational bugs and architectural limitations spanning the rules engine, tensor encoding, dataset labeling, and lookahead search.

### Benchmark Progression Against `GreedyBot`
Under identical evaluation conditions (5–6 game matches using 1-ply lookahead search):

| Milestone | Architecture / Pipeline | Win Rate vs Greedy | Avg Pts / Game | Net Margin vs Greedy | Top Plays Demonstrated |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **V2 Legacy Baseline** | 27 channels, uncorrected cross-words & search | **16.7%** (1/6) | ~340 | -75.0 | `STHENIC` (75) |
| **V3 Supervised Clean** | 31 channels, continuous deficit labels, fixed search | **60.0%** (3/5) | 412.0 | -16.4 | `ALNAGER` (75), `UNIQUE` (51) |
| **V3 RL Generation 2** | Clean curriculum (Mirror + Anti-Greedy, `--keep-p0-only`) | **80.0%** (4/5) | **447.2** | **+56.2** | `TRAPNEST` (89), `ONIGIRIS` (78), `QINTAR` (52) |

---

## 3. What Worked (Empirical Breakthroughs)

### A. Dynamic Open Premium Square Channels (Channels 27–30)
- **Concept:** In V2, premium squares (DL, TL, DW, TW) were statically encoded.
- **Pivot:** In V3, channels 27–30 are set to $1.0$ only if the premium square is **unoccupied**. Once a tile is played onto a premium square, it transitions to $0.0$.
- **Impact:** Teaches the network spatial board exhaustion. The model no longer assumes covered multipliers are available for future plays.

### B. Enriched 36-Dimensional Leave & Balance Vector
- **Concept:** Scrabble strategy depends heavily on rack leave balance.
- **Additions:**
  - Vowel ratio and consonant ratio.
  - Explicit blank (`?`) and `'S'` presence indicators.
  - Duplicate letter penalty ratio ($\sum \max(0, \text{count}-1) / 7.0$).
  - Empty leave indicator (identifying out-of-tiles / bingos).
- **Impact:** Dramatic reduction in vowel/consonant trapping. The agent actively preserves blanks and `'S'` tiles for high-leverage bingo turns.

### C. Continuous Deficit-Scaled Hard Negative Labeling
- **The Problem:** In V2, every legal alternative move that was not the played expert move was labeled with target $-1.0$. If the expert played for 34 points and an alternative move scored 32 points, the 32-point move was punished as a catastrophic loss ($-1.0$).
- **The Solution:** Replaced binary $-1.0$ labeling with continuous deficit scaling:
  $$\text{deficit\_ratio} = \min\left(1.0, \frac{\text{pos\_score} - \text{neg\_score}}{\max(10, \text{pos\_score})}\right)$$
  $$\text{target} = \max(-1.0, 1.0 - 2.0 \times \text{deficit\_ratio})$$
- **Result:** Validation loss dropped from **0.4112 down to 0.0293** (>14x improvement in model convergence).

### D. Zero-Sum Minimax Opponent Reply Equity Deduction
- **The Problem:** 1-ply search previously ranked opponent replies purely by the neural network value `opp_vals` without adding `opp_points`.
- **The Solution:** Formulated full reply equity:
  $$\text{Opponent Reply Equity} = \text{opp\_points} + 25.0 \times V_{\text{opp}}(s'')$$
  $$\text{Candidate Net Equity} = \text{cand\_points} - \text{Expected Opponent Equity}$$
- **Result:** Instantly eliminated board-opening blunders. Win rate against GreedyBot rose from 16.7% to 60% immediately.

### E. Anti-Greedy Sample Shielding (`--keep-p0-only`)
- **The Problem:** When running curriculum self-play against `GreedyBot`, if Greedy won, its point-chasing turns were previously recorded into the training set with positive labels.
- **The Solution:** The `--keep-p0-only` flag restricts recording to Player 0 (the neural network), teaching the agent how to counter greedy play without adopting greedy blunders.
- **Result:** Pushed win rate from 60% to **80%** in RL Generation 2.

---

## 4. What Failed & Key Lessons Learned

### A. Categorical Policy Head
- Attempting to output a categorical probability distribution over all possible $(r, c, \text{dir}, \text{word})$ actions failed due to exponential combinatorial action spaces ($1000+$ moves per turn).
- **Lesson:** After-State Value Modeling combined with fast C++ move generation is the optimal architecture for Scrabble.

### B. Binary Hard-Negative Penalty (-1.0)
- Punishing high-scoring alternative plays destroyed the network's value calibration and caused severe gradient thrashing during supervised pretraining.
- **Lesson:** Supervised target labels must reflect continuous strategic quality.

### C. Search Lookahead Without Move Points
- Trying to simulate opponent counterattacks using only value network predictions without adding immediate move points left the search engine blind to high-point plays.
- **Lesson:** Immediate points are mandatory in Scrabble equity calculations.

### D. Static 7-Tile Bag Decrement
- Decrementing the tile bag by 7 on every turn drained the bag in 14 turns, causing late-game states to be trained with incorrect bag counts.
- **Lesson:** Tile bag accounting must strictly track tiles actually placed on the board from the rack.
