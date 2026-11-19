# Testing and Verification Guide

This guide describes how to run tests, verify feature specifications, execute paired duplicate tournaments, evaluate game-phase telemetry, and audit statistical benchmarks in Alphable.

---

## 1. Quick Reference & Authoritative Commands

All commands assume an active virtual environment:

```bash
source venv/bin/activate
```

| Task | Command | Typical Runtime | Purpose |
| :--- | :--- | :--- | :--- |
| **All Automated Tests** | `pytest tests/ visualizer/tests/ -q` | ~20 seconds | Full unit, integration, and E2E regression check (196 tests). |
| **Opaque-Box E2E Suite** | `CUDA_VISIBLE_DEVICES="" python3 -m pytest tests/e2e/ -v` | ~3 seconds | 4-tier requirement verification (87 tests covering Features 1–22). |
| **Statistical Audit Tests** | `pytest -m audit -v` | ~1 second | Verifies historical 10,000-game dataset math and metrics. |
| **Fast Verification** | `./scripts/reproduce_benchmarks.sh --verify` | <1 second | Recalculates paper tables from raw tournament JSON. |
| **Live Smoke Match** | `./scripts/reproduce_benchmarks.sh --smoke-test` | ~1 minute | Plays a 4-game duplicate match between engines. |
| **Custom Tournament** | `./scripts/reproduce_benchmarks.sh --run-tournament 20` | ~5 minutes | Runs 20 games (10 duplicate pairs) via CLI. |

### Authoritative Test Commands

To run the complete test suite across all subsystems:

```bash
CUDA_VISIBLE_DEVICES="" PYTHONPATH=./venv/lib/python3.11/site-packages:. python3 -m pytest tests/ -v
```

To run only the opaque-box end-to-end verification suite:

```bash
CUDA_VISIBLE_DEVICES="" PYTHONPATH=./venv/lib/python3.11/site-packages:. python3 -m pytest tests/e2e/ -v
```

---

## 2. Test Architecture & Methodology

Alphable implements a 4-tier requirements-driven test engineering methodology designed for rigorous opaque-box verification, adversarial auditing, and scientific defense. The test suite applies four formal verification frameworks across all system features:

1. **Category-Partition Testing**: Systematic decomposition of the input domain into disjoint equivalence classes (valid, invalid, boundary, corner) with explicit constraint filtering.
2. **Boundary Value Analysis (BVA)**: Stress testing of domain extremities, including zero-tile states, single-tile thresholds, maximum rack constraints, score extrema, and grid coordinate limits (1–15, A–O).
3. **Pairwise Combinatorial Testing**: Orthogonal array sampling across multi-dimensional feature configurations (for example, BAMS search depth $\times$ Bayesian belief states $\times$ volatility weights $\times$ duplicate tournament modes) to detect interaction anomalies.
4. **Real-World Workload Testing**: Full execution of multi-game duplicate match series, Paired Student's t-test hypothesis verification, Two-Proportion z-tests, Wilson score interval validation, and game transcript replaying.

### Test Design Principles

1. **Isolation & Independence**: Every test instantiates fresh state instances or relies on shared session-scoped engine wrappers with automatic cleanup. Tests can run in any order without state leakage.
2. **Deterministic CRN Verification**: Bitwise determinism across identical seeds and divergence across varying seeds are validated without relying on wall-clock timing or external network resources.
3. **Formal Mathematical Verification**: Statistical validation formulas for Paired Student's t-test, Two-Proportion z-test, and Wilson 95% Score Intervals are tested against exact mathematical ground truth.
4. **Physical Tile Bag Conservation**: Strict enforcement of physical Scrabble bag limits (such as a maximum of 2 blanks) ensures that impossible physical states are rejected as expected.

---

## 3. Test Suite Organization & Summary

The repository test directory is organized into four primary functional packages and the end-to-end tier suite:

```
tests/
├── e2e/                        # End-to-end integration tiers (87 tests)
│   ├── conftest.py             # Shared fixtures and game generators
│   ├── test_e2e_tier1_engine.py      # Tier 1: Core C engine, ctypes memory, Move parsing, GameState
│   ├── test_e2e_tier1_search.py      # Tier 1: BAMS search, 2-ply rollouts, CRN determinism, volatility
│   ├── test_e2e_tier1_tournament.py  # Tier 1: Match simulation, bag conservation, Woogles protocol, telemetry
│   ├── test_e2e_tier1_analysis.py    # Tier 1: CLI analysis, model registry, teacher-student distillation
│   ├── test_e2e_tier2_boundaries.py  # Tier 2: Boundary & Corner Cases (empty bag, single tile, coordinate limits)
│   ├── test_e2e_tier3_combinations.py# Tier 3: Cross-Feature Combinations (BAMS + Belief + Duplicate Tournament)
│   └── test_e2e_tier4_workloads.py   # Tier 4: Real-World Workloads (reproducible matches, t-test, z-test)
│
├── engine/                     # Core engine unit tests
│   ├── test_bug_fixes.py       # Regressions for ctypes memory, coordinates, sign bugs
│   ├── test_game_state.py      # CGP round-trip, board tensors, move generation
│   └── test_magpie_parity.py   # Move generation equivalence against native MAGPIE
│
├── models/                     # Deep learning tensor tests
│   ├── test_compiled_inference.py # TorchScript loading and numerical parity
│   └── test_models.py          # ValueNetwork, BeliefNetwork, Dirichlet-multinomial sampling
│
├── platform/                   # CLI, platform, and tournament runner tests
│   ├── test_audit.py           # Statistical audit verification
│   ├── test_checkpoint.py      # Tournament checkpoint resumption and corruption handling
│   ├── test_cli.py             # Command-line parser and presets
│   ├── test_cli_parallel.py    # Parallel tournament flags
│   ├── test_eval.py            # Platform simulation and Woogles protocol formatting
│   └── test_parallel_tournament.py # Parallel worker coordination
│
└── search/                     # Tree search algorithm tests
    ├── test_bams.py            # Volatility control, beam pruning, and 2-ply returns
    └── test_native_solvers.py  # PAT candidate generation and C PIMC move selection
```

### E2E Test Suite Summary

| Test Module | Tier | Scope | Total Tests | Passed | Failed | Skipped | Runtime |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| `tests/e2e/test_e2e_tier1_engine.py` | Tier 1 | Core C engine, ctypes memory, Move parsing, GameState representations | 20 | 20 | 0 | 0 | 0.06s |
| `tests/e2e/test_e2e_tier1_search.py` | Tier 1 | BAMS search, 2-ply rollouts, CRN determinism, volatility, parity logic | 15 | 15 | 0 | 0 | 1.35s |
| `tests/e2e/test_e2e_tier1_tournament.py` | Tier 1 | Match simulation, bag conservation, Woogles protocol, telemetry | 12 | 12 | 0 | 0 | 0.08s |
| `tests/e2e/test_e2e_tier1_analysis.py` | Tier 1 | CLI registry, presets, throughput latency, teacher-student distillation | 9 | 9 | 0 | 0 | 0.47s |
| `tests/e2e/test_e2e_tier2_boundaries.py` | Tier 2 | Empty bag, single tile, pass chains, coordinate bounds, adversarial racks | 17 | 17 | 0 | 0 | 0.04s |
| `tests/e2e/test_e2e_tier3_combinations.py` | Tier 3 | BAMS + Belief tracking, dynamic beam + volatility, duplicate luck cancellation | 6 | 6 | 0 | 0 | 0.64s |
| `tests/e2e/test_e2e_tier4_workloads.py` | Tier 4 | Paired t-test, z-test, Wilson intervals, duplicate simulations, GCG replayer | 8 | 8 | 0 | 0 | 0.35s |
| **Total E2E Suite** | **Tiers 1–4** | **Comprehensive Opaque-Box Coverage** | **87** | **87** | **0** | **0** | **2.55s** |

### Targeted Test Execution with Pytest Markers

Markers configured in `pyproject.toml` allow selective test execution:

```bash
# Run unit tests
pytest -m unit

# Run end-to-end integration tiers
pytest -m e2e

# Run statistical audit tests
pytest -m audit
```

---

## 4. 22-Feature Specification & Verification Matrix

The 22 features documented in `docs/PROJECT_CONTEXT.md` map to the following verification requirements and tests:

| Feature # | Feature Name | Category Partition Classes & Extremities | Authoritative Oracle & Requirement | Test File Mapping | Status |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **F-01** | C Memory Management | 0-byte strings, 64KB buffers, rapid sequential commands | C `libmagpie.so` `magpie_free_string` verification; address non-leakage | `tests/e2e/test_e2e_tier1_engine.py` | VERIFIED |
| **F-02** | Pre-Endgame Parity Logic | Bag count $\in [1, 5]$, empty bag (0), tiles played = bag count | Pre-endgame specification in `bams.py:493`; bag-emptying parity bonus ($+2.0$) | `tests/e2e/test_e2e_tier1_search.py` | VERIFIED |
| **F-03** | Woogles Protocol Formatting | Pass move (0 letters), exchange 1 tile, exchange 7 tiles, bingo | Official Woogles.io action specification (`action: play`, `pass`, `exchange`) | `tests/e2e/test_e2e_tier1_tournament.py` | VERIFIED |
| **F-04** | Continuous Volatility Control | Trailing ($\Delta < -20$), Balanced ($\Delta \in [-20, +20]$), Leading ($\Delta > +20$) | Mathematical continuity constraint: $\lim_{\Delta \to 20^-} \lambda(\Delta) = \lim_{\Delta \to 20^+} \lambda(\Delta)$ | `tests/e2e/test_e2e_tier1_search.py` | VERIFIED |
| **F-05** | Strict Coordinate Parsing | Min row 1, max row 15, col A, col O, invalid (0A, 16A, P1, 8P) | Scrabble standard 15x15 notation; raises `ValueError` on out-of-bounds | `tests/e2e/test_e2e_tier1_engine.py`, `tests/e2e/test_e2e_tier2_boundaries.py` | VERIFIED |
| **F-06** | Tournament Runner Sign Fix | P1 first (even games), P1 second (odd games), duplicate pairs | Symmetrical margin rule: $P1 - P2 = -(P2 - P1)$; win count invariant to seat | `tests/e2e/test_e2e_tier1_tournament.py`, `tests/e2e/test_e2e_tier4_workloads.py` | VERIFIED |
| **F-07** | Game-Phase Telemetry | Opening (turns 1–5), Midgame (bag > 14), Pre-endgame (1–14), Endgame (0) | `docs/PROJECT_CONTEXT.md § Interface Contracts`; telemetry tags per move | `tests/e2e/test_e2e_tier1_tournament.py` | VERIFIED |
| **F-08** | Statistical Hypothesis Testing | Sample size $N \in [10, 100, 3000, 10000]$, $\alpha = 0.05, 0.01$ | Formal equations in `docs/explanation/STATISTICAL_SIGNIFICANCE_AND_BENCHMARKING_GUIDE.md`; `scipy.stats` reference | `tests/e2e/test_e2e_tier4_workloads.py` | VERIFIED |
| **F-09** | Game-Phase Sensitivity Audit | Win rate and score spread contribution per phase | Mathematical sum of phase deltas equals total game margin | `tests/e2e/test_e2e_tier4_workloads.py` | VERIFIED |
| **F-10** | CRN Variance Reduction | Identical seed $S$ vs different seed $S'$, sample count $N \in [8, 16, 24]$ | Mathematical proof $\text{Var}(X - Y) = \sigma_X^2 + \sigma_Y^2 - 2\text{Cov}(X, Y) < \sigma_X^2 + \sigma_Y^2$ | `tests/e2e/test_e2e_tier1_search.py`, `tests/e2e/test_e2e_tier3_combinations.py` | VERIFIED |
| **F-11** | First-Order Luck Cancellation | Duplicate pair: Game A (P1 first, seed $S$) + Game B (P2 first, seed $S$) | Algebraic cancellation: $L(\sigma_1) - L(\sigma_2) = 0$ for identical tile sequence | `tests/e2e/test_e2e_tier3_combinations.py`, `tests/e2e/test_e2e_tier4_workloads.py` | VERIFIED |
| **F-12** | Base MAGPIE Ceiling Audit | Static 1-ply KLV, PAT (`-pat CSW24`), PlayChooser simulation | Native C MAGPIE engine capabilities in `vendor/magpie/src/impl/` | `tests/e2e/test_e2e_tier1_engine.py` | VERIFIED |
| **F-13** | Tuned MAGPIE Benchmark | Default Base MAGPIE vs Tuned Base MAGPIE vs Alphable V4 | Empirical benchmark tournament output matching Table 1 schema | `tests/e2e/test_e2e_tier1_tournament.py` | VERIFIED |
| **F-14** | Generator Enhancement Transfer | Candidate beam expansion, PAT-guided candidate ranking | Candidate pool quality and top-move equity monotonic improvement | `tests/e2e/test_e2e_tier1_search.py` | VERIFIED |
| **F-15** | Macondo Architectural Benchmark | BAMS 2-ply MCTS vs Macondo B* search and Quackle PIMC | Comparative architectural assessment in technical reports | `tests/e2e/test_e2e_tier1_analysis.py` | VERIFIED |
| **F-16** | Throughput & Depth Landscape | Batch size $B \in [1, 10, 100]$, latency budget $< 5.0$s (GPU $< 35$ms) | Empirical performance benchmarks in `tests/models/test_models.py` | `tests/e2e/test_e2e_tier1_analysis.py` | VERIFIED |
| **F-17** | Teacher-Student Relationship | Distillation formula: $v = 0.75 \cdot v_{\text{macondo}} + 0.25 \cdot v_{\text{outcome}}$ | Distillation pipeline in `alphable/training/macondo_distill.py` | `tests/e2e/test_e2e_tier1_analysis.py` | VERIFIED |
| **F-18** | Master Benchmark Tables | Production schema for Table 1 (Master), Table 2 (Ablations), Table 3 (Phase) | Column completeness, metric validity, confidence interval consistency | `tests/e2e/test_e2e_tier4_workloads.py` | VERIFIED |
| **F-19** | Complete Bug Remediation Log | Verification of fixes for BUG-01 through BUG-07 | Fixed component behavior matches specification without regressions | `tests/e2e/test_e2e_tier1_engine.py`, `tests/e2e/test_e2e_tier2_boundaries.py` | VERIFIED |
| **F-20** | Publication Defense Document | Complete evidence synthesis satisfying acceptance criteria | 100% test pass, statistical significance, comparative landscape | `tests/e2e/test_e2e_tier4_workloads.py` | VERIFIED |
| **F-21** | Opaque-Box E2E Test Suite | 4-tier test suite covering features 1–20 | 100% test execution and pass rate | All `tests/e2e/` test files | VERIFIED |
| **F-22** | Adversarial Hardening | Malformed CGP strings, extreme racks, adversarial layouts | Graceful rejection or safe fallback without segfaults or crash | `tests/e2e/test_e2e_tier2_boundaries.py` | VERIFIED |

---

## 5. Pre-Flight Verification & CI Checklist

Before opening a pull request or cutting a release, execute this verification sequence:

```bash
# 1. Clean unit, integration, and visualizer test pass
pytest tests/ visualizer/tests/ -q

# 2. Complete opaque-box E2E test verification
CUDA_VISIBLE_DEVICES="" PYTHONPATH=./venv/lib/python3.11/site-packages:. python3 -m pytest tests/e2e/ -v

# 3. Statistical audit check
pytest tests/platform/test_audit.py -v

# 4. Benchmark table telemetry recalculation
./scripts/reproduce_benchmarks.sh --verify

# 5. Paper compilation check
./scripts/build_paper.sh
```

All commands must exit with code 0.

---

## 6. Paired Duplicate Tournament Testing

Standard Scrabble evaluation suffers from high variance because single-game scores depend heavily on tile draws. Drawing two blanks and an S often creates a 100-point swing regardless of algorithm quality.

To isolate decision-making quality from tile draw luck, Alphable uses the **Paired Duplicate Match** protocol:

1. A match consists of two games played with the identical tile bag sequence.
2. In Game A, Player 1 moves first and Player 2 moves second.
3. In Game B, the seats swap: Player 2 plays first with the identical opening rack, and Player 1 plays second.
4. The pair differential is computed as:
   $$\Delta_{\text{pair}} = \frac{(S_{1, A} - S_{2, A}) + (S_{1, B} - S_{2, B})}{2}$$

Because both engines play both sides of every tile rack, seat advantage and tile luck cancel out algebraically. Common Random Numbers (CRN) reduces candidate estimation variance by 65% to 85%, meaning 50 duplicate pairs provide the statistical confidence of roughly 200 to 400 standard games.

---

## 7. Interpreting Statistical Outputs

When running tournaments or audits, Alphable reports three primary statistical metrics:

### 1. Paired Student's t-Test on Net Point Spread

Measures whether the mean point spread per game differs significantly from zero:

$$t = \frac{\bar{d}}{\text{SE}}, \quad \text{where } \text{SE} = \frac{s}{\sqrt{N}}$$

- $\bar{d}$: Sample mean spread per game (for example, $+7.06$ pts).
- $N$: Number of duplicate pairs.
- $p < 0.05$ indicates statistical significance. For publication standards, we target $p < 0.001$.

### 2. Two-Proportion Z-Test

Tests whether the observed win rate $\hat{p}$ differs significantly from a 50% neutral baseline ($p_0 = 0.50$):

$$Z = \frac{\hat{p} - 0.50}{\sqrt{0.25 / N}}$$

### 3. Wilson Score Confidence Intervals

Standard Wald intervals ($\hat{p} \pm 1.96 \sqrt{\hat{p}(1-\hat{p})/N}$) break down when win rates deviate from 50% or sample sizes are modest. We report Wilson 95% score intervals because they maintain accurate coverage probabilities without producing limits outside $[0, 1]$.

---

## 8. Game-Phase Sensitivity Instrumentation

Tournament game logs record score accumulation across four distinct phases:

1. **Opening:** Turns 1 through 5.
2. **Midgame:** Turn $>5$ and remaining bag $>14$ tiles.
3. **Pre-Endgame:** Remaining bag between $1$ and $14$ tiles.
4. **Endgame:** Remaining bag is zero tiles.

### How to Analyze Phase Telemetry

Match results save phase-by-phase point contributions in structured JSON telemetry:

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

This telemetry reveals whether an engine wins through early board scoring or late-game bag management. In Alphable V4, opening and midgame turns run at slight deficits ($-4.00$ pts total), while late-game bag parity and exact endgame lookahead generate a $+17.67$ point advantage.

---

## 9. Model vs. Model Tournament Benchmarking & Testing Levels

Codebase tests verify that functions execute cleanly and maintain state consistency. Verifying whether an AI model plays better Scrabble requires game-theoretic tournament testing.

Alphable provides a tournament engine with four operational testing tiers depending on runtime budget and required statistical power.

### The Four Tournament Testing Tiers

| Tier / Level | Game Count | Duplicate Pairs | Runtime | Recommended Use Case |
| :--- | :---: | :---: | :---: | :--- |
| **Level 1: Smoke Test** | 4 games | 2 pairs | ~45 seconds | Sanity check during development. Confirms move generation, C bindings, and value net inference communicate without errors. |
| **Level 2: Evaluation Benchmark** | 40 games | 20 pairs | ~8 minutes | Validation of algorithmic changes. Yields initial net spread and win-rate directionality. |
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
| **`v3-transformer`** | None | Alphable V3 SmolLM2-135M Autoregressive Transformer candidate ranker | Legacy HuggingFace |
| **`greedy`** | None | Score-greedy baseline (picks move with highest immediate score) | Heuristic Baseline |

---

### Running Alphable V4 Hybrid PIMC vs. Tuned MAGPIE

To benchmark the Hybrid PIMC engine against Tuned MAGPIE across testing levels:

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

> **Note on `--duplicate`**: Always include `--duplicate`. Without this flag, games alternate seats but draw from unseeded random bags, reintroducing tile-draw variance and tripling the sample size required for statistical significance.

---

## 10. Inspecting and Comparing Match Telemetry

Every tournament automatically persists structured telemetry to `data/tournaments/`:

- JSON detail file: `data/tournaments/run_<timestamp>_<p1>_vs_<p2>_<N>g_dup.json`
- Historical ledger: `data/tournaments/tournament_history.jsonl`

### View Past Tournament Records

```bash
# Display the historical ledger of all tournaments run on this machine
python cli.py history
```

### Compare Two Specific Tournament Runs Side-by-Side

```bash
# Compare two tournament runs by their run IDs:
python cli.py history --compare run_20261109_tuned_ceiling run_20261112_103230
```

This comparison displays win rate, score differential, bingo frequency, and phase-by-phase net spread side by side to quantify where performance changed between engine configurations.
