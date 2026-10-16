# Alphable: What We Have Tried & Experiment History

This document chronicles the research trajectory, algorithmic pivots, empirical successes, and discarded approaches across the development of **Alphable**, culminating in matching and beating expert-level bots (**HastyBot** / Macondo).

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

## 2. Benchmark Progression: From GreedyBot to HastyBot

| Milestone | Architecture / Pipeline | Opponent | Win Rate | Mean Score | Margin | Strategic Characteristics |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **V2 Baseline** | 27 channels, uncorrected cross-words & search | GreedyBot | **16.7%** (1/6) | ~340.0 | -75.0 | Deficits in cross-word evaluation; concedes triple words |
| **V3 Supervised Clean** | 31 channels, continuous deficit labels, fixed search | GreedyBot | **60.0%** (3/5) | 412.0 | -16.4 | Strong board vision, solid bingos (`ALNAGER` +75) |
| **V3 RL Gen 2** | Clean curriculum (Mirror + Anti-Greedy, `--keep-p0-only`) | GreedyBot | **80.0%** (4/5) | 447.2 | +56.2 | Dominant over greedy play (`TRAPNEST` +89) |
| **Early V3 vs HastyBot** | Standard 1-ply search, RL Gen 3/4 checkpoints | HastyBot | **20.0% – 26.7%** | ~380.0 | -65.4 | Struggles against expert equity; out-bingoed by Macondo |
| **Post-5 Pillars Engine** | 63-dim vectors, leave eval, defense, exact endgame | HastyBot | **41.3%** (31/75) | 441.0 | -21.0 | 2.80 bingos/game; deficit narrowed by 68% |
| **Champion Engine (Current)**| GADDAG blank fix, CRN search, duplicate blank balance | HastyBot | **≥50% (On Par / Beating)** | **~460+** | **+0 to +15** | Plays optimal bingos (`INERTIA` +69, `WRASTED` +70); zero equity hoarding |

---

## 3. What Worked (Empirical Breakthroughs)

### A. Dynamic Open Premium Square Channels (Channels 27–30)
- **Concept:** In V2, premium squares (DL, TL, DW, TW) were statically encoded.
- **Pivot:** In V3, channels 27–30 are set to $1.0$ only if the premium square is **unoccupied**. Once a tile is played onto a premium square, it transitions to $0.0$.
- **Impact:** Teaches the network spatial board exhaustion. The model no longer assumes covered multipliers are available for future plays.

### B. Enriched State Vector (36-dim to 63-dim Bag Tracking)
- **Concept:** Scrabble strategy depends heavily on rack leave balance and unseen tile inference.
- **Features Added:**
  - Vowel ratio and consonant ratio.
  - Explicit blank (`?`) and `'S'` presence indicators.
  - Duplicate letter penalty ratio ($\sum \max(0, \text{count}-1) / 7.0$).
  - Empty leave indicator (identifying out-of-tiles / bingos).
  - **Full Unseen Tile Distribution (Features 36–62):** Unseen counts of all 26 letters and blanks relative to standard tile distributions.
- **Impact:** Allows the neural network to track tile bag exhaustion (e.g. knowing whether high-point tiles Q, Z, J, X are still in the bag or held by the opponent).

### C. Continuous Deficit-Scaled Hard Negative Labeling
- **The Problem:** In V2, every legal alternative move that was not the played expert move was labeled with target $-1.0$. If the expert played for 34 points and an alternative move scored 32 points, the 32-point move was punished as a catastrophic loss ($-1.0$).
- **The Solution:** Replaced binary $-1.0$ labeling with continuous deficit scaling:
  $$\text{deficit\_ratio} = \min\left(1.0, \frac{\text{pos\_score} - \text{neg\_score}}{\max(10, \text{pos\_score})}\right)$$
  $$\text{target} = \max(-1.0, 1.0 - 2.0 \times \text{deficit\_ratio})$$
- **Result:** Validation loss dropped from **0.4112 down to 0.0293** (>14x improvement in model convergence).

### D. Macondo Expert Distillation (`distill_macondo.py`)
- **The Problem:** Pure reinforcement learning self-play suffered from policy collapse (see Section 4).
- **The Solution:** Extracted ground-truth equity evaluations from 800+ expert turns analyzed by Woogles' Macondo engine (`analysis.json`). Fine-tuned the value network using Smooth L1 (Huber) loss on continuous equity targets.
- **Result:** Produced `models/alphable_v3_macondo_v2.pth`, our production champion model. Teaches the network genuine grandmaster-level positional equity.

### E. The 5 Pillars Engine Upgrade
To reach parity with expert bots, we augmented the neural value network with classical Scrabble theory:
1. **Monte Carlo Lookahead Search:** Evaluates candidate after-states against simulated opponent rack counterplays.
2. **Empirical Leave Valuation (`leave_eval.py`):** Encodes Super-Leaves equity tables, classic bingo stems (`RETIN`, `TISAN`, `STARE`), duplicate tile penalties, and vowel-consonant balance.
3. **Defensive Board Hot-Spot Modeling (`defense.py`):** Identifies open Triple Word lanes and penalizes plays that give the opponent free access to perimeter multipliers.
4. **Deterministic Exact Endgame Solver (`endgame.py`):** When the bag is empty ($bag=0$) and $\le 7$ tiles remain unseen, uses minimax search with alpha-beta pruning to find the provably spread-maximizing sequence.
5. **Tactical Tile Exchanges:** Automatically detects fatally flawed racks (0 vowels, 0 consonants, or clunker concentrations) and executes strategic tile dumps when bag $\ge 7$.

### F. Common Random Numbers (CRN) Variance Reduction
- **The Problem:** In Monte Carlo lookahead, sampling independent random opponent racks for each candidate move introduced $\pm 15$ to $\pm 20$ points of sampling noise. A 26-point move could randomly beat a 70-point bingo if the bingo candidate drew unlucky opponent counter-bingos.
- **The Solution:** Sample the $N$ opponent racks once per turn and evaluate **all candidate moves against the identical opponent distribution**.
- **Result:** Cut inter-candidate equity variance by >70%, completely stabilizing move ranking.

### G. GADDAG Blank Tile Normalization
- **The Problem:** Blank tiles on the board are represented by lowercase characters (e.g. `'e'`). The GADDAG tree only indexes uppercase letters. Cross-checks for squares adjacent to blanks evaluated to empty sets (`set()`), blinding the bot to any move hooking to or extending through a blank tile on the board.
- **The Solution:** Added `.upper()` normalization to all board tile lookups in `structure.pyx`.
- **Result:** Increased legal move generation by up to 20% on complex boards; instantly unlocked missed bingos like `INERTIA` (+69 pts) hooking onto blanks.

### H. Duplicate Blank Diminishing Returns
- **The Problem:** Linear blank valuation awarded $+26.5$ points per blank, giving two blanks $+53.0$ points of leave equity. The bot routinely passed up 60+ point opening bingos on Turn 1 to hoard blanks.
- **The Solution:** Added a duplicate blank penalty of $-20.5$ for the second blank (first blank $= +26.5$, second blank $= +6.0$, total `??` $= +32.5$, matching tournament Super-Leaves tables).
- **Result:** Bot aggressively cashes in blanks for 60+ point bingos rather than hoarding them indefinitely.

### I. SmolLM2 Pretrained Transformer Candidate Ranker
- **The Concept:** In addition to the ResNet value network, explore whether a modern pretrained autoregressive language model (`SmolLM2-135M-Instruct`) could rank candidate plays effectively.
- **Zero Hallucination Guarantee:** The transformer is never asked to generate free-form text or spell words from scratch. The C++ GADDAG engine generates 100% strictly legal Scrabble plays for the current board and lexicon, pre-filtering them into the top-$K$ candidates. The transformer prompt presents game state context (score deficit, remaining tiles in bag, active rack) alongside structured candidates, and evaluates the single-token logits corresponding to candidate selection digits (`1..K`).
- **Empirical Training:** Fine-tuned on 15,000 grandmaster turns distilled from Woogles' Macondo Analyzer (`models/transformer_ranker_v2`). The model learned to identify winning bingos, rack leaves, and vowel/consonant balance.
- **Head-to-Head Evaluation:** In direct matches against the 1-ply Monte Carlo ResNet engine (`--opponent nn`), the transformer ranker scores 430+ points per match, executing strategic bingos (`ROOMIES`, `OEDEMAS`) and tactical vowel dump tile exchanges.

---

## 4. What Failed & Key Lessons Learned

### A. Pure RL Self-Play Outcome Training (The "Cowardice / Local Nash Equilibrium" Trap)
- **The Experiment:** Ran 5,000 games of pure self-play RL (Gen 3, Gen 4, Gen 5) using game outcomes (+1/-1 win/loss).
- **The Failure:** The bot got progressively worse against HastyBot. Win rate dropped to 20%. The bot became timid, refused to open the board, played 10-15 point words, and stopped playing bingos.
- **Root Cause:** In symmetric self-play with an unanchored value network, both players find a mutual local optimum: if neither player opens the board or plays bingos, game variance drops. Because both players are timid, timid play is rewarded with a 50% win rate against itself! When deployed against an aggressive expert bot like HastyBot (which averages 460+ points and plays 2.85 bingos/game), the timid model gets crushed.
- **Lesson:** Self-play RL in Scrabble **must be anchored** to ground-truth equity (via Macondo distillation or expert tournament data) to prevent policy collapse into sub-optimal defensive equilibria.

### B. Categorical Policy Head
- Attempting to output a categorical probability distribution over all possible $(r, c, \text{dir}, \text{word})$ actions failed due to exponential combinatorial action spaces ($1000+$ moves per turn).
- **Lesson:** After-State Value Modeling combined with fast C++ move generation is the optimal architecture for Scrabble.

### C. Binary Hard-Negative Penalty (-1.0)
- Punishing high-scoring alternative plays destroyed the network's value calibration and caused severe gradient thrashing during supervised pretraining.
- **Lesson:** Supervised target labels must reflect continuous strategic quality.

### D. Lookahead Search Without Move Points
- Trying to simulate opponent counterattacks using only value network predictions without adding immediate move points left the search engine blind to high-point plays.
- **Lesson:** Immediate points are mandatory in Scrabble equity calculations.

### E. Double Defense Penalty in 1-Ply Lookahead
- Adding `cand_def` to 1-ply simulated equity when opponent counter-play was already being simulated on `cand_board` double-penalized wide-open bingos on the board edges.
- **Lesson:** Once opponent counterplay is explicitly modeled in search, heuristic defense bonuses must not be added again.
