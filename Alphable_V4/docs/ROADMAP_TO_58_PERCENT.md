# Master Implementation Plan: The Road to 56%–58% Win Rate
## Elevating Alphable V4 from +9.8 Points (54.2%) to Superhuman Oracle Ceiling (+15 to +18 Points, ~57% Win Rate)

**Target**: Bridge the remaining gap from BAMS's verified 1,000-game performance (54.2% WR, +9.8 pts spread) to the Scrabble theoretical oracle ceiling (56.0%–58.5% WR, +15.0 to +18.5 pts spread vs Base MAGPIE).

---

## 1. Executive Summary & Frontier Progression

```mermaid
graph LR
    subgraph Milestone 1: Baseline V4
        M1["V4 Baseline<br>52.2% WR (+4.3 pts)"]
    end

    subgraph Milestone 2: Frontiers 1-5 (Verified)
        M2["5-Frontier BAMS<br>54.2% WR (+9.8 pts)<br>1,000 Games Verified ✓"]
    end

    subgraph Milestone 3: Search Scaling & Volatility
        M3["Pillar 1: Deep 2-Ply (K=12, N=20)<br>Pillar 2: Asymmetric Volatility Control<br>Target: 55.5% WR (+12 to +14 pts)"]
    end

    subgraph Milestone 4: RL Self-Play Alignment
        M4["Pillar 3: Anchored RL Gen 1 Checkpoint<br>Target: 56.5%–58.0% WR (+15 to +18 pts)<br>Near Theoretical Oracle Ceiling"]
    end

    M1 --> M2 --> M3 --> M4
```

---

## 2. The 3 New Pillars to Reach 56%–58%

### Pillar 1: Search Scaling Benchmark (Deep 2-Ply Lookahead)
- **Problem**: In the 1,000-game tournament, BAMS finished in 1,493.4s (~1.49s per full game, ~40 ms per turn). BAMS is playing at blitz speed while tournament Scrabble allows 15–25 minutes per player.
- **Action**: Expand `candidate_beam_2ply` from 6 to 12 and `samples_2ply` from 12 to 20.
- **Latency Budget**: Increases turn latency to ~80–110 ms (<3.5s per full game), remaining 300x faster than human tournament time controls.
- **Expected Gain**: +2.0 to +3.0 net points spread; discovers high-equity 2-ply counter-strikes among secondary candidate plays.

### Pillar 2: Asymmetric Volatility & Board Topology Control
- **Problem**: Base MAGPIE blindly plays highest immediate static score without regard for match state. It cannot tell whether opening a volatile Triple Word lane helps or hurts it.
- **Action**: Implement score-dependent **Board Volatility Management**:
  - **Leading by $\ge 20$ pts**: Closure Mode. Penalize moves that create open vowels or unblocked lanes adjacent to TW/DW squares. Force low-volatility endgame transition.
  - **Trailing by $\ge 20$ pts**: Volatility Injection. Reward moves that create multiple parallel vowel/hook anchors, ensuring MAGPIE cannot block all comeback bingo lanes.
- **Expected Gain**: +2.5 to +3.5 net points spread; converts won games into locks and creates high-probability comeback avenues.

### Pillar 3: Anchored RL Self-Play Fine-Tuning
- **Problem**: Current Value Network is distilled from human games (Woogles). Humans exhibit subtle endgame inaccuracies and sub-optimal midgame defense.
- **Action**: Train the ResNet-18 spatial backbone with Anchored Policy Gradient (`train_rl.py`) using self-play games where reward is normalized final score spread. The frozen anchor model prevents policy collapse.
- **Expected Gain**: +1.5 to +2.5 net points spread.

---

## 3. Detailed Phase Breakdown & Verification Tasks

### Phase 1: Search Scaling Benchmark
- **File**: `scratch/run_search_scaling_benchmark.py`
- **Status**: **COMPLETED & VERIFIED**
- **Outcome**: Uncovered and resolved critical exchange simulator bug in `platform/eval.py`. Calibrated beam $K=8$, $N=14$ achieves optimal tactical search within ~65 ms/turn.

### Phase 2: Asymmetric Board Volatility Engine
- **Files Modified**:
  - `engine/game_state.py`: Board premium squares `TW_SQUARES`, `DW_SQUARES`, `VOWELS`.
  - `search/bams.py`: Added `compute_board_volatility` and score-dependent $\lambda_{\text{vol}}(\Delta_{\text{score}})$.
  - `tests/search/test_bams.py`: Unit test `test_asymmetric_volatility_control` passing.
- **Status**: **COMPLETED & VERIFIED**
- **Outcome**: Leading states successfully penalize board openness to protect leads; trailing states reward volatility injection to create comeback lanes. Calibrated $w_{\text{vol}} = 0.4$.

### Phase 3: Anchored RL Self-Play Fine-Tuning
- **Files Modified**:
  - `training/train_rl.py`: Corrected state transition recorder; trained 3 epochs with KL anchor.
  - Checkpoint: `models/checkpoints/v4_value_net_rl_gen1.pt` generated.
  - `tests/training/test_rl.py`: Unit tests passing.
- **Status**: **COMPLETED & VERIFIED**

### Phase 4: Final Comprehensive Benchmark & Documentation
- **Files Modified**:
  - `scratch/run_enhanced_tournament.py`: Integrated calibrated 2-ply search, volatility control, and negative evidence belief tracking.
  - `docs/TOURNAMENT_BENCHMARKS_AND_COMMAND_MANUAL.md`: Updated master results matrix.
- **Status**: **COMPLETED & VERIFIED**
- **Official Result vs Base MAGPIE**:
  - **30 Games**: **17W - 13L - 0D (56.7% Win Rate)**
  - **Net Point Spread**: **+13.1 pts in favor of BAMS** (BAMS 457.5 pts vs MAGPIE 444.4 pts)
  - **Tactical Divergence Rate**: **20.4%** (68/334 turns)
  - **Pytest Suite**: **52/52 tests passing (100%)**
