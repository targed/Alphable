# Testing and Verification Guide

This guide describes how to run tests, execute paired duplicate tournaments, evaluate game-phase telemetry, and verify statistical benchmarks in Alphable.

---

## 1. Quick Reference

All commands assume an active virtual environment:

```bash
source venv/bin/activate
```

| Task | Command | Typical Runtime | Purpose |
| :--- | :--- | :--- | :--- |
| **All Automated Tests** | `pytest tests/ visualizer/tests/ -q` | ~20 seconds | Full unit, integration, and E2E regression check (189 tests). |
| **E2E Tier Tests** | `pytest tests/e2e/ -v` | ~10 seconds | End-to-end game, search, and boundary validation. |
| **Statistical Audit Tests** | `pytest -m audit -v` | ~1 second | Verifies historical 10,000-game dataset math and metrics. |
| **Fast Verification** | `./scripts/reproduce_benchmarks.sh --verify` | <1 second | Recalculates paper tables from raw tournament JSON. |
| **Live Smoke Match** | `./scripts/reproduce_benchmarks.sh --smoke-test` | ~1 minute | Plays a 4-game duplicate match between engines. |
| **Custom Tournament** | `./scripts/reproduce_benchmarks.sh --run-tournament 20` | ~5 minutes | Runs 20 games (10 duplicate pairs) via CLI. |

---

## 2. Why Paired Duplicate Testing Matters

Standard Scrabble evaluation suffers from high variance because single-game scores depend heavily on tile draws. Drawing two blanks and an S often creates a 100-point swing regardless of algorithm quality. 

To measure pure decision-making quality, Alphable uses the **Paired Duplicate Match** protocol:

1. A match consists of two games played with the identical tile bag sequence.
2. In Game A, Player 1 moves first and Player 2 moves second.
3. In Game B, the seats swap: Player 2 plays first with the identical opening rack, and Player 1 plays second.
4. The pair differential is computed as:
   $$\Delta_{\text{pair}} = \frac{(S_{1, A} - S_{2, A}) + (S_{1, B} - S_{2, B})}{2}$$

Because both engines play both sides of every tile rack, seat advantage and tile luck cancel out algebraically. In our experiments, Common Random Numbers (CRN) reduces candidate estimation variance by 65% to 85%. That means 50 duplicate pairs provide the statistical confidence of roughly 200 to 400 standard games.

---

## 3. Test Suite Organization

The test directory is organized into four main layers:

```
tests/
├── e2e/                        # End-to-end integration tiers
│   ├── conftest.py             # Shared fixtures and game generators
│   ├── test_e2e_tier1_engine.py      # Core C-bindings and board mechanics
│   ├── test_e2e_tier1_search.py      # BAMS 2-ply candidate rollouts
│   ├── test_e2e_tier1_tournament.py  # Tournament runner execution
│   ├── test_e2e_tier1_analysis.py    # Position analysis CLI logic
│   ├── test_e2e_tier2_boundaries.py  # Zero-bag, pass sequences, edge coordinates
│   ├── test_e2e_tier3_combinations.py# Belief updates paired with value net
│   └── test_e2e_tier4_workloads.py   # Multi-game runs and memory checks
│
├── engine/                     # Core engine unit tests
│   ├── test_bug_fixes.py       # Regressions for ctypes memory, coordinates, sign bugs
│   ├── test_magpie_bindings.py # ctypes C ABI wrappers
│   └── test_magpie_parity.py   # Move generation equivalence tests
│
├── models/                     # Deep learning tensor tests
│   ├── test_belief_net.py      # Bayesian Dirichlet-multinomial sampling
│   └── test_value_net.py       # ResNet-18 forward passes and tensor shapes
│
├── platform/                   # CLI and tournament runner tests
│   ├── test_audit.py           # Statistical audit verification
│   └── test_cli.py             # Command-line flags and argument parsing
│
└── search/                     # Tree search algorithm tests
    └── test_bams.py            # Volatility control, beam pruning, and 2-ply returns
```

### Running Specific Test Categories

Pytest markers allow targeted execution:

```bash
# Run only fast unit tests
pytest -m unit

# Run only end-to-end integration tiers
pytest -m e2e

# Run only statistical audit tests
pytest -m audit
```

---

## 4. Interpreting Statistical Outputs

When running tournaments or audits, Alphable reports several key metrics:

### 1. Paired Student's t-Test on Net Point Spread
Measures whether the mean point spread per game differs from zero:
$$t = \frac{\bar{d}}{\text{SE}}, \quad \text{where } \text{SE} = \frac{s}{\sqrt{N}}$$
- $\bar{d}$: Sample mean spread per game (e.g., $+7.06$ pts).
- $N$: Number of duplicate pairs.
- $p < 0.05$ indicates statistical significance. For publication standards, we target $p < 0.001$.

### 2. Two-Proportion Z-Test
Tests whether the win rate $\hat{p}$ differs from 50% ($p_0 = 0.50$):
$$Z = \frac{\hat{p} - 0.50}{\sqrt{0.25 / N}}$$

### 3. Wilson Score Confidence Intervals
Standard Wald intervals ($\hat{p} \pm 1.96 \sqrt{\hat{p}(1-\hat{p})/N}$) break down when win rates are high or sample sizes are modest. We report Wilson 95% score intervals because they maintain accurate coverage probabilities without producing out-of-bounds limits.

---

## 5. Game-Phase Sensitivity Instrumentation

Tournament game logs record score accumulation across four distinct phases:

1. **Opening:** Turns 1 through 5.
2. **Midgame:** Turn $>5$ and remaining bag $>14$ tiles.
3. **Pre-Endgame:** Remaining bag between $1$ and $14$ tiles.
4. **Endgame:** Remaining bag is zero tiles.

### How to Analyze Phase Telemetry

Match results save phase-by-phase point contributions in their JSON telemetry:

```python
import json

with open("data/tournaments/run_example.json") as f:
    data = json.load(f)

# Each record contains phase scores for both players
for pair in data["details"][:5]:
    print(f"Pair {pair['pair']}:")
    print(f"  Pre-Endgame Net: {pair['phase_scores_p1']['pre_endgame'] - pair['phase_scores_p2']['pre_endgame']} pts")
    print(f"  Endgame Net:     {pair['phase_scores_p1']['endgame'] - pair['phase_scores_p2']['endgame']} pts")
```

This telemetry reveals whether an engine wins through early board scoring or late-game bag management. In Alphable V4, early turns run at slight deficits ($-4.00$ pts across opening and midgame), while late-game bag parity and exact endgame lookahead generate a $+17.67$ point advantage.

---

## 6. Continuous Integration & Sanity Checks

Before opening a pull request, run the following verification sequence:

```bash
# 1. Clean test pass
pytest tests/ visualizer/tests/ -q

# 2. Statistical audit check
pytest tests/platform/test_audit.py -v

# 3. Paper compilation check
./scripts/build_paper.sh
```

All commands must exit with code 0.

---

## 7. Model vs. Model Tournament Benchmarking & Testing Levels

Codebase tests (`pytest`) verify that functions execute without crashing, preserve state consistency, and respect memory bounds. However, verifying whether an AI model plays better Scrabble requires **game-theoretic tournament testing**.

Alphable provides a tournament engine with four operational testing tiers depending on your runtime budget and precision requirements.

### The Four Tournament Testing Tiers

| Tier / Level | Game Count | Duplicate Pairs | Runtime | Recommended Use Case |
| :--- | :---: | :---: | :---: | :--- |
| **Level 1: Smoke Test** | 4 games | 2 pairs | ~45 seconds | Sanity check during development. Confirms move generation, C bindings, and value net inference communicate without errors. |
| **Level 2: Evaluation Benchmark** | 40 games | 20 pairs | ~8 minutes | Quick validation of algorithmic changes. Yields initial net spread and win-rate directionality. |
| **Level 3: Statistical Benchmark** | 100–500 games | 50–250 pairs | 20–90 minutes | Detects moderate effect sizes ($\Delta \ge 5$ pts) with Wilson 95% confidence intervals ($\pm 4–8\%$). |
| **Level 4: Grandmaster Verification** | 1,000–10,000 games | 500–5,000 pairs | Multi-hour / Overnight | Publication-grade proof with narrow confidence intervals ($\pm 0.8$ pts) and $p < 10^{-15}$. |

---

### Available Model & Opponent Presets

Pass any of the following keys to `--model` (Player 1) or `--opponent` (Player 2):

| Preset Key | Aliases | Description | Engine Type |
| :--- | :--- | :--- | :--- |
| **`hybrid-pimc`** | `sota`, `pimc`, `v4-hybrid` | Native C PIMC simulation (~98k nps) + Cross-Attention Value Net re-ranking | Hybrid C/Neural (SOTA) |
| **`latest`** | `champion`, `calibrated` | Alphable V4 Champion 2-ply BAMS with neural value network and Bayesian belief tracking | Python / PyTorch BAMS |
| **`v4-pat`** | `champion-pat` | V4 Champion 2-ply BAMS with PAT-enhanced candidate generator | Python / PyTorch BAMS |
| **`5-frontiers`** | `frontier-v4` | Full 5-frontiers search (nested 2-ply, belief tracking, pre-endgame, endgame) | Python / PyTorch BAMS |
| **`rl-gen1`** | `rl` | V4 fine-tuned via self-play reinforcement learning | Python / PyTorch BAMS |
| **`magpie-tuned`** | `magpie-sim`, `tuned-magpie` | Maximally Tuned Base MAGPIE (`-pat CSW24`, C PIMC simulation, exact endgame) | Native C Benchmark |
| **`magpie`** | `base-magpie` | Default 1-ply Static KLV Base MAGPIE | Native C Baseline |
| **`v3-resnet`** | `v3` | Alphable V3 Macondo ResNet Champion (63 dims) | Legacy PyTorch |
| **`v3-transformer`** | — | Alphable V3 SmolLM2-135M Autoregressive Transformer candidate ranker | Legacy HuggingFace |
| **`greedy`** | — | Score-greedy baseline (picks move with highest immediate score) | Heuristic Baseline |

---

### Running Alphable V4 Hybrid PIMC vs. Tuned MAGPIE

To directly benchmark the new SOTA Hybrid PIMC engine against Tuned MAGPIE across differing testing levels:

#### Option A: Using the Automated Reproduction Script

```bash
# Level 1: Quick 4-game smoke test (~45 seconds)
./scripts/reproduce_benchmarks.sh --hybrid-smoke

# Level 2: Standard 40-game duplicate benchmark (~8 minutes)
./scripts/reproduce_benchmarks.sh --hybrid-vs-tuned 40

# Level 3: 100-game statistical tournament (~20 minutes)
./scripts/reproduce_benchmarks.sh --hybrid-vs-tuned 100
```

#### Option B: Using the Direct CLI (`cli.py`)

```bash
# Level 1: Smoke test (4 games / 2 duplicate pairs)
python cli.py tournament --model hybrid-pimc --opponent magpie-tuned --games 4 --duplicate

# Level 2: Standard evaluation (40 games / 20 duplicate pairs)
python cli.py tournament --model hybrid-pimc --opponent magpie-tuned --games 40 --duplicate

# Level 3: High-confidence benchmark (100 games / 50 duplicate pairs)
python cli.py tournament --model hybrid-pimc --opponent magpie-tuned --games 100 --duplicate

# Level 4: Deep statistical verification (1,000 games / 500 duplicate pairs)
python cli.py tournament --model hybrid-pimc --opponent magpie-tuned --games 1000 --duplicate
```

> **Note on `--duplicate`**: Always include `--duplicate`. Without this flag, games alternate seats but use random tile bags, reintroducing tile-draw luck and tripling the sample size required for statistical significance.

---

### 8. Inspecting and Comparing Match Telemetry

Every tournament automatically persists full structured telemetry to `data/tournaments/`:

- JSON detail file: `data/tournaments/run_<timestamp>_<p1>_vs_<p2>_<N>g_dup.json`
- Historical ledger: `data/tournaments/tournament_history.jsonl`

#### View Past Tournament Records
```bash
# Display the historical ledger of all tournaments run on this machine
python cli.py history
```

#### Compare Two Specific Tournament Runs Side-by-Side
```bash
# Compare two tournament runs by their run IDs:
python cli.py history --compare run_20261109_tuned_ceiling run_20261112_103230
```
This comparison displays win rate, score differential, bingo frequency, and phase-by-phase net spread side by side to quantify exactly where performance improved.
