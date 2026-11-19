# Project: Alphable V4 Comprehensive Audit & Scientific Defense

## Architecture
Alphable V4 is a hybrid neural-symbolic Scrabble artificial intelligence combining:
1. **Ultra-fast C-native Move Generation**: Wrapped around MAGPIE (`vendor/magpie/bin/libmagpie.so` via `magpie_bindings.py`).
2. **Bayesian Opponent Rack Inference**: `NeuralBeliefNet` and `OpponentTracker` tracking unseen tiles with negative-evidence likelihood decay and hypergeometric bag replenishment.
3. **Deep Cross-Attention Value Network**: `V4ValueNetwork` combining a 32-channel ResNet-18 spatial board encoder and a 64-dimensional dynamic state vector (score spread, rack metrics, bag tracking) via multi-head cross-attention.
4. **BAMS 2-Ply Search**: Beam-filtered candidate selection, 2-ply counterplay rollouts with Common Random Numbers (CRN), asymmetric volatility control, and exact alpha-beta endgame solver.
5. **Evaluation Platform**: Head-to-head duplicate tournament simulator (`GameSimulator`, `cli.py`) isolating player skill by pair-swapping racks and tile draw sequences.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | C Memory Management | Zero-leak string allocation and freeing in ctypes wrapper (`magpie_bindings.py`) | M1 | Survey 1 (BUG-01) |
| 2 | Pre-Endgame Parity Logic | Correct calculation of `tiles_played` and bag-emptying parity tempo bonus | M1 | Survey 1 (BUG-02) |
| 3 | Woogles Protocol Formatting | Standard pass and exchange move formatting in `woogles_bot.py` | M1 | Survey 1 (BUG-03) |
| 4 | Continuous Volatility Control | Smooth score-differential volatility scaling without jump discontinuity | M1 | Survey 1 (BUG-04) |
| 5 | Strict Coordinate Parsing | Safe coordinate range validation (1-15, A-O) in `Move.parse_coordinate` | M1 | Survey 1 (BUG-05) |
| 6 | Tournament Runner Sign Fix | Correct winner/spread assignment in alternating tournament mode | M1 | Survey 2 (BUG-06) |
| 7 | Game-Phase Telemetry | Per-move phase tagging (opening, midgame, pre-endgame, endgame) in tournament logs | M1 | Survey 2 (BUG-07) |
| 8 | Statistical Hypothesis Testing | Paired t-test, 2-proportion z-test, Wilson intervals on 3k and 10k duplicate games | M2 | R1, Survey 2 |
| 9 | Game-Phase Sensitivity Audit | Empirical win-rate and spread sensitivity breakdown across game phases | M2 | R1, Acceptance Criteria |
| 10 | CRN Variance Reduction Proof | Formal mathematical proof of Common Random Numbers variance reduction in Scrabble | M2 | Survey 3 |
| 11 | First-Order Luck Cancellation | Formal theorem and proof of tile luck cancellation in duplicate pair matches | M2 | Survey 3 |
| 12 | Base MAGPIE Ceiling Audit | Discovery and analysis of PAT, WMP, and simulation lookahead parameters in MAGPIE | M3 | R2, Survey 2 |
| 13 | Tuned MAGPIE Benchmark | Empirical benchmark tournament data vs default and tuned Base MAGPIE | M3 | R2, Acceptance Criteria |
| 14 | Generator Enhancement Transfer | Verification of MAGPIE parameter enhancements transferring to V4 candidate generation | M3 | R2, Survey 2 |
| 15 | Macondo Architectural Benchmark | Deep comparative assessment against Macondo (B* search, Superleaves) and Quackle | M4 | R3, Survey 3 |
| 16 | Throughput & Depth Landscape | Quantitative comparison of search throughput (nps), equity accuracy, and lookahead | M4 | R3, Survey 3 |
| 17 | Teacher-Student Relationship | Formal documentation of Macondo distillation dataset in V4 neural training | M4 | Survey 3 |
| 18 | Master Benchmark Tables | Production of Tables 1-3 (Master Benchmark, Ablations, Phase Sensitivity) | M5 | R5, Survey 3 |
| 19 | Complete Bug Remediation Log | Formal audit log of all identified bugs, root causes, and verified fixes | M5 | R5, Survey 1 |
| 20 | Publication Defense Document | Publication-grade scientific defense report in `docs/` meeting all criteria | M5 | R5, Acceptance Criteria |
| 21 | Opaque-Box E2E Test Suite | 4-tier requirement-driven E2E test suite covering features 1-20 | E2E | Dual Track |
| 22 | Adversarial Hardening | Tier 5 adversarial stress testing of neural inference, search edge cases, and memory | M6 | Dual Track Phase 2 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Suite | Requirements-driven 4-tier E2E tests, `TEST_INFRA.md`, and `TEST_READY.md` | none | DONE |
| M1 | Code Remediation & Bug Fixes | Fix BUG-01 to BUG-07 in engine, search, platform, and cli; verify unit tests | none | DONE |
| M2 | Statistical Rigor & Phase Audit | Run paired hypothesis tests, phase sensitivity analysis, mathematical proofs | M1 | DONE |
| M3 | MAGPIE Ceiling & Parameter Rigor | Tuned MAGPIE analysis, generator transferability test, benchmark tournament | M1 | DONE |
| M4 | Comparative SOTA Landscape | Macondo and Quackle architecture, throughput, equity comparison | M1 | DONE |
| M5 | Scientific Defense Report | Publication-grade comprehensive report in `docs/` synthesizing R1-R5 | M2, M3, M4 | DONE |
| M6 | Final Verification & Hardening | 100% E2E test pass + Tier 5 adversarial stress testing & clean audit | E2E, M5 | DONE |

## Interface Contracts
### `alphable/engine/magpie_bindings.py` ↔ `vendor/magpie/bin/libmagpie.so`
- `magpie_get_last_command_output(mp: c_void_p) -> c_void_p`: Return raw pointer, decode via `string_at()`, immediately free via `magpie_free_string(ptr)`.
- `magpie_get_and_clear_error(mp: c_void_p) -> c_void_p`: Same safe memory management pattern.

### `alphable/engine/move.py` ↔ `alphable/search/bams.py`
- `Move.tiles_placed`: Evaluated accurately from `Move` definition or calculated as `7 - len(cand.leave)` for placement moves.
- `Move.parse_coordinate(coord: str) -> Tuple[int, int, str]`: Enforce `1 <= row <= 15` and `'A' <= col <= 'O'`. Raise `ValueError` on out-of-bounds coordinates.

### `alphable/platform/eval.py` ↔ `alphable/cli.py`
- `GameSimulator.play_game(...) -> MatchStats`: Track phase per move:
  - `OPENING`: turns 1 to 5
  - `MIDGAME`: turn > 5 and bag > 14
  - `PRE_ENDGAME`: bag in 1..14
  - `ENDGAME`: bag == 0
- Log phase score differentials and phase win contributions in duplicate game records.

## Code Layout
- `alphable/engine/`: `magpie_bindings.py`, `game_state.py`, `move.py`
- `alphable/models/`: `value_net.py`, `belief_net.py`, `checkpoints/`
- `alphable/search/`: `bams.py`
- `alphable/platform/`: `eval.py`, `woogles_bot.py`
- `alphable/training/`: `parse_gcg.py`, `train_value.py`, `train_rl.py`, etc.
- `alphable/cli.py` & `cli.py`: CLI tournament and analysis runner
- `tests/`: 57 core unit & integration tests
- `visualizer/tests/`: 20 visualizer unit tests
- `tests/e2e/`: Requirement-driven E2E test suite
- `docs/`: Comprehensive scientific defense and audit report
