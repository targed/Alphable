# Original User Request

## 2026-11-09T22:20:16Z

Comprehensive adversarial audit, independent verification, and scientific defense of Alphable V4 against Base MAGPIE and state-of-the-art Scrabble engines (including Macondo), evaluating statistical validity, parameter limits, implementation correctness, and publication readiness.

Working directory: /home/targed/Documents/Git/Alphable
Integrity mode: development

## Requirements

### R1. Statistical Rigor & Algorithmic Edge Audit
Perform an adversarial audit of Alphable V4's empirical claims (+7.1 pts net spread, 54.7% win rate in 3,000 duplicate games vs Base MAGPIE). Disprove or prove whether this performance delta represents a genuine strategic advantage or is an artifact of sample variance, random seed selection, or an overfit exploitation of specific Base MAGPIE move generation gaps that would fail to generalize.

### R2. Base MAGPIE Configuration & Parameter Ceiling Investigation
Investigate whether Base MAGPIE possesses unturned parameters, deeper lookahead settings, alternative leave-value tables, or runtime options (e.g., `-numplays`, `-maxnumdplays`, WMP mode, endgame search depth) that eliminate or reverse Alphable V4's advantage. Evaluate whether any improvements available to Base MAGPIE directly transfer to or benefit Alphable V4 as its underlying generator.

### R3. Comparative Evaluation Against State-of-the-Art (Macondo & Landscape)
Benchmark Alphable V4 within the broader Scrabble AI research landscape. Compare its architecture (BAMS 2-ply MCTS with cross-attention value network and Bayesian rack inference) against Macondo (the current state-of-the-art benchmark engine) and Quackle in terms of equity accuracy, search throughput, position evaluation depth, and tournament performance.

### R4. Exhaustive Codebase, Implementation & Bug Audit
Review every core module of Alphable V4:
1. `alphable_v4/engine/`: Ctypes bindings (`magpie_bindings.py`), CGP board string serialization, move dataclasses, and coordinate parsing.
2. `alphable_v4/models/`: `V4ValueNetwork` architecture, tensor representations, weight checkpoint loading, and `NeuralBeliefNet` Bayesian inference.
3. `alphable_v4/search/`: `BAMSSearch` 2-ply candidate rollouts, opponent threat calculation, volatility control formula, pre-endgame tile sticking, and exact alpha-beta endgame solver.
4. `alphable_v4/platform/`: Tournament simulation loops, paired duplicate runner, and statistical significance calculations.
Identify and fix any latent bugs, numerical instability, memory leaks, or flawed theoretical assumptions.

### R5. Scientific Defense & Publication Readiness Report
Produce a publication-grade audit report documenting:
1. Mathematical proofs and statistical validation of the observed win-rate distribution.
2. Verified benchmark tables comparing default and tuned Base MAGPIE, Alphable V4 variants, and Macondo.
3. A complete log of identified bugs, code remediation, and structural improvements.
4. Definitive conclusions on the scientific validity of Alphable V4's contribution to Scrabble AI.

## Verification Resources

- Automated test suites: `pytest tests/ -v` (57 unit/integration tests) and `pytest visualizer/tests/ -v` (20 visualizer tests).
- CLI tournament runner: `./cli.py tournament --duplicate --games <N>` and position analyzer: `./cli.py analyze`.
- Historical tournament logs: `data/tournaments/tournament_history.jsonl` and full JSON run telemetry in `data/tournaments/`.
- Native C MAGPIE engine: `vendor/magpie/` with compiled shared library at `vendor/magpie/bin/libmagpie.so`.
- Lexicon resources: `resources/CSW24.txt` and `resources/NWL23.txt`.

## Acceptance Criteria

### Statistical & Empirical Validation
- [ ] Statistical significance verified via paired two-tailed t-tests and two-proportion z-tests on reproducible duplicate tournament seeds.
- [ ] Quantitative sensitivity analysis testing whether the win rate holds across varying game phases (opening, midgame, pre-endgame, endgame).

### Engine Benchmark & Parameter Rigor
- [ ] Empirical tournament data comparing Alphable V4 against both default Base MAGPIE and maximally tuned Base MAGPIE configurations.
- [ ] Documented comparative assessment analyzing architectural differences, performance trade-offs, and head-to-head feasibility between Alphable V4 and Macondo.

### Code Quality & Implementation Correctness
- [ ] All discovered codebase bugs, edge-case failures, or numerical instabilities documented and resolved.
- [ ] All 57 core unit tests and 20 visualizer tests pass cleanly without errors or regressions.
- [ ] Full audit findings compiled into a comprehensive, publication-ready technical document in `docs/`.
