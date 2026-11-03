# Alphable V4 Repository Restructuring & Promotion Specification

**Date:** 2026-11-03  
**Status:** Approved  
**Topic:** Transition from multi-version monorepo to dedicated Alphable V4 research repository  

---

## 1. Executive Summary & Goals

This specification outlines the architectural restructuring of the `Alphable` repository. The goal is to transform the repository into a clean, modern, high-performance research and code repository centered on **Alphable V4** (the championship-tier Scrabble AI engine combining native C MAGPIE move generation, Bayesian opponent rack inference, and BAMS Monte Carlo search with deep cross-attention value networks).

Key objectives:
1. **Permanent Archival**: Safely preserve the historical monorepo (Alphable V1, V2, and V3 prototypes, benchmarks, datasets, and history) on a dedicated branch (`archive/legacy-monorepo`) and tag (`archive-monorepo-v1-v3`).
2. **Promote V4 to Root**: Remove nested `Alphable_V4/` subfolder and promote its package, CLI, tests, documentation, benchmarks, and resources to the repository root.
3. **Clean Packaging**: Replace the recursive symlink hack (`alphable_v4 -> .`) with a standard, concrete Python package directory (`alphable_v4/`), including all submodules (`engine`, `models`, `search`, `platform`, `training`).
4. **Preserve Untracked Assets**: Protect untracked local vendor dependencies (`vendor/magpie/` with compiled `libmagpie.so` and binary lexica) and local checkpoints (`v4_value_net_best_full_training.pt`) during the migration.
5. **Update Studio Adapters & Tooling**: Update `visualizer/` adapters and backend services to seamlessly interface with the promoted root package and data directories, ensuring all tests pass.
6. **Streamline Root Documentation & Scripts**: Replace obsolete root-level files with a unified `README.md`, `pyproject.toml`, `requirements.txt`, and `install.sh`.

---

## 2. Archival & Preservation Strategy

Before executing any file moves or removals on `main`:
1. Verify working directory status (clean git state).
2. Create permanent preservation branch:
   ```bash
   git branch archive/legacy-monorepo HEAD
   ```
3. Create annotated git tag:
   ```bash
   git tag -a archive-monorepo-v1-v3 -m "Monorepo baseline preserving Alphable V1, V2, and V3"
   ```
4. Verify that the branch points to commit `bd0cb6c` (or current `HEAD`).

---

## 3. Target Repository Hierarchy

The repository root on `main` will have the following structure:

```
Alphable/
├── alphable_v4/                     # Core Python Package
│   ├── __init__.py                  # Version, package exports, PyTorch CUDA settings
│   ├── engine/                      # Move, GameState, C-extension MAGPIE bindings
│   │   ├── __init__.py
│   │   ├── game_state.py
│   │   ├── magpie_bindings.py
│   │   └── move.py
│   ├── models/                      # Neural architectures & weights
│   │   ├── __init__.py
│   │   ├── belief_net.py            # Bayesian rack inference
│   │   ├── value_net.py             # ResNet-18 + Cross-Attention Value Network
│   │   └── checkpoints/             # Tracked and untracked neural checkpoints
│   │       ├── v4_value_net_best.pt
│   │       ├── v4_belief_net_best.pt
│   │       ├── v4_value_net_rl_gen1.pt
│   │       └── v4_value_net_best_full_training.pt (untracked)
│   ├── search/                      # BAMS Search
│   │   ├── __init__.py              # Added standard package init
│   │   └── bams.py
│   ├── platform/                    # Tournament runners & platform bots
│   │   ├── __init__.py
│   │   ├── eval.py
│   │   └── woogles_bot.py
│   └── training/                    # Datasets, distillation, RL pipelines
│       ├── __init__.py
│       ├── build_belief_dataset.py
│       ├── build_value_dataset.py
│       ├── collect_woogles.py
│       ├── macondo_distill.py
│       ├── optimize_hyperparams.py
│       ├── parse_gcg.py
│       ├── train_belief.py
│       ├── train_rl.py
│       └── train_value.py
├── cli.py                           # Command center (models, tournament, play, analyze, ablation)
├── tests/                           # Complete test suite
│   ├── engine/
│   │   ├── test_game_state.py
│   │   └── test_magpie_parity.py
│   ├── models/
│   │   └── test_models.py
│   ├── search/
│   │   └── test_bams.py
│   ├── platform/
│   │   ├── test_cli.py
│   │   └── test_eval.py
│   └── training/
│       ├── test_data_pipeline.py
│       └── test_rl.py
├── docs/                            # Research & technical documentation
│   ├── ARCHITECTURE.md
│   ├── GETTING_STARTED.md
│   ├── USER_GUIDE.md
│   ├── AI_VS_MAGPIE_EXPLAINED.md
│   ├── DIAGNOSIS_AND_STRATEGIC_IMPROVEMENTS.md
│   ├── MASTER_FRONTIERS_IMPLEMENTATION_PLAN.md
│   ├── MODELS_AND_RESOURCES.md
│   ├── PHASE0_RESULTS.md
│   ├── PHASE1_RESULTS.md
│   ├── PHASE2_RESULTS.md
│   ├── PHASE3_RESULTS.md
│   ├── PHASE4_RESULTS.md
│   ├── RESEARCH_AND_BRAINSTORMING_BREAKTHROUGH.md
│   ├── ROADMAP_TO_58_PERCENT.md
│   ├── STATISTICAL_SIGNIFICANCE_AND_BENCHMARKING_GUIDE.md
│   ├── TOURNAMENT_BENCHMARKS_AND_COMMAND_MANUAL.md
│   ├── papers/
│   │   └── 2511.07312v2.pdf         # Reference paper moved from root
│   └── superpowers/                 # Planning & spec artifacts
├── data/                            # Persistent datasets & tournaments
│   ├── belief/
│   ├── value/
│   └── tournaments/
│       ├── tournament_history.jsonl
│       └── run_*.json
├── resources/                       # Lexica
│   ├── CSW24.txt
│   └── NWL23.txt
├── vendor/                          # Native C engine dependencies
│   └── magpie/                      # MAGPIE submodule / clone
│       ├── bin/
│       │   ├── libmagpie.so
│       │   └── libmagpie.dylib
│       └── data/                    # Precompiled lexicon binary caches
├── scratch/                         # Scratch benchmarks & experiments
├── visualizer/                      # Studio frontend & Flask backend
│   ├── backend/
│   ├── frontend/
│   ├── tests/
│   ├── README.md
│   └── run.sh
├── pyproject.toml                   # Root package metadata & pytest config
├── requirements.txt                 # Clean pinned dependencies
├── install.sh                       # One-command build & verification script
├── start_visualizer.sh              # Symlink -> visualizer/run.sh
├── .gitignore                       # Updated to reflect root vendor/ and data/
└── README.md                        # Primary V4 research repository README
```

---

## 4. Component Details & Migration Steps

### 4.1 Git Removals on `main`
The legacy folders are tracked in git and will be deleted from the working tree and index on `main`:
- `git rm -r Alphable_V1`
- `git rm -r Alphable_V2`
- `git rm -r Alphable_V3`
- Remove stale root files: `structure.c`, `structure.cpython-311-x86_64-linux-gnu.so`, `alphable_v4_implementation_plan.md`, `eval/`, `build/`.

### 4.2 Moving Alphable_V4 into Root
To maintain git history, tracked files are moved via `git mv`:
1. Create `alphable_v4/` directory.
2. Move core modules:
   - `Alphable_V4/engine/` -> `alphable_v4/engine/`
   - `Alphable_V4/models/` -> `alphable_v4/models/`
   - `Alphable_V4/search/` -> `alphable_v4/search/`
   - Add `alphable_v4/search/__init__.py`
   - `Alphable_V4/platform/` -> `alphable_v4/platform/`
   - `Alphable_V4/training/` -> `alphable_v4/training/`
   - `Alphable_V4/__init__.py` -> `alphable_v4/__init__.py`
3. Move root-level scripts and assets:
   - `Alphable_V4/cli.py` -> `cli.py`
   - `Alphable_V4/tests/` -> `tests/`
   - `Alphable_V4/docs/*` -> `docs/`
   - `Alphable_V4/data/*` -> `data/`
   - `Alphable_V4/resources/*` -> `resources/`
   - `Alphable_V4/scratch/*` -> `scratch/`
   - `Alphable_V4/pyproject.toml` -> `pyproject.toml`
   - `Alphable_V4/requirements.txt` -> `requirements.txt`
   - `Alphable_V4/install.sh` -> `install.sh`
   - `Alphable_V4/README.md` -> `README.md`
4. Move reference paper:
   - `2511.07312v2.pdf` -> `docs/papers/2511.07312v2.pdf`
5. Untracked file migrations (using filesystem `mv`):
   - `Alphable_V4/vendor/` -> `vendor/`
   - `Alphable_V4/models/checkpoints/v4_value_net_best_full_training.pt` -> `alphable_v4/models/checkpoints/`
6. Clean up:
   - Remove `Alphable_V4/alphable_v4` symlink.
   - Delete empty `Alphable_V4/` directory.

### 4.3 Updating Visualizer Studio Integration
Update backend services and adapters:
1. `visualizer/backend/adapters/v4_adapter.py`:
   - Replace `V4_DIR` relative navigation with repository root.
   - Import `from alphable_v4.engine.magpie_bindings import MagpieEngine` directly.
2. `visualizer/backend/adapters/baseline_adapter.py`:
   - Update `V4_DIR` to repository root.
3. `visualizer/backend/services/replay_service.py`:
   - Update `V4_DATA_DIR` from `Alphable_V4/data` to `REPO_ROOT / "data"`.
4. `visualizer/backend/services/dictionary_service.py`:
   - Update `CSW24_PATH` to `BASE_DIR / "resources" / "CSW24.txt"`.
   - Update `NWL23_PATH` to `BASE_DIR / "resources" / "NWL23.txt"`.
5. `visualizer/backend/adapters/v3_adapter.py`:
   - Confirm it handles missing `Alphable_V3` gracefully without raising unhandled exceptions (`V3_AVAILABLE = False`).
6. `visualizer/tests/`:
   - Run visualizer unit tests to confirm all adapters, services, and endpoints pass.

### 4.4 Engine Path Resolution & Config Updates
In `alphable_v4/engine/magpie_bindings.py`:
- Verify `find_libmagpie()` searches `vendor/magpie/bin/libmagpie.so` relative to the package root and `cwd`.
- Ensure `data_dir` resolves to `vendor/magpie/data`.

In `install.sh`:
- Ensure virtual environment and setup script operations run relative to repo root (`.` instead of `cd Alphable_V4`).

In `.gitignore`:
- Replace `/Alphable_V4/vendor/` with `/vendor/`.
- Ensure `*.pt` rules keep `v4_value_net_best.pt`, `v4_belief_net_best.pt`, `v4_value_net_rl_gen1.pt` tracked while ignoring `*_full_training.pt`.

---

## 5. Verification Plan

1. **Git Integrity**:
   - `git branch` confirms `archive/legacy-monorepo` exists.
   - `git tag -l` confirms `archive-monorepo-v1-v3` exists.
   - `git status` confirms working directory is clean and properly tracked.
2. **Package & Engine Verification**:
   - Python package import test: `python -c "import alphable_v4; print(alphable_v4.__file__)"`
   - Magpie C bindings test: `python -c "from alphable_v4.engine.magpie_bindings import MagpieEngine; e = MagpieEngine(); print('Magpie loaded successfully')"`
   - Checkpoints test: `python cli.py models` displays all registered presets and win rates.
3. **Automated Test Suites**:
   - Engine and model unit tests: `pytest tests/engine/ tests/models/ tests/search/ tests/platform/`
   - Visualizer tests: `pytest visualizer/tests/`
4. **Interactive Verification**:
   - `python cli.py analyze --rack "AQRTUYZ"` generates move valuations.
   - Launch `./start_visualizer.sh` or check backend health endpoint.
