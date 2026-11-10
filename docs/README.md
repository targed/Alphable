# Alphable Documentation Index

Welcome to the documentation repository for **Alphable V4**, a superhuman hybrid neural-symbolic Scrabble AI engine.

---

## Primary Publications & Scientific Defense

- **[ALPHABLE_V4_SCIENTIFIC_DEFENSE_AND_AUDIT_REPORT.md](ALPHABLE_V4_SCIENTIFIC_DEFENSE_AND_AUDIT_REPORT.md)**  
  *Primary Publication-Grade Technical Report (TR-2026-ALPHABLE-V4-DEFENSE)*  
  Comprehensive adversarial audit, mathematical proofs (POMDP, CRN variance reduction, luck cancellation), empirical statistical significance tests (3k and 10k duplicate games, $t=8.75$), Base MAGPIE parameter ceiling audit, SOTA comparative analysis (Macondo distillation, Quackle, Maven), complete codebase bug remediation log (BUG-01 to BUG-07), verified benchmark tables (Tables 1–3), and publication readiness attestation.

---

## Architectural & Research Documents

- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Deep overview of Alphable V4's hybrid architecture (C-native MAGPIE bindings, Bayesian belief tracking, ResNet-18 cross-attention value network, and BAMS 2-ply nested MCTS).
- **[RESEARCH_AND_BRAINSTORMING_BREAKTHROUGH.md](RESEARCH_AND_BRAINSTORMING_BREAKTHROUGH.md)**: Core research log and theoretical breakthroughs.
- **[ROADMAP_TO_58_PERCENT.md](ROADMAP_TO_58_PERCENT.md)**: Strategic roadmap for maximizing competitive win rate against grandmaster engines.
- **[MASTER_FRONTIERS_IMPLEMENTATION_PLAN.md](MASTER_FRONTIERS_IMPLEMENTATION_PLAN.md)**: Engineering breakdown of the five frontiers of Alphable V4.

---

## Empirical Benchmarks & Operational Guides

- **[STATISTICAL_SIGNIFICANCE_AND_BENCHMARKING_GUIDE.md](STATISTICAL_SIGNIFICANCE_AND_BENCHMARKING_GUIDE.md)**: Rigorous guide to interpreting duplicate tournaments, two-proportion z-tests, Wilson score intervals, and paired t-tests.
- **[TOURNAMENT_BENCHMARKS_AND_COMMAND_MANUAL.md](TOURNAMENT_BENCHMARKS_AND_COMMAND_MANUAL.md)**: Master CLI reference for running duplicate tournaments, evaluating checkpoints, and logging match telemetry.
- **[GETTING_STARTED.md](GETTING_STARTED.md)**: Setup guide, virtual environment instructions, and dependencies.
- **[USER_GUIDE.md](USER_GUIDE.md)**: End-user and developer manual for running CLI commands and analyzing Scrabble positions.
- **[MODELS_AND_RESOURCES.md](MODELS_AND_RESOURCES.md)**: Model checkpoint registry, weights metadata, and lexicon file descriptions.
- **[AI_VS_MAGPIE_EXPLAINED.md](AI_VS_MAGPIE_EXPLAINED.md)**: High-level conceptual explanation of how Alphable V4 differs from Base MAGPIE.
- **[DIAGNOSIS_AND_STRATEGIC_IMPROVEMENTS.md](DIAGNOSIS_AND_STRATEGIC_IMPROVEMENTS.md)**: Historical diagnostic insights and algorithmic refinements.

---

## Audit Telemetry & Structured Data Artifacts

Primary machine-readable audit artifacts are located in `data/audit/`:
- `data/audit/m2_statistical_rigor.json`: Statistical hypothesis tests, phase sensitivity metrics, and mathematical proof structures.
- `data/audit/m3_magpie_ceiling.json`: Base MAGPIE parameter ceiling benchmarks, tuned tournaments, and generator transfer evaluations.
- `data/audit/m4_sota_comparative.json`: SOTA landscape taxonomy, Macondo distillation loss metrics, and quantitative throughput evaluations.
