# Alphable Cleanup, Package Rename, and Main Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean up the repository root, reorganize documentation under the Diátaxis framework, rename `alphable_v4` to `alphable` with backwards-compatible checkpoint shims, verify all tests pass, and fast-forward merge `alphable_V4_paper_base` into `main`.

**Architecture:** Use structured migration: first clear root noise and Slurm cluster logs into `slurm/logs/`, then relocate documentation into Diátaxis subdirectories (`tutorials/`, `how_to/`, `reference/`, `explanation/`, `reports/`), rename the Python package to `alphable` while injecting a `sys.modules` alias in `alphable/__init__.py`, update all imports, verify the test suite, and merge into `main`.

**Tech Stack:** Python 3.11, PyTorch, MAGPIE C engine, Pytest, Git.

**Spec:** `/home/targed/Documents/Git/Alphable/docs/superpowers/specs/2026-11-18-alphable-cleanup-rename-merge-design.md`

## Global Constraints

- Working directory: `/home/targed/Documents/Git/Alphable`
- Python environment: `/home/targed/Documents/Git/Alphable/venv`
- All 186 unit and integration tests must pass cleanly.
- Checkpoints and unpicklers must continue loading without `ModuleNotFoundError`.
- Preserve documentation integrity and clean Diátaxis navigation.

---

### Task 1: Root Directory Hygiene and Slurm Log Archival

**Files:**
- Move: `Mill-*.err`, `Mill-*.out` -> `slurm/logs/`
- Modify: `.gitignore`
- Delete: `main.log`, `ORIGINAL_REQUEST.md` (broken symlink)

**Interfaces:**
- Produces: Clean repository root with no cluster logs or stale scratch files.

- [ ] **Step 1: Create `slurm/logs/` and move all Mill logs**

```bash
cd /home/targed/Documents/Git/Alphable
mkdir -p slurm/logs
mv Mill-*.err Mill-*.out slurm/logs/ 2>/dev/null || true
```

- [ ] **Step 2: Remove broken symlinks and unversioned logs**

```bash
cd /home/targed/Documents/Git/Alphable
rm -f ORIGINAL_REQUEST.md main.log
```

- [ ] **Step 3: Update `.gitignore`**

Append to `.gitignore`:
```gitignore
# Slurm & runtime logs
Mill-*.out
Mill-*.err
*.log
slurm/logs/
```

- [ ] **Step 4: Verify root directory cleanliness**

Run: `git status --short`
Expected: Mill files untracked or deleted from root, `.gitignore` modified.

- [ ] **Step 5: Commit**

```bash
cd /home/targed/Documents/Git/Alphable
git add slurm/logs/ .gitignore
git add -u Mill-*.err Mill-*.out ORIGINAL_REQUEST.md main.log 2>/dev/null || true
git commit -m "chore: archive Slurm cluster logs to slurm/logs and remove broken root symlinks"
```

---

### Task 2: Diátaxis Documentation Reorganization

**Files:**
- Create: `docs/tutorials/`, `docs/how_to/`, `docs/reference/`, `docs/explanation/`, `docs/reports/`
- Move:
  - `docs/GETTING_STARTED.md` -> `docs/tutorials/GETTING_STARTED.md`
  - `docs/USER_GUIDE.md` -> `docs/how_to/USER_GUIDE.md`
  - `PROJECT.md` -> `docs/PROJECT_CONTEXT.md`
  - `docs/ARCHITECTURE.md` -> `docs/reference/ARCHITECTURE.md`
  - `docs/MODELS_AND_RESOURCES.md` -> `docs/reference/MODELS_AND_RESOURCES.md`
  - `docs/TOURNAMENT_BENCHMARKS_AND_COMMAND_MANUAL.md` -> `docs/reference/TOURNAMENT_BENCHMARKS_AND_COMMAND_MANUAL.md`
  - `docs/AI_VS_MAGPIE_EXPLAINED.md` -> `docs/explanation/AI_VS_MAGPIE_EXPLAINED.md`
  - `docs/STATISTICAL_SIGNIFICANCE_AND_BENCHMARKING_GUIDE.md` -> `docs/explanation/STATISTICAL_SIGNIFICANCE_AND_BENCHMARKING_GUIDE.md`
  - `docs/ROADMAP_TO_58_PERCENT.md` -> `docs/explanation/ROADMAP_TO_58_PERCENT.md`
  - Reports (`docs/PHASE*.md`, `ALPHABLE_V4_SCIENTIFIC_DEFENSE_AND_AUDIT_REPORT.md`, `BENCHMARK_10K_HYBRID_PIMC_VS_TUNED_MAGPIE.md`, `DIAGNOSIS_AND_STRATEGIC_IMPROVEMENTS.md`, `MASTER_FRONTIERS_IMPLEMENTATION_PLAN.md`, `RESEARCH_AND_BRAINSTORMING_BREAKTHROUGH.md`) -> `docs/reports/`
- Consolidate: `TEST_INFRA.md` and `TEST_READY.md` into `docs/how_to/TESTING_AND_VERIFICATION_GUIDE.md`, then delete from root.
- Modify: `docs/README.md` and root `README.md`

**Interfaces:**
- Produces: Professional Diátaxis-compliant documentation structure.

- [ ] **Step 1: Create Diátaxis directory structure and move files**

```bash
cd /home/targed/Documents/Git/Alphable
mkdir -p docs/tutorials docs/how_to docs/reference docs/explanation docs/reports

# Tutorials
git mv docs/GETTING_STARTED.md docs/tutorials/

# How-to
git mv docs/USER_GUIDE.md docs/how_to/
git mv docs/TESTING_AND_VERIFICATION_GUIDE.md docs/how_to/

# Reference
git mv docs/ARCHITECTURE.md docs/reference/
git mv docs/MODELS_AND_RESOURCES.md docs/reference/
git mv docs/TOURNAMENT_BENCHMARKS_AND_COMMAND_MANUAL.md docs/reference/

# Explanation
git mv docs/AI_VS_MAGPIE_EXPLAINED.md docs/explanation/
git mv docs/STATISTICAL_SIGNIFICANCE_AND_BENCHMARKING_GUIDE.md docs/explanation/
git mv docs/ROADMAP_TO_58_PERCENT.md docs/explanation/

# Reports
git mv docs/PHASE*.md docs/reports/
git mv docs/ALPHABLE_V4_SCIENTIFIC_DEFENSE_AND_AUDIT_REPORT.md docs/reports/
git mv docs/BENCHMARK_10K_HYBRID_PIMC_VS_TUNED_MAGPIE.md docs/reports/
git mv docs/DIAGNOSIS_AND_STRATEGIC_IMPROVEMENTS.md docs/reports/
git mv docs/MASTER_FRONTIERS_IMPLEMENTATION_PLAN.md docs/reports/
git mv docs/RESEARCH_AND_BRAINSTORMING_BREAKTHROUGH.md docs/reports/

# Root markdown consolidation
git mv PROJECT.md docs/PROJECT_CONTEXT.md
```

- [ ] **Step 2: Consolidate TEST_INFRA.md and TEST_READY.md into docs/how_to/TESTING_AND_VERIFICATION_GUIDE.md**

Incorporate infrastructure setup and pre-flight checklists from `TEST_INFRA.md` and `TEST_READY.md` into `docs/how_to/TESTING_AND_VERIFICATION_GUIDE.md`, then remove `TEST_INFRA.md` and `TEST_READY.md`.

- [ ] **Step 3: Update `docs/README.md` with Diátaxis Navigation**

Rewrite `docs/README.md` with four clear quadrants (Tutorials, How-to, Reference, Explanation) and a link to `reports/`.

- [ ] **Step 4: Update root `README.md` documentation links**

Update relative paths in root `README.md` to point to `docs/tutorials/`, `docs/how_to/`, `docs/reference/`, `docs/explanation/`, and `docs/reports/`.

- [ ] **Step 5: Commit**

```bash
cd /home/targed/Documents/Git/Alphable
git add docs/ README.md
git rm TEST_INFRA.md TEST_READY.md 2>/dev/null || true
git commit -m "docs: reorganize documentation into Diátaxis framework and archive milestone reports"
```

---

### Task 3: Package Directory Rename and Backwards Compatibility Shim

**Files:**
- Move: `alphable_v4` -> `alphable` via `git mv`
- Modify: `alphable/__init__.py`
- Modify: `pyproject.toml`
- Modify: `cli.py`
- Modify: `install.sh`

**Interfaces:**
- Produces: Package `alphable` with `sys.modules["alphable_v4"]` compatibility shim.

- [ ] **Step 1: Rename package directory**

```bash
cd /home/targed/Documents/Git/Alphable
git mv alphable_v4 alphable
```

- [ ] **Step 2: Add backwards compatibility shim in `alphable/__init__.py`**

Add to `alphable/__init__.py`:
```python
import sys
from . import engine, models, platform, search, training

# Backwards compatibility alias for existing checkpoints and legacy code
sys.modules.setdefault("alphable_v4", sys.modules[__name__])
sys.modules.setdefault("alphable_v4.engine", engine)
sys.modules.setdefault("alphable_v4.engine.game_state", engine.game_state)
sys.modules.setdefault("alphable_v4.engine.magpie_bindings", engine.magpie_bindings)
sys.modules.setdefault("alphable_v4.models", models)
sys.modules.setdefault("alphable_v4.models.value_net", models.value_net)
sys.modules.setdefault("alphable_v4.search", search)
sys.modules.setdefault("alphable_v4.search.bams", search.bams)
sys.modules.setdefault("alphable_v4.platform", platform)
sys.modules.setdefault("alphable_v4.platform.eval", platform.eval)
sys.modules.setdefault("alphable_v4.training", training)
```

- [ ] **Step 3: Update `pyproject.toml`, `cli.py`, and `install.sh`**

In `pyproject.toml`:
```toml
name = "alphable"
packages = [{include = "alphable"}]
```

In `cli.py`:
Change `from alphable_v4...` to `from alphable...`.

In `install.sh`:
Change references from `alphable_v4` to `alphable`.

- [ ] **Step 4: Verify compatibility shim**

Run:
```bash
cd /home/targed/Documents/Git/Alphable
venv/bin/python -c "import alphable; import alphable_v4; assert alphable is alphable_v4; from alphable_v4.models.value_net import V4ValueNetwork; print('Compatibility shim OK')"
```
Expected: Prints "Compatibility shim OK" with exit code 0.

- [ ] **Step 5: Commit**

```bash
cd /home/targed/Documents/Git/Alphable
git add alphable/ pyproject.toml cli.py install.sh
git commit -m "feat: rename package directory to alphable with backwards-compatibility shims"
```

---

### Task 4: Systematic Import Updates across Codebase, Tests, Scripts, and Visualizer

**Files:**
- Modify: all Python files in `alphable/`
- Modify: all Python files in `tests/`
- Modify: all Python files in `scripts/`
- Modify: all Python files in `visualizer/`

**Interfaces:**
- Produces: Clean direct imports of `alphable` across all source code and test suites.

- [ ] **Step 1: Replace `from alphable_v4` and `import alphable_v4` across source and tests**

```bash
cd /home/targed/Documents/Git/Alphable
# Replace in alphable/
find alphable/ -type f -name "*.py" -exec sed -i 's/from alphable_v4\./from alphable\./g' {} +
find alphable/ -type f -name "*.py" -exec sed -i 's/import alphable_v4\./import alphable\./g' {} +
find alphable/ -type f -name "*.py" -exec sed -i 's/alphable_v4/alphable/g' {} +

# Replace in tests/
find tests/ -type f -name "*.py" -exec sed -i 's/from alphable_v4\./from alphable\./g' {} +
find tests/ -type f -name "*.py" -exec sed -i 's/import alphable_v4\./import alphable\./g' {} +
find tests/ -type f -name "*.py" -exec sed -i 's/alphable_v4/alphable/g' {} +

# Replace in scripts/ and visualizer/
find scripts/ visualizer/ -type f -name "*.py" -exec sed -i 's/from alphable_v4\./from alphable\./g' {} +
find scripts/ visualizer/ -type f -name "*.py" -exec sed -i 's/import alphable_v4\./import alphable\./g' {} +
find scripts/ visualizer/ -type f -name "*.py" -exec sed -i 's/alphable_v4/alphable/g' {} +
```

- [ ] **Step 2: Verify zero residual broken imports**

Run:
```bash
grep -rnI "from alphable_v4" alphable/ tests/ scripts/ visualizer/ || true
```
Expected: No matches (except the backwards-compatibility alias lines in `alphable/__init__.py`).

- [ ] **Step 3: Reinstall package in editable mode**

```bash
cd /home/targed/Documents/Git/Alphable
venv/bin/pip install -e .
```

- [ ] **Step 4: Run unit tests**

```bash
cd /home/targed/Documents/Git/Alphable
venv/bin/pytest tests/engine/ tests/models/ tests/platform/ tests/search/ -v
```
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
cd /home/targed/Documents/Git/Alphable
git add alphable/ tests/ scripts/ visualizer/
git commit -m "refactor: update all imports from alphable_v4 to alphable"
```

---

### Task 5: End-to-End Verification & Fast-Forward Merge into `main`

**Files:**
- Merge: `alphable_V4_paper_base` into `main`

**Interfaces:**
- Produces: Updated and verified `main` branch containing all features, tests, and documentation.

- [ ] **Step 1: Run full test suite on `alphable_V4_paper_base`**

```bash
cd /home/targed/Documents/Git/Alphable
venv/bin/pytest tests/ -v
```
Expected: 186 passed.

- [ ] **Step 2: Check git status is clean**

Run: `git status`
Expected: Working tree clean.

- [ ] **Step 3: Switch to `main` and fast-forward merge**

```bash
cd /home/targed/Documents/Git/Alphable
git checkout main
git merge alphable_V4_paper_base
```
Expected: Fast-forward merge succeeds.

- [ ] **Step 4: Run test suite on `main`**

```bash
cd /home/targed/Documents/Git/Alphable
venv/bin/pytest tests/engine/ tests/models/ tests/search/ -v
```
Expected: All tests pass on `main`.

- [ ] **Step 5: Push `main` and `alphable_V4_paper_base` to origin**

```bash
cd /home/targed/Documents/Git/Alphable
git push origin main
git push origin alphable_V4_paper_base
```
Expected: Both branches pushed to GitHub.

---
