# Alphable Documentation Index

Documentation for the Alphable Scrabble AI engine is organized using the [Diátaxis framework](https://diataxis.fr/), partitioning content across four operational modes: Tutorials, How-To Guides, Reference, and Explanation. Historical milestone reports and audit findings are archived in `reports/`.

---

## 1. Tutorials (Learning-Oriented)

Tutorials guide newcomers through their first working installation and end-to-end match execution.

- **[tutorials/GETTING_STARTED.md](tutorials/GETTING_STARTED.md)**  
  Step-by-step setup walkthrough: configuring the virtual environment, compiling the C MAGPIE shared library, verifying value net weights, and running your first smoke match.

---

## 2. How-To Guides (Task-Oriented)

How-to guides provide direct runbooks for solving concrete operational tasks and running experiments.

- **[how_to/USER_GUIDE.md](how_to/USER_GUIDE.md)**  
  Runbook for end users and researchers: executing CLI commands, analyzing single rack positions, inspecting word hooks, and launching interactive terminal play.
- **[how_to/TESTING_AND_VERIFICATION_GUIDE.md](how_to/TESTING_AND_VERIFICATION_GUIDE.md)**  
  Runbook for verification and testing: executing the 4-tier E2E test suite, running paired duplicate tournaments, setting up pre-flight CI checks, and inspecting structured telemetry.

---

## 3. Reference (Information-Oriented)

Reference material provides technical specifications, interfaces, hyperparameters, and command options.

- **[reference/ARCHITECTURE.md](reference/ARCHITECTURE.md)**  
  Technical specification of Alphable subsystems: C-native MAGPIE bindings, Bayesian belief tracking, ResNet-18 spatial cross-attention value network, and BAMS nested 2-ply search.
- **[reference/MODELS_AND_RESOURCES.md](reference/MODELS_AND_RESOURCES.md)**  
  Specification of neural checkpoints, tensor dimensions, parameter counts, lexicon files (CSW24, NWL23), and model registry presets.
- **[reference/TOURNAMENT_BENCHMARKS_AND_COMMAND_MANUAL.md](reference/TOURNAMENT_BENCHMARKS_AND_COMMAND_MANUAL.md)**  
  Command syntax, CLI flags, configuration arguments, and benchmark output schemas for duplicate tournaments.

---

## 4. Explanation (Understanding-Oriented)

Explanations explore theoretical concepts, mathematical formulations, strategic trade-offs, and design choices.

- **[explanation/AI_VS_MAGPIE_EXPLAINED.md](explanation/AI_VS_MAGPIE_EXPLAINED.md)**  
  Conceptual comparison between classical 1-ply heuristic valuation (Static KLV in Base MAGPIE) and deep Monte Carlo search with negative-evidence belief tracking.
- **[explanation/STATISTICAL_SIGNIFICANCE_AND_BENCHMARKING_GUIDE.md](explanation/STATISTICAL_SIGNIFICANCE_AND_BENCHMARKING_GUIDE.md)**  
  Mathematical background on paired duplicate testing, Common Random Numbers (CRN) variance reduction, Two-Proportion z-tests, and Wilson score intervals.
- **[explanation/ROADMAP_TO_58_PERCENT.md](explanation/ROADMAP_TO_58_PERCENT.md)**  
  Strategic analysis and scaling projections for reaching 58% duplicate win rates against grandmaster engines.

---

## Project Context & Architecture Overview

- **[PROJECT_CONTEXT.md](PROJECT_CONTEXT.md)**  
  High-level problem overview, 22-feature inventory, milestone definitions, and interface contracts.

---

## Reports & Historical Archives

Milestone logs, audit records, and competitive defense documents are preserved in `reports/`:

- **[reports/ALPHABLE_V4_SCIENTIFIC_DEFENSE_AND_AUDIT_REPORT.md](reports/ALPHABLE_V4_SCIENTIFIC_DEFENSE_AND_AUDIT_REPORT.md)**: Technical report (TR-2026-ALPHABLE-V4-DEFENSE) synthesizing 10k duplicate game statistics, parameter ceiling audits, bug remediation records, and publication defense.
- **[reports/BENCHMARK_10K_HYBRID_PIMC_VS_TUNED_MAGPIE.md](reports/BENCHMARK_10K_HYBRID_PIMC_VS_TUNED_MAGPIE.md)**: Benchmark report evaluating the Hybrid PIMC engine against Tuned MAGPIE.
- **[reports/DIAGNOSIS_AND_STRATEGIC_IMPROVEMENTS.md](reports/DIAGNOSIS_AND_STRATEGIC_IMPROVEMENTS.md)**: Diagnostic breakdown of historical bottlenecks and algorithmic refinements.
- **[reports/MASTER_FRONTIERS_IMPLEMENTATION_PLAN.md](reports/MASTER_FRONTIERS_IMPLEMENTATION_PLAN.md)**: Architecture roadmap for the five core frontiers of Alphable V4.
- **[reports/RESEARCH_AND_BRAINSTORMING_BREAKTHROUGH.md](reports/RESEARCH_AND_BRAINSTORMING_BREAKTHROUGH.md)**: Research notes and theoretical breakthroughs during development.
- **Phase Results**: [Phase 0](reports/PHASE0_RESULTS.md), [Phase 1](reports/PHASE1_RESULTS.md), [Phase 2](reports/PHASE2_RESULTS.md), [Phase 3](reports/PHASE3_RESULTS.md), and [Phase 4](reports/PHASE4_RESULTS.md).

---

## Primary Machine-Readable Telemetry

Audit artifacts and raw JSON records reside in `data/audit/`:
- `data/audit/m2_statistical_rigor.json`: Statistical hypothesis test results and phase sensitivity metrics.
- `data/audit/m3_magpie_ceiling.json`: Base MAGPIE parameter ceiling benchmarks and transfer evaluations.
- `data/audit/m4_sota_comparative.json`: SOTA landscape taxonomy, Macondo distillation loss metrics, and latency logs.
