# Alphable V4 Repository Restructuring & Promotion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the Alphable repository into a clean, modern, championship-tier Scrabble AI research repository by archiving historical V1–V3 versions on a dedicated branch and promoting Alphable V4 to the root package structure.

**Architecture:** Create an archive branch and tag for full historical preservation, prune legacy directories from `main`, move `Alphable_V4` components into a standard root Python package (`alphable_v4/`) with top-level CLI, tests, docs, and datasets while safeguarding untracked vendor binaries, and update visualizer studio adapters and services to interface with the unified root package.

**Tech Stack:** Python 3.10+, PyTorch, C (GCC/Make for MAGPIE), Cython, Flask, React/TypeScript (Visualizer), Git.

**Spec:** [docs/superpowers/specs/2026-11-03-repo-restructuring-v4-promotion-design.md](file:///home/targed/Documents/Git/Alphable/docs/superpowers/specs/2026-11-03-repo-restructuring-v4-promotion-design.md)

## Global Constraints

- **Python Floor:** `>=3.10`
- **Core Package Directory:** `alphable_v4/` at repository root
- **Preservation Branch:** `archive/legacy-monorepo`
- **Preservation Tag:** `archive-monorepo-v1-v3`
- **Native Engine Path:** `vendor/magpie/bin/libmagpie.so` (Linux) / `libmagpie.dylib` (macOS)
- **Official Lexica:** `resources/CSW24.txt` and `resources/NWL23.txt`
- **Visualizer Compatibility:** `visualizer/` remains at repository root and must continue functioning with root `alphable_v4`

---

### Task 1: Preservation Branching & Tagging

**Files:**
- Modify: `.git` (branches and tags)

**Interfaces:**
- Consumes: Current git `HEAD` commit (`d5f3fa7`)
- Produces: `archive/legacy-monorepo` branch and `archive-monorepo-v1-v3` tag

- [ ] **Step 1: Check git working tree clean state**

Run:
```bash
git status
```
Expected: Working tree clean on branch `main`.

- [ ] **Step 2: Create archive branch**

Run:
```bash
git branch archive/legacy-monorepo HEAD
```
Expected: Branch `archive/legacy-monorepo` created.

- [ ] **Step 3: Create annotated tag**

Run:
```bash
git tag -a archive-monorepo-v1-v3 -m "Monorepo baseline preserving Alphable V1, V2, and V3"
```
Expected: Tag `archive-monorepo-v1-v3` created.

- [ ] **Step 4: Verify branch and tag exist and point to expected commit**

Run:
```bash
git log -n 1 --oneline archive/legacy-monorepo && git tag -l -n1 archive-monorepo-v1-v3
```
Expected: Output shows commit matching `HEAD` with tag annotation.

---

### Task 2: Clean Stale Root Artifacts & Retire Legacy Versions on `main`

**Files:**
- Delete: `Alphable_V1/`, `Alphable_V2/`, `Alphable_V3/`
- Delete: `structure.c`, `structure.cpython-311-x86_64-linux-gnu.so`, `alphable_v4_implementation_plan.md`, `eval/`, `build/`
- Create: `docs/papers/2511.07312v2.pdf`
- Remove: `2511.07312v2.pdf` from root

**Interfaces:**
- Consumes: Legacy files tracked in git
- Produces: Cleaned root workspace with legacy code removed from `main`

- [ ] **Step 1: Organize reference research paper**

Run:
```bash
mkdir -p docs/papers
git mv 2511.07312v2.pdf docs/papers/2511.07312v2.pdf
```
Expected: Paper moved to `docs/papers/`.

- [ ] **Step 2: Remove legacy version directories from git index**

Run:
```bash
git rm -rf Alphable_V1 Alphable_V2 Alphable_V3
```
Expected: `Alphable_V1`, `Alphable_V2`, and `Alphable_V3` removed from index.

- [ ] **Step 3: Remove obsolete root-level files and stale build debris**

Run:
```bash
git rm -f alphable_v4_implementation_plan.md
rm -rf build/ eval/ structure.c structure.cpython-311-x86_64-linux-gnu.so
```
Expected: Stale files and directories removed.

- [ ] **Step 4: Commit legacy pruning**

Run:
```bash
git commit -m "chore: archive legacy V1-V3 code and clean stale root artifacts"
```
Expected: Commit successful on `main`.

---

### Task 3: Promote Alphable_V4 Core Package and Assets to Root

**Files:**
- Create: `alphable_v4/` (concrete package directory)
- Create: `alphable_v4/search/__init__.py`
- Move: `Alphable_V4/engine/` -> `alphable_v4/engine/`
- Move: `Alphable_V4/models/` -> `alphable_v4/models/`
- Move: `Alphable_V4/search/` -> `alphable_v4/search/`
- Move: `Alphable_V4/platform/` -> `alphable_v4/platform/`
- Move: `Alphable_V4/training/` -> `alphable_v4/training/`
- Move: `Alphable_V4/__init__.py` -> `alphable_v4/__init__.py`
- Move: `Alphable_V4/cli.py` -> `cli.py`
- Move: `Alphable_V4/tests/` -> `tests/`
- Move: `Alphable_V4/docs/*` -> `docs/`
- Move: `Alphable_V4/data/*` -> `data/`
- Move: `Alphable_V4/resources/*` -> `resources/`
- Move: `Alphable_V4/scratch/*` -> `scratch/`
- Move: `Alphable_V4/pyproject.toml` -> `pyproject.toml`
- Move: `Alphable_V4/requirements.txt` -> `requirements.txt`
- Move: `Alphable_V4/install.sh` -> `install.sh`
- Move: `Alphable_V4/README.md` -> `README.md`
- Move untracked: `Alphable_V4/vendor/` -> `vendor/`
- Move untracked: `Alphable_V4/models/checkpoints/v4_value_net_best_full_training.pt` -> `alphable_v4/models/checkpoints/`
- Remove: `Alphable_V4/alphable_v4` (old symlink) and empty `Alphable_V4/`

**Interfaces:**
- Consumes: `Alphable_V4/` contents
- Produces: Promoted top-level repository structure with valid `alphable_v4` package

- [ ] **Step 1: Move untracked vendor and checkpoint assets safely**

Run:
```bash
mv Alphable_V4/vendor .
if [ -f Alphable_V4/models/checkpoints/v4_value_net_best_full_training.pt ]; then
  mkdir -p /tmp/alphable_ckpt_backup
  cp Alphable_V4/models/checkpoints/v4_value_net_best_full_training.pt /tmp/alphable_ckpt_backup/
fi
```
Expected: `vendor/` moved to repo root; checkpoint safely backed up.

- [ ] **Step 2: Create root package directory and move python submodules**

Run:
```bash
mkdir -p alphable_v4
git mv Alphable_V4/engine alphable_v4/engine
git mv Alphable_V4/models alphable_v4/models
git mv Alphable_V4/search alphable_v4/search
git mv Alphable_V4/platform alphable_v4/platform
git mv Alphable_V4/training alphable_v4/training
git mv Alphable_V4/__init__.py alphable_v4/__init__.py
touch alphable_v4/search/__init__.py
git add alphable_v4/search/__init__.py
```
Expected: Core modules moved into `alphable_v4/` with `alphable_v4/search/__init__.py` added.

- [ ] **Step 3: Restore full-training checkpoint into alphable_v4/models/checkpoints/**

Run:
```bash
if [ -f /tmp/alphable_ckpt_backup/v4_value_net_best_full_training.pt ]; then
  mv /tmp/alphable_ckpt_backup/v4_value_net_best_full_training.pt alphable_v4/models/checkpoints/
  rmdir /tmp/alphable_ckpt_backup
fi
```
Expected: Untracked checkpoint restored in `alphable_v4/models/checkpoints/`.

- [ ] **Step 4: Move top-level scripts, tests, data, resources, docs, and configs**

Run:
```bash
git mv Alphable_V4/cli.py cli.py
git mv Alphable_V4/tests tests
git mv Alphable_V4/scratch scratch
git mv Alphable_V4/pyproject.toml pyproject.toml
git mv Alphable_V4/requirements.txt requirements.txt
git mv Alphable_V4/install.sh install.sh
git mv Alphable_V4/README.md README.md

# Merge docs, data, and resources
for f in Alphable_V4/docs/*; do
  git mv "$f" docs/
done

mkdir -p data resources
for f in Alphable_V4/data/*; do
  git mv "$f" data/
done

for f in Alphable_V4/resources/*; do
  git mv "$f" resources/
done
```
Expected: All top-level directories populated with V4 files.

- [ ] **Step 5: Clean up old symlink and remove empty Alphable_V4 folder**

Run:
```bash
rm -f Alphable_V4/alphable_v4
rmdir Alphable_V4
```
Expected: `Alphable_V4` directory completely removed.

- [ ] **Step 6: Commit promoted V4 files**

Run:
```bash
git commit -m "feat: promote Alphable V4 to repository root and establish alphable_v4 package"
```
Expected: Commit created on `main`.

---

### Task 4: Update Configuration, Engine Paths, and Root Tooling

**Files:**
- Modify: `.gitignore`
- Modify: `pyproject.toml`
- Modify: `install.sh`
- Modify: `alphable_v4/engine/magpie_bindings.py:24-50`

**Interfaces:**
- Consumes: Promoted repository paths
- Produces: Correct configuration for git, pytest, pip, and C shared library resolution

- [ ] **Step 1: Update .gitignore for root vendor and data paths**

Edit `.gitignore`:
Replace `/Alphable_V4/vendor/` with `/vendor/`.
Ensure `*_full_training.pt` remains ignored.
Ensure `.coverage`, `.pytest_cache/`, `__pycache__/` are ignored.

Run:
```bash
git add .gitignore
```

- [ ] **Step 2: Update pyproject.toml**

Update `pyproject.toml`:
Ensure `tool.setuptools.packages.find` finds `alphable_v4*`.
Ensure `tool.pytest.ini_options` has:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
norecursedirs = ["vendor", "data", ".git", ".pytest_cache", "visualizer/frontend/node_modules"]
```

Run:
```bash
git add pyproject.toml
```

- [ ] **Step 3: Update install.sh for root execution**

Update `install.sh`:
Ensure `SCRIPT_DIR` runs at the root, installs requirements from `./requirements.txt`, checks `vendor/magpie`, compiles if needed, and runs smoke verification.

Run:
```bash
git add install.sh
```

- [ ] **Step 4: Verify and optimize find_libmagpie() in alphable_v4/engine/magpie_bindings.py**

Verify that `find_libmagpie()` searches:
`os.path.join(base_dir, "..", "vendor", "magpie", "bin", "libmagpie.so")`
and `os.path.join(cwd, "vendor", "magpie", "bin", "libmagpie.so")`.
Both point directly to `vendor/magpie/bin/libmagpie.so` now!

- [ ] **Step 5: Commit configuration and tooling updates**

Run:
```bash
git commit -m "chore: update pyproject.toml, .gitignore, and install.sh for root package"
```
Expected: Commit created on `main`.

---

### Task 5: Update Visualizer Studio Adapters & Backend Services

**Files:**
- Modify: `visualizer/backend/adapters/v4_adapter.py`
- Modify: `visualizer/backend/adapters/baseline_adapter.py`
- Modify: `visualizer/backend/services/replay_service.py`
- Modify: `visualizer/backend/services/dictionary_service.py`
- Modify: `visualizer/backend/adapters/v3_adapter.py`
- Test: `visualizer/tests/`

**Interfaces:**
- Consumes: Root `alphable_v4` package, `data/tournaments/`, `resources/*.txt`
- Produces: Working visualizer studio connecting to root V4 engine

- [ ] **Step 1: Update visualizer/backend/adapters/v4_adapter.py**

Update `v4_adapter.py`:
Point `REPO_ROOT` to `Path(__file__).resolve().parent.parent.parent.parent`.
Ensure `str(REPO_ROOT)` is in `sys.path`.
Directly import `alphable_v4` modules without needing `V4_DIR / "Alphable_V4"`.

- [ ] **Step 2: Update visualizer/backend/adapters/baseline_adapter.py**

Update `baseline_adapter.py`:
Point to `REPO_ROOT` instead of `V4_DIR / "Alphable_V4"`.

- [ ] **Step 3: Update visualizer/backend/services/replay_service.py**

Update `replay_service.py`:
Set `V4_DATA_DIR = REPO_ROOT / "data"`.

- [ ] **Step 4: Update visualizer/backend/services/dictionary_service.py**

Update `dictionary_service.py`:
Set:
```python
CSW24_PATH = BASE_DIR / "resources" / "CSW24.txt"
NWL23_PATH = BASE_DIR / "resources" / "NWL23.txt"
```

- [ ] **Step 5: Verify visualizer/backend/adapters/v3_adapter.py graceful fallback**

Verify `v3_adapter.py`:
If `Alphable_V3` does not exist, it cleanly sets `V3_AVAILABLE = False` without errors.

- [ ] **Step 6: Run visualizer unit tests**

Run:
```bash
pytest visualizer/tests/ -v
```
Expected: All visualizer tests pass (or skipped if optional dependencies like torch in test environment require venv).

- [ ] **Step 7: Commit visualizer adapter updates**

Run:
```bash
git add visualizer/
git commit -m "feat(visualizer): adapt backend services and adapters to root alphable_v4 package"
```
Expected: Commit created on `main`.

---

### Task 6: Full Verification & Repository Health Check

**Files:**
- Test: `tests/`
- Test: `visualizer/tests/`
- Test: `cli.py`

**Interfaces:**
- Consumes: All updated root packages and configurations
- Produces: Fully verified Alphable V4 research repository

- [ ] **Step 1: Test Python import and Magpie C engine initialization**

Run:
```bash
python3 -c "import alphable_v4; print('Package version:', alphable_v4.__version__ if hasattr(alphable_v4, '__version__') else 'alphable_v4 loaded')"
```
Expected: Success.

- [ ] **Step 2: Test native MAGPIE shared library resolution**

Run:
```bash
python3 -c "from alphable_v4.engine.magpie_bindings import MagpieEngine; e = MagpieEngine(); print('MAGPIE initialized successfully: handle=', e._handle)"
```
Expected: Success.

- [ ] **Step 3: Verify CLI models catalog**

Run:
```bash
python3 cli.py models
```
Expected: Displays table of registered models (`latest`, `5-frontiers`, `v4-scaled`, `v4-baseline`, `ablation-no-nn`, `base-magpie`).

- [ ] **Step 4: Verify test suite execution**

Run:
```bash
pytest tests/platform/test_cli.py -v
```
Expected: Tests pass.

- [ ] **Step 5: Check git status and branch integrity**

Run:
```bash
git status
git branch -v
git tag -l
```
Expected:
- `main` working tree clean.
- `archive/legacy-monorepo` branch exists.
- `archive-monorepo-v1-v3` tag exists.

- [ ] **Step 6: Final commit if any adjustments were made**

Run:
```bash
git status
```
Expected: Clean working tree.
