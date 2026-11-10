# Alphable V4 Comprehensive Test Infrastructure & Methodology (TEST_INFRA)

## 1. Test Architecture & Methodology

The Alphable V4 Test Infrastructure implements a 4-tier requirements-driven test engineering methodology designed for rigorous opaque-box verification, adversarial auditing, and scientific defense. The test suite applies four formal verification frameworks across all system features:

1. **Category-Partition Testing**: Systematic decomposition of the input domain into disjoint equivalence classes (valid, invalid, boundary, corner) with explicit constraint filtering.
2. **Boundary Value Analysis (BVA)**: Stress testing of domain extremities, including zero-tile states, single-tile thresholds, maximum rack constraints, score extrema, and grid coordinate limits (1-15, A-O).
3. **Pairwise Combinatorial Testing**: Orthogonal array sampling across multi-dimensional feature configurations (e.g., BAMS search depth $\times$ Bayesian belief states $\times$ volatility weights $\times$ duplicate tournament modes) to detect unexpected interaction anomalies.
4. **Real-World Workload Testing**: Full end-to-end execution of multi-game duplicate match series, Paired Student's t-test hypothesis verification, Two-Proportion z-tests, Wilson score interval validation, and game transcript replaying.

---

## 2. Feature Inventory & Test Specification Matrix (Features 1–22)

The 22 features enumerated in `PROJECT.md § Feature Inventory` are systematically partitioned and mapped to authoritative expected outputs:

| Feature # | Feature Name | Category Partition Classes | Boundary Values (BVA) | Pairwise Combinations | Authoritative Oracle | E2E Test Mapping |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **F-01** | C Memory Management | Valid command string, empty command, multiline output, error string | 0-byte string, 64KB output buffer, rapid sequential commands | Ctypes wrapper $\times$ multiple `MagpieEngine` instances $\times$ error triggers | C `libmagpie.so` `magpie_free_string` verification; address non-leakage | `tests/e2e/test_e2e_tier1_engine.py` |
| **F-02** | Pre-Endgame Parity Logic | `tiles_placed` evaluation, bag $\in [1, 5]$, parity tempo bonus | Bag count = 1, bag count = 5, empty bag (0), tiles played = bag count | Pre-endgame solver $\times$ Q without U $\times$ blank tile hazard | Pre-endgame specification in `bams.py:493`; bag-emptying parity bonus ($+2.0$) | `tests/e2e/test_e2e_tier1_search.py` |
| **F-03** | Woogles Protocol Formatting | Placement play, pass play (`pass` / `--`), exchange play (`exchange [TILES]`) | Pass move (0 letters), exchange 1 tile, exchange 7 tiles, bingo placement | Woogles bot agent $\times$ pass $\times$ exchange $\times$ challenge modes | Official Woogles.io action specification (`action: play`, `pass`, `exchange`) | `tests/e2e/test_e2e_tier1_tournament.py` |
| **F-04** | Continuous Volatility Control | Trailing ($\Delta < -20$), Balanced ($\Delta \in [-20, +20]$), Leading ($\Delta > +20$) | $\Delta \in \{-21, -20, -19, 0, +19, +20, +21\}$ | Volatility weight $w \in [0.0, 1.0] \times$ leading/trailing $\times$ open/closed boards | Mathematical continuity constraint: $\lim_{\Delta \to 20^-} \lambda(\Delta) = \lim_{\Delta \to 20^+} \lambda(\Delta)$ | `tests/e2e/test_e2e_tier1_search.py` |
| **F-05** | Strict Coordinate Parsing | Across (`8H`, `15A`), Down (`H8`, `A15`), Invalid strings (`0A`, `16A`, `P1`, `8P`) | Row 1 (min), Row 15 (max), Col A (min), Col O (max), Row 0, Row 16 | Coordinate format $\times$ direction $\times$ grid limits | Scrabble standard 15x15 notation; raise `ValueError` on out-of-bounds | `tests/e2e/test_e2e_tier1_engine.py`, `tests/e2e/test_e2e_tier2_boundaries.py` |
| **F-06** | Tournament Runner Sign Fix | P1 first (even games), P1 second (odd games), duplicate pair mode | Score margin = 0, positive margin, negative margin, large blowouts | Alternating seat tournament $\times$ duplicate mode $\times$ custom seeds | Symmetrical margin rule: $P1 - P2 = -(P2 - P1)$; win count invariant to seat | `tests/e2e/test_e2e_tier1_tournament.py`, `tests/e2e/test_e2e_tier4_workloads.py` |
| **F-07** | Game-Phase Telemetry | Opening (turns 1-5), Midgame (bag > 14), Pre-endgame (bag 1-14), Endgame (bag 0) | Turn 5/6 transition, Bag 15/14 transition, Bag 1/0 transition | Game phase $\times$ turn count $\times$ remaining bag count | `PROJECT.md § Interface Contracts`; telemetry tags per move record | `tests/e2e/test_e2e_tier1_tournament.py` |
| **F-08** | Statistical Hypothesis Testing | Paired two-tailed t-test, two-proportion z-test, Wilson 95% score interval | Sample size $N \in [10, 100, 3000, 10000]$, $p$-value threshold $\alpha = 0.05, 0.01$ | Significance level $\times$ paired vs unpaired $\times$ win proportions | Formal mathematical equations in `survey_3/handoff.md`; `scipy.stats` reference | `tests/e2e/test_e2e_tier4_workloads.py` |
| **F-09** | Game-Phase Sensitivity Audit | Win-rate and score spread contribution per phase (opening, midgame, pre, end) | Phase boundaries, games ending early by 6 consecutive passes | Move phase $\times$ margin contribution $\times$ duplicate game matching | Mathematical sum of phase deltas equals total game margin | `tests/e2e/test_e2e_tier4_workloads.py` |
| **F-10** | CRN Variance Reduction | Common Random Numbers vs independent random seeds for opponent rack sampling | Identical seed $S$, different seed $S'$, sample count $N \in [8, 16, 24]$ | CRN mode $\times$ candidate beam $\times$ rack leave variations | Mathematical proof $\text{Var}(X - Y) = \sigma_X^2 + \sigma_Y^2 - 2\text{Cov}(X, Y) < \sigma_X^2 + \sigma_Y^2$ | `tests/e2e/test_e2e_tier1_search.py`, `tests/e2e/test_e2e_tier3_combinations.py` |
| **F-11** | First-Order Luck Cancellation | Duplicate pair match: Game A (P1 first, Seed S) + Game B (P2 first, Seed S) | Spread delta $D_{\text{pair}} = (S_{1A} + S_{1B}) - (S_{2A} + S_{2B})$ | Player skill differential $\times$ tile draw sequence $\times$ seat position | Theorem 1: $L(\sigma_1) - L(\sigma_2) = 0$ for identical tile sequences | `tests/e2e/test_e2e_tier3_combinations.py`, `tests/e2e/test_e2e_tier4_workloads.py` |
| **F-12** | Base MAGPIE Ceiling Audit | Static 1-ply KLV, Positional Adjustment Term (PAT), PlayChooser simulation | `-pat CSW24`, `-numplays 100`, `-maxnumdplays 100`, `-wmp` | Command-line options $\times$ lexicon $\times$ lookahead depth | Native C MAGPIE engine capabilities in `vendor/magpie/src/impl/` | `tests/e2e/test_e2e_tier1_engine.py` |
| **F-13** | Tuned MAGPIE Benchmark | Default Base MAGPIE vs Tuned Base MAGPIE vs Alphable V4 | Candidate beam $K \in [5, 10, 20]$, search time limits | Engine configuration $\times$ opponent policy $\times$ duplicate format | Empirical benchmark tournament output matching Table 1 schema | `tests/e2e/test_e2e_tier1_tournament.py` |
| **F-14** | Generator Enhancement Transfer | MAGPIE candidate generator enhancements transferring to BAMS candidate pool | Candidate beam expansion, PAT-guided candidate ranking | Move generator parameter $\times$ BAMS search pipeline | BAMS candidate pool quality and top-move equity monotonic improvement | `tests/e2e/test_e2e_tier1_search.py` |
| **F-15** | Macondo Architectural Benchmark | BAMS 2-ply MCTS vs Macondo B* search and Quackle PIMC | Tree search depth, candidate evaluation throughput, memory footprint | Search algorithm $\times$ inference type $\times$ evaluation backend | Diátaxis comparative architectural assessment in `survey_3/handoff.md` | `tests/e2e/test_e2e_tier1_analysis.py` |
| **F-16** | Throughput & Depth Landscape | Search throughput (nodes/sec), GPU batch latency, decision time | Batch size $B \in [1, 10, 100]$, latency budget $< 5.0$s (GPU batch $< 35$ms) | Batch size $\times$ device (CPU/GPU) $\times$ candidate count | Empirical performance benchmarks in `tests/models/test_models.py` | `tests/e2e/test_e2e_tier1_analysis.py` |
| **F-17** | Teacher-Student Relationship | Distillation target formula: $v = 0.75 \cdot v_{\text{macondo}} + 0.25 \cdot v_{\text{outcome}}$ | Macondo equity $\pm 100$, outcome margin $\pm 200$, loss bounds | Distillation dataset $\times$ target normalization $\times$ MSE/Huber loss | Distillation pipeline in `alphable_v4/training/macondo_distill.py` | `tests/e2e/test_e2e_tier1_analysis.py` |
| **F-18** | Master Benchmark Tables | Production schema for Table 1 (Master), Table 2 (Ablations), Table 3 (Phase) | Column completeness, metric validity, confidence interval consistency | Model preset $\times$ opponent type $\times$ tournament mode | Publication reporting requirements from `ORIGINAL_REQUEST.md § R5` | `tests/e2e/test_e2e_tier4_workloads.py` |
| **F-19** | Complete Bug Remediation Log | Verification of fixes for BUG-01 through BUG-07 | Defect reproduction condition vs remediated behavior | Fixed component $\times$ regression verification $\times$ boundary test | Bug definitions in `PROJECT.md § Feature Inventory` (1-7) | `tests/e2e/test_e2e_tier1_engine.py`, `tests/e2e/test_e2e_tier2_boundaries.py` |
| **F-20** | Publication Defense Document | Complete evidence synthesis satisfying R1-R5 acceptance criteria | 100% test pass, statistical significance, comparative landscape | Audit finding $\times$ mathematical proof $\times$ reproducible script | Formal acceptance criteria in `ORIGINAL_REQUEST.md § Acceptance Criteria` | `tests/e2e/test_e2e_tier4_workloads.py` |
| **F-21** | Opaque-Box E2E Test Suite | 4-Tier test suite covering features 1-20 | 100% test execution and pass rate | Tier 1 (Coverage) $\times$ Tier 2 (BVA) $\times$ Tier 3 (Combinations) $\times$ Tier 4 (Workloads) | Complete end-to-end test execution via `pytest tests/e2e/ -v` | All `tests/e2e/` test files |
| **F-22** | Adversarial Hardening | Malformed CGP strings, extreme racks, adversarial board layouts | Empty racks, full board (225 tiles), unicode injection, non-ASCII letters | Malformed input $\times$ engine resilience $\times$ error containment | Graceful rejection / safe fallback without segfaults or crash | `tests/e2e/test_e2e_tier2_boundaries.py` |

---

## 3. Test Suite Organization

The E2E test suite resides entirely within `/home/targed/Documents/Git/Alphable/tests/e2e/` and is partitioned into structured test modules:

```
tests/e2e/
├── __init__.py
├── conftest.py                       # Shared test fixtures (engine, checkpoints, mock policies)
├── test_e2e_tier1_engine.py          # Tier 1: Core Engine, Memory, Move representation, CGP roundtrip
├── test_e2e_tier1_search.py          # Tier 1: BAMS Search, 2-ply rollouts, volatility, parity logic
├── test_e2e_tier1_tournament.py      # Tier 1: Tournament simulation, sign parity, Woogles bot, telemetry
├── test_e2e_tier1_analysis.py        # Tier 1: CLI analysis, model registry, teacher-student distillation
├── test_e2e_tier2_boundaries.py      # Tier 2: Boundary & Corner Cases (empty bag, single tile, coordinate limits)
├── test_e2e_tier3_combinations.py    # Tier 3: Cross-Feature Combinations (BAMS + Belief + Duplicate Tournament)
└── test_e2e_tier4_workloads.py       # Tier 4: Real-World Workload Scenarios (reproducible match series, t-test, z-test)
```

---

## 4. Test Verification Command

The authoritative, production-grade command to execute the complete E2E test suite cleanly is:

```bash
CUDA_VISIBLE_DEVICES="" PYTHONPATH=./venv/lib/python3.11/site-packages:. python3 -m pytest tests/e2e/ -v
```

All tests execute self-contained, isolated state setups with explicit cleanup fixtures ensuring zero test interdependence or residual state.
