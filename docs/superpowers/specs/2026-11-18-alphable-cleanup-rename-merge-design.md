# Design specification: Alphable repository cleanup, package rename, and merge preparation

## Overview

This specification details the repository reorganization, package renaming, and documentation restructuring for Alphable (`/home/targed/Documents/Git/Alphable`) to transition the `alphable_V4_paper_base` development branch into the clean, polished `main` branch.

## Goals

1. **Root Directory Hygiene**: Archive all Slurm cluster output/error files (`Mill-*.{out,err}`) to `slurm/logs/`, remove broken symlinks and scratch logs (`ORIGINAL_REQUEST.md`, `main.log`), and move root developer documentation into `docs/`.
2. **Diátaxis Documentation Reorganization**: Group the 24 flat Markdown files in `docs/` into Diátaxis quadrants (Tutorials, How-to, Reference, Explanation), archive historical phase reports into `docs/reports/`, and provide a clean navigation index in `docs/README.md`.
3. **Clean Package Rename (`alphable_v4` -> `alphable`)**: Rename package directory `alphable_v4/` to `alphable/`, update all imports across the codebase, tests, scripts, and visualizer, and provide a `sys.modules` compatibility shim to preserve seamless PyTorch checkpoint unpickling.
4. **Verification and Merge**: Verify the test suite (all 186 unit and integration tests) passes cleanly, fast-forward merge `alphable_V4_paper_base` into `main`, and push to remote.

## Component specifications

### 1. Root Cleanup and Gitignore Policy

- Move `Mill-*.err` and `Mill-*.out` (11 pairs) into `slurm/logs/`.
- Append to `.gitignore`:
  ```text
  Mill-*.out
  Mill-*.err
  *.log
  ```
- Remove `ORIGINAL_REQUEST.md` (broken symlink).
- Remove `main.log`.
- Move `PROJECT.md` to `docs/PROJECT_CONTEXT.md`.
- Consolidate `TEST_INFRA.md` and `TEST_READY.md` into `docs/how_to/TESTING_AND_VERIFICATION_GUIDE.md`, then remove from root.

### 2. Documentation Architecture (Diátaxis)

Restructure `docs/` as follows:

```text
docs/
├── README.md                                          # Diátaxis navigation index
├── PROJECT_CONTEXT.md                                 # High-level architecture and problem overview
├── tutorials/
│   └── GETTING_STARTED.md                             # Step-by-step setup walkthrough
├── how_to/
│   ├── USER_GUIDE.md                                  # CLI commands and match execution
│   └── TESTING_AND_VERIFICATION_GUIDE.md             # Testing runbooks & infrastructure guide
├── reference/
│   ├── ARCHITECTURE.md                                # Neural ResNet-18, attention heads, BAMS specification
│   ├── MODELS_AND_RESOURCES.md                        # Checkpoint details, tensor shapes, parameters
│   └── TOURNAMENT_BENCHMARKS_AND_COMMAND_MANUAL.md   # Benchmark metrics and execution commands
├── explanation/
│   ├── AI_VS_MAGPIE_EXPLAINED.md                      # Neural MCTS vs classical heuristics
│   ├── STATISTICAL_SIGNIFICANCE_AND_BENCHMARKING_GUIDE.md # Duplicate tournament methodology
│   └── ROADMAP_TO_58_PERCENT.md                       # Strategic analysis and scaling horizons
└── reports/                                           # Historical milestone reports and audit logs
    ├── PHASE0_RESULTS.md
    ├── PHASE1_RESULTS.md
    ├── PHASE2_RESULTS.md
    ├── PHASE3_RESULTS.md
    ├── PHASE4_RESULTS.md
    ├── ALPHABLE_V4_SCIENTIFIC_DEFENSE_AND_AUDIT_REPORT.md
    ├── BENCHMARK_10K_HYBRID_PIMC_VS_TUNED_MAGPIE.md
    ├── DIAGNOSIS_AND_STRATEGIC_IMPROVEMENTS.md
    ├── MASTER_FRONTIERS_IMPLEMENTATION_PLAN.md
    └── RESEARCH_AND_BRAINSTORMING_BREAKTHROUGH.md
```

All relative links in `README.md` and `docs/README.md` must be updated to match the new directory layout.

### 3. Package Rename (`alphable_v4` -> `alphable`)

- Execute `git mv alphable_v4 alphable`.
- Update `pyproject.toml`:
  - `name = "alphable"`
  - `packages = [{include = "alphable"}]`
- In `alphable/__init__.py`, register module aliases in `sys.modules`:
  ```python
  import sys
  from . import models, engine, search, platform, training

  sys.modules.setdefault("alphable_v4", sys.modules[__name__])
  sys.modules.setdefault("alphable_v4.models", models)
  sys.modules.setdefault("alphable_v4.models.value_net", models.value_net)
  sys.modules.setdefault("alphable_v4.engine", engine)
  sys.modules.setdefault("alphable_v4.search", search)
  sys.modules.setdefault("alphable_v4.platform", platform)
  sys.modules.setdefault("alphable_v4.training", training)
  ```
- Update imports across:
  - `alphable/**/*.py`
  - `tests/**/*.py`
  - `cli.py`
  - `scripts/**/*.py`
  - `visualizer/**/*.py`
  - `install.sh`
- Verify checkpoint paths default to `alphable/models/checkpoints/v4_value_net_best.pt` (or `alphable_value_net_best.pt`).

### 4. Verification and Merge Plan

1. Run unit test suite: `pytest tests/ -v` (confirming all 186 tests pass).
2. Run smoke check via CLI: `python cli.py --help` and verify model checkpoint loading.
3. Verify git tree is clean on `alphable_V4_paper_base`.
4. Switch to `main`: `git checkout main`.
5. Merge `alphable_V4_paper_base`: `git merge alphable_V4_paper_base`.
6. Run `pytest tests/ -v` on `main` to verify merged state.
7. Push `main` to `origin`.
