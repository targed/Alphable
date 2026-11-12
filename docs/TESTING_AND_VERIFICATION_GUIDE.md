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
