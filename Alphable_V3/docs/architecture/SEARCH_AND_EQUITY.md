# Alphable V3: Search & Move Equity Formulation

This document details the search algorithm, evaluation mathematics, and tactical lookahead mechanics that power move selection in **Alphable V3**.

---

## 1. The Scrabble Equity Equation

In Scrabble, choosing the move with the highest immediate points is known as **Greedy play**. While greedy play is strong against novice humans, it routinely loses to expert players because it ignores:
1. **Leave Quality:** Discarding high-value synergy tiles (e.g. burning both blanks or dumping an `'S'` for 8 points).
2. **Board Openness:** Playing a high-scoring word that leaves an open Triple Word Score or Triple Letter hook for the opponent.
3. **Endgame Tile Trapping:** Failing to track remaining unseen tiles as the bag empties.

To balance immediate points with long-term strategic advantage, Alphable models move selection using **Total Equity**:

$$\text{Equity}(m) = \text{Points}(m) + \lambda \times V(s'_m)$$

Where:
- $\text{Points}(m)$: Immediate score earned by playing move $m$ (including all cross-words, premium multipliers, and the +50 bingo bonus).
- $s'_m$: The **after-state** resulting from playing $m$ on the current board.
- $V(s'_m) \in [-1.0, 1.0]$: Neural network value estimating the mover's long-term win probability / normalized margin from after-state $s'_m$.
- $\lambda = 25.0$: The **Equity Scale Factor**. In championship Scrabble AI research, a $+1.0$ swing in value (from even to dominant) corresponds to an equity advantage of roughly $+25$ points.

---

## 2. Decision Modes: 0-Ply Direct Evaluation vs 1-Ply Lookahead

Alphable supports two move selection modes in [`src/alphable/core/search.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/search.py):

### A. 0-Ply Direct Evaluation (`mode='bc_0ply'`)
1. Generate all legal moves $M$ using the C++ GADDAG generator.
2. For each move $m \in M$, simulate the after-state $s'_m$.
3. Run a batched forward pass through `AlphableValueNet` to obtain $V(s'_m)$ for all candidates simultaneously.
4. Compute $\text{Equity}(m) = \text{Points}(m) + 25.0 \times V(s'_m)$.
5. Select $\arg\max_m \text{Equity}(m)$.
- **Latency:** ~5–15 ms total per turn on GPU.

### B. 1-Ply Monte Carlo Lookahead (`mode='lookahead'`)
When playing against high-level opponents, direct 0-ply evaluation can occasionally overlook an opponent's direct tactical counterattack. 1-ply lookahead simulates the opponent's strongest replies using **Monte Carlo Rack Sampling**.

---

## 3. The 1-Ply Monte Carlo Rack Sampling Algorithm

```
+-----------------------------------------------------------------------------+
|                      1-Ply Monte Carlo Search Workflow                      |
+-----------------------------------------------------------------------------+
|                                                                             |
|  1. Candidate Generation & 0-Ply Filtering                                  |
|     - Generate all legal moves for our rack using GADDAG.                   |
|     - Score each candidate via 0-ply Equity = Points + 25 * V(s').         |
|     - Select top-K candidates (default: K=3) for deep lookahead simulation. |
|                                                                             |
|  2. Unseen Tile Distribution Calculation                                    |
|     - Standard Bag (100 tiles) - Board Tiles - Our Rack = Unseen Tiles.     |
|                                                                             |
|  3. Monte Carlo Simulation Loop (for each of the K candidates):             |
|     FOR sim = 1 to N_simulations (default: N=10):                           |
|       a. Sample 7 random tiles from Unseen Tiles to form Opponent Rack.     |
|       b. Generate all legal opponent replies on resulting board cand_board. |
|       c. Simulate each opponent reply to get (opp_points, opp_afterstate).  |
|       d. Forward pass opp replies: opp_val = model(opp_afterstate).         |
|       e. Calculate Opponent Reply Equity:                                   |
|          opp_equity = opp_points + 25.0 * opp_val                           |
|       f. Softmax-temperature average over top opponent replies:             |
|          expected_opp_equity = sum(w_i * opp_equity_i)                      |
|       g. Net Simulation Value = -expected_opp_equity / 25.0                 |
|                                                                             |
|  4. Candidate Equity Ranking & Move Selection                               |
|     - Average simulation value across all N simulations.                    |
|     - cand_total_equity = cand_points - expected_opp_equity                 |
|     - Select candidate with maximum net equity.                             |
|                                                                             |
+-----------------------------------------------------------------------------+
```

### Unseen Tile Probability Distribution
Implemented in `get_unseen_distribution(board, my_rack)`:
- Total standard Scrabble tile distribution consists of 100 tiles:
  `A:9, B:2, C:2, D:4, E:12, F:2, G:3, H:2, I:9, J:1, K:1, L:4, M:2, N:6, O:8, P:2, Q:1, R:6, S:4, T:6, U:4, V:2, W:2, X:1, Y:2, Z:1, ?:2`
- All tiles currently visible on the $15 \times 15$ board are decremented.
- All tiles in our own rack are decremented.
- The remaining multiset forms the true conditional distribution of unseen tiles in the bag and opponent rack.

---

## 4. Zero-Sum Opponent Reply Equity Deduction

### The Mathematical Formulation
In zero-sum game theory, our equity gain from a round equals what we score minus what our opponent scores on their counter-turn, plus the net value of the final board state:

$$\text{Net Equity}(m) = \text{Points}(m) - \text{Expected Opponent Equity}$$

Where:
$$\text{Expected Opponent Equity} = \sum_{j \in \text{top replies}} w_j \left( \text{opp\_points}_j + 25.0 \times V_{\text{opp}}(s''_j) \right)$$

And softmax temperature weights over the opponent's best replies:
$$w_j = \frac{\exp\left(\frac{\text{opp\_equity}_j - \max(\text{opp\_equity})}{\tau}\right)}{\sum_k \exp\left(\frac{\text{opp\_equity}_k - \max(\text{opp\_equity})}{\tau}\right)}$$

Using $\tau = 5.0$ prevents single noisy outlier plays from skewing the expected counter-reply while ensuring the opponent is modeled as choosing their highest-equity plays.

---

## 5. Live Tactical Defense Case Study

During baseline testing against `GreedyBot`:
- **Board State:** Turn 1, center opening.
- **Candidate 1:** `TAX` at (7, 6) Across.
  - Immediate Points: 20 pts.
  - Raw 0-ply Neural Value: $+0.716$.
  - 1-Ply Simulation: Conceded an open Triple Word hook where GreedyBot replied for $55+$ points.
  - 1-Ply Simulated Value: $-2.300$.
  - **Net Total Equity:** $20 - 57.5 = \mathbf{-37.5}$.
- **Candidate 2:** `DEATH` at (7, 7) Across.
  - Immediate Points: 26 pts.
  - Raw 0-ply Neural Value: $+0.453$.
  - 1-Ply Simulation: Closed down the open board; opponent reply was limited to safe low-scoring plays.
  - 1-Ply Simulated Value: $-1.850$.
  - **Net Total Equity:** $26 - 46.3 = \mathbf{-20.3}$.

**Outcome:** Under uncorrected search, the bot would have selected `TAX` because its 0-ply value was higher (+0.716 vs +0.453). With our zero-sum opponent equity deduction, Alphable correctly detected the counterattack, rejected `TAX`, played `DEATH`, and went on to win the game **412 to 379**.
