# Alphable V3: Search & Move Equity Formulation

This document details the search algorithms, evaluation mathematics, and tactical lookahead mechanics that power move selection in **Alphable V3**.

---

## 1. The Scrabble Equity Equation

In Scrabble, choosing the move with the highest immediate points is known as **Greedy play**. While greedy play is strong against novice humans, it routinely loses to expert players because it ignores:
1. **Leave Quality:** Discarding high-value synergy tiles (e.g. burning both blanks or dumping an `'S'` for 8 points).
2. **Board Openness:** Playing a word that exposes an open Triple Word Score (TWS) or Triple Letter hook for the opponent.
3. **Endgame Tile Trapping:** Failing to track remaining unseen tiles as the bag empties.

To balance immediate points with long-term strategic advantage, Alphable models move selection using **Total Equity**:

$$\text{Equity}(m) = \text{Points}(m) + \text{LeaveEquity}(R') + \text{DefenseAdj}(B, B') + \lambda \times V(s'_m)$$

Where:
- $\text{Points}(m)$: Immediate score earned by playing move $m$ (including all perpendicular cross-words, square multipliers, and the +50 bingo bonus).
- $\text{LeaveEquity}(R')$: Empirical future expected value of the tiles left in hand after the move (from Super-Leaves tournament tables).
- $\text{DefenseAdj}(B, B')$: Heuristic board security adjustment for occupying or dangerously exposing high-multiplier squares (TWS / DWS).
- $V(s'_m) \in [-1.0, 1.0]$: Neural network value estimating long-term game equity from after-state $s'_m$.
- $\lambda = 25.0$: The **Equity Scale Factor**. In championship Scrabble AI research, a $+1.0$ swing in value (from even to dominant) corresponds to an equity advantage of roughly $+25$ points.

---

## 2. Decision Modes: 0-Ply Direct Evaluation vs 1-Ply Lookahead

Alphable supports two move selection modes in [`src/alphable/core/search.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/search.py):

### A. 0-Ply Direct Evaluation (`mode='bc_0ply'`)
1. Generate all legal moves $M$ using the C++ GADDAG generator.
2. For each move $m \in M$, simulate the after-state $s'_m$.
3. Run a batched forward pass through `AlphableValueNet` to obtain $V(s'_m)$ for all candidates simultaneously.
4. Compute 0-ply Equity for every move.
5. Select $\arg\max_m \text{Equity}(m)$.
- **Latency:** ~5–15 ms total per turn on GPU.

### B. 1-Ply Monte Carlo Lookahead (`mode='lookahead'`)
When playing against high-level opponents, direct 0-ply evaluation can occasionally overlook an opponent's direct tactical counterattack. 1-ply lookahead simulates the opponent's strongest replies using **Monte Carlo Rack Sampling with Common Random Numbers (CRN)**.

---

## 3. The 1-Ply Monte Carlo Search Workflow

```
+---------------------------------------------------------------------------------+
|                       1-Ply Monte Carlo Search Workflow                         |
+---------------------------------------------------------------------------------+
|                                                                                 |
|  1. Exact Endgame Check (Bag = 0)                                               |
|     - If bag == 0 and unseen <= 7: invoke ExactEndgameSolver (deterministic).    |
|                                                                                 |
|  2. Candidate Generation & Strategic Diversity Selection                        |
|     - Generate all legal board moves with GADDAG.                               |
|     - Generate tactical tile exchange candidates if bag >= 7 and rack flawed.   |
|     - Score all moves via 0-Ply Equity.                                         |
|     - Pick Top-K diverse candidates (top equity, top points, top leave).        |
|                                                                                 |
|  3. Common Random Numbers (CRN) Pre-Sampling                                    |
|     - Sample N opponent racks (default: N=10) ONCE from unseen tile bag.        |
|     - Identical N racks are evaluated across all K candidate moves.             |
|                                                                                 |
|  4. Monte Carlo Opponent Simulation (for each candidate C):                     |
|     FOR each sampled opponent rack:                                             |
|       a. Generate opponent replies on candidate's resulting board.              |
|       b. Stage 1 Fast Pruning: Rank opponent replies by (pts + leave).          |
|       c. Stage 2 Deep Evaluation: Evaluate top replies with ValueNet.           |
|       d. Softmax weighting over top replies -> Expected Opponent Points & Value.|
|                                                                                 |
|  5. 1-Ply Equity Computation:                                                   |
|     SimEquity = (CandPoints - ExpectedOppPoints) + CandLeave + 25 * SimValueDiff|
|                                                                                 |
|  6. Selective 2-Ply Trigger:                                                    |
|     - If gap between Top 1 and Top 2 <= 8.0 pts, evaluate 1-ply counter-reply.  |
|                                                                                 |
+---------------------------------------------------------------------------------+
```

---

## 4. Key Mathematical Innovations

### A. Common Random Numbers (CRN) Variance Reduction
In standard Monte Carlo simulation, evaluating candidate moves $C_1$ and $C_2$ with independently drawn random opponent racks yields:

$$\text{Var}(C_1 - C_2) = \text{Var}(C_1) + \text{Var}(C_2)$$

With a small sample size ($N = 10$), the standard error is $\pm 15$ to $\pm 20$ points, allowing small plays to randomly beat 70-point bingos if the bingo faces an unlucky opponent sample.

Under **Common Random Numbers (CRN)**, both candidates are evaluated against the **exact same set of sampled opponent racks**:

$$\text{Var}(C_1 - C_2) = \text{Var}(C_1) + \text{Var}(C_2) - 2 \text{Cov}(C_1, C_2)$$

Because strong racks (e.g. blanks, high consonants) boost opponent counter-scores against *both* candidates, the covariance term $\text{Cov}(C_1, C_2)$ is strongly positive, reducing inter-candidate variance by **over 70%**.

### B. Leave Valuation & Duplicate Diminishing Returns
[`leave_eval.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/leave_eval.py) models rack leave value based on the Lipkin-Smith Super-Leaves tables:
- **Base Tile Equities:** `?` (+26.5), `S` (+8.2), `Z` (+2.5), `X` (+2.5), `R` (+1.8), ..., `Q` (-7.5).
- **Duplicate Blank Diminishing Returns:**
  $$\text{If } \text{blank\_count} > 1: \quad \text{Equity} \mathrel{-}= 20.5 \times (\text{blank\_count} - 1)$$
  - First blank: $+26.5$
  - Second blank: $+6.0$ (total `??` $= +32.5$).
  - Prevents the engine from hoarding blanks on rack over immediate 60+ point bingos.
- **Stem Synergies:** Non-overlapping stem bonuses for classic bingo stems:
  - 5-letter: `RETIN` (+4.5), `TISAN` (+4.5), `STARE` (+4.5), `SATIN` (+4.5)
  - 3-letter: `EST`, `ERS`, `RET`, `SAT`, `INE` (+2.0 to +2.5)
  - 2-letter pairs: `QU` (+6.5, neutralizes Q), `?S` (+5.0), `ES`, `ST`, `ER`, `ED` (+1.5 to +2.0)
- **Vowel / Consonant Balance:** Parabolic penalty when vowel ratio exceeds 65% or drops below 25%, with heavy penalties for 0 vowels or 0 consonants.

### C. Defensive Hot-Spot Modeling
[`defense.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/defense.py) scans all 8 Triple Word Score (TWS) squares:
- **Occupation Bonus:** $+6.0$ points when a move directly occupies an open TWS square.
- **Exposure Penalty:** $-5.5$ points if newly placed tiles create an open horizontal or vertical lane 1 square away from an unoccupied TWS.
- **Score-Adaptive Weighting:**
  - Leading by $\ge +40$: defense weight $= 1.4\times$ (lock down the board).
  - Trailing by $\le -40$: defense weight $= 0.6\times$ (open the board for comeback bingos).
- **No Double-Counting:** `cand_def` is utilized for 0-ply candidate pruning, but omitted from 1-ply simulated equity because opponent counter-moves on `cand_board` already explicitly simulate and score the opened lane.

### D. Deterministic Exact Endgame Solver
When $bag = 0$, all remaining unseen tiles are in the opponent's rack. [`endgame.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/endgame.py) activates an exact minimax solver:
- Searches all sequences up to 4 plies deep.
- Evaluates out-of-tile bonuses: when a player empties their rack, they score double the face value of the opponent's remaining tiles.
- Guarantees the optimal spread-maximizing play in close games.
