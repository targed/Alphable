# Parallel Tournaments and Missouri S&T "The Mill" SLURM Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parallelize duplicate Scrabble tournaments across multi-core CPU nodes with incremental checkpointing, and provide a self-bootstrapping SLURM batch job suite for Missouri S&T's "The Mill" supercomputer.

**Architecture:** 
1. `TournamentCheckpointManager` in `alphable_v4/platform/checkpoint.py`: atomic append-only JSONL streaming for duplicate pairs with resumption capability.
2. `run_parallel_duplicate_tournament()` in `alphable_v4/platform/eval.py`: process-isolated multi-worker simulation via `concurrent.futures.ProcessPoolExecutor`, isolating native `libmagpie.so` C state per worker process.
3. CLI exposure in `alphable_v4/cli.py` via `--parallel`, `--workers`, and `--resume` flags.
4. `slurm/submit_tournament.slurm`: self-bootstrapping SLURM submission script targeting The Mill's environment (module loads, venv bootstrap, native build, automated resource scaling).

**Tech Stack:** Python 3.10+, `concurrent.futures.ProcessPoolExecutor`, `ctypes` (`libmagpie.so`), SLURM Workload Manager, Linux Bash.

**Spec:** Missouri S&T IT RSS "The Mill" HPC guidelines; Scrabble paired duplicate tournament protocol with seed spacing $S_k = 1000 + 31k$.

## Global Constraints
- Native C library `libmagpie.so` has global state; workers must run in separate OS processes (multiprocessing, not multithreading).
- Incremental checkpoint writes must be atomic and flushed (`fsync`) to survive cluster preemption.
- Zero regressions across existing 196 test cases.
- Python 3.10+ compatibility across Linux environments.

---

### Task 1: Incremental Tournament Checkpoint System

**Files:**
- Create: `alphable_v4/platform/checkpoint.py`
- Test: `tests/platform/test_checkpoint.py`

**Interfaces:**
- Produces: `TournamentCheckpointManager`
  - `__init__(checkpoint_path: Path, metadata: Dict[str, Any])`
  - `record_pair(pair_record: Dict[str, Any]) -> None`
  - `load_completed_pairs() -> Tuple[Set[int], List[Dict[str, Any]]]`
  - `is_resumable() -> bool`
  - `finalize(final_json_path: Path) -> None`

- [ ] **Step 1: Write unit tests for `TournamentCheckpointManager`**
  Create `tests/platform/test_checkpoint.py` covering:
  - Fresh checkpoint initialization with metadata header.
  - Appending completed pair records atomically.
  - Loading completed pairs on resume (detecting finished seeds).
  - Resumption skipping already completed seeds.
  - Finalizing into master tournament JSON.

- [ ] **Step 2: Run test to confirm it fails**
  Run: `./venv/bin/pytest tests/platform/test_checkpoint.py -v` (fails with `ModuleNotFoundError`).

- [ ] **Step 3: Implement `TournamentCheckpointManager` in `alphable_v4/platform/checkpoint.py`**
  Implement:
  - JSONL format: line 1 is run metadata (schema, run_id, model specs, total pairs). Lines 2+ are JSON objects for each completed pair.
  - Atomic flush: `file.write(... + "\n"); file.flush(); os.fsync(file.fileno())`.
  - Checkpoint discovery and validation.

- [ ] **Step 4: Run tests and ensure 100% pass**
  Run: `./venv/bin/pytest tests/platform/test_checkpoint.py -v`.

- [ ] **Step 5: Git commit**
  Commit checkpoint module with clean commit message.

---

### Task 2: Parallel Duplicate Tournament Engine

**Files:**
- Modify: `alphable_v4/platform/eval.py`
- Test: `tests/platform/test_parallel_tournament.py`

**Interfaces:**
- Consumes: `TournamentCheckpointManager` from `alphable_v4/platform/checkpoint.py`.
- Produces: `run_parallel_duplicate_tournament(...)` in `alphable_v4/platform/eval.py`.
  - Signature:
    ```python
    def run_parallel_duplicate_tournament(
        p1_spec: str,
        p2_spec: str,
        num_pairs: int,
        workers: int = 4,
        lexicon: str = "CSW24",
        device: str = "cpu",
        start_seed: int = 1000,
        seed_stride: int = 31,
        p1_kwargs: Optional[Dict[str, Any]] = None,
        p2_kwargs: Optional[Dict[str, Any]] = None,
        checkpoint_path: Optional[str] = None,
        resume: bool = False,
        verbose: bool = True,
    ) -> Dict[str, Any]:
    ```

- [ ] **Step 1: Write unit tests for parallel worker and execution**
  Create `tests/platform/test_parallel_tournament.py` covering:
  - Multi-worker execution with 2 workers playing 2 duplicate pairs (4 games total).
  - Verification that results match sequential duplicate pair results with identical seeds.
  - Resumption from a partial checkpoint (pairs 1 completed, resuming executes only pair 2).
  - Process isolation (no ctypes crashes or state leakage across workers).

- [ ] **Step 2: Run test to confirm it fails**
  Run: `./venv/bin/pytest tests/platform/test_parallel_tournament.py -v`.

- [ ] **Step 3: Implement parallel engine in `alphable_v4/platform/eval.py`**
  - Implement top-level picklable worker function `_run_pair_worker(task: Tuple[...]) -> Dict[str, Any]` that creates its own isolated `MagpieEngine`, builds policies, and executes Game A + Game B.
  - Implement `run_parallel_duplicate_tournament()` using `concurrent.futures.ProcessPoolExecutor`.
  - Integrate `TournamentCheckpointManager` to stream pairs to disk as they complete.
  - Calculate summary stats, paired t-test, 95% confidence intervals, and phase breakdowns.

- [ ] **Step 4: Run tests to verify implementation**
  Run: `./venv/bin/pytest tests/platform/test_parallel_tournament.py -v`.

- [ ] **Step 5: Git commit**
  Commit parallel tournament runner.

---

### Task 3: CLI Integration (`cli.py`)

**Files:**
- Modify: `alphable_v4/cli.py`
- Test: `tests/platform/test_cli_parallel.py`

**Interfaces:**
- Consumes: `run_parallel_duplicate_tournament` from `alphable_v4/platform/eval.py`.
- Produces: CLI flags `--parallel`, `--workers <N>`, `--resume`, and `--checkpoint <path>` for `tournament` subcommand.

- [ ] **Step 1: Write CLI integration test**
  Create `tests/platform/test_cli_parallel.py` testing:
  - Invoking `cmd_tournament` with `--parallel --workers 2 --games 2 --duplicate`.
  - Testing `--resume` behavior with an existing checkpoint.

- [ ] **Step 2: Run test to confirm it fails**
  Run: `./venv/bin/pytest tests/platform/test_cli_parallel.py -v`.

- [ ] **Step 3: Update `alphable_v4/cli.py`**
  - Add argument parser flags: `--parallel` (store_true), `--workers` (int, default=os.cpu_count()), `--resume` (store_true), `--checkpoint` (str, default=None).
  - In `cmd_tournament()`, route to `run_parallel_duplicate_tournament()` when `args.parallel` is enabled.
  - Ensure standard summary reporting, telemetry saving, and error handling are preserved.

- [ ] **Step 4: Run CLI tests and full test suite**
  Run: `./venv/bin/pytest tests/platform/test_cli_parallel.py -v`.

- [ ] **Step 5: Git commit**
  Commit CLI updates.

---

### Task 4: Missouri S&T "The Mill" SLURM Job Infrastructure

**Files:**
- Create: `slurm/submit_tournament.slurm`
- Create: `slurm/README.md`
- Test: Syntax and dry-run validation

- [ ] **Step 1: Write `slurm/submit_tournament.slurm`**
  Create self-bootstrapping bash script:
  - SLURM directives: `#SBATCH --job-name=alphable-tourney`, `#SBATCH --ntasks=1`, `#SBATCH --cpus-per-task=64`, `#SBATCH --mem=64G`, `#SBATCH --time=01:00:00`, `#SBATCH --mail-type=begin,end,fail,requeue`, `#SBATCH --export=all`, `#SBATCH --output=Mill-%j.out`, `#SBATCH --error=Mill-%j.err`.
  - Environment bootstrap: checks `module load python/3.11` or available GCC/Python module; falls back to system Python if already loaded.
  - Venv bootstrap: checks `[ -d "venv" ]`; if missing, creates `venv` and runs `pip install -r requirements.txt`.
  - Build check: checks `[ -f "vendor/magpie/bin/libmagpie.so" ]`; if missing, runs `make -C vendor/magpie libmagpie`.
  - Execution: launches `./venv/bin/python cli.py tournament --model hybrid-pimc --opponent magpie-tuned --games 10000 --duplicate --parallel --workers ${SLURM_CPUS_PER_TASK:-16} --resume`.
  - Clean exit: saves final report and exits immediately so SLURM releases compute allocation.

- [ ] **Step 2: Write `slurm/README.md`**
  Write complete documentation:
  - Submitting jobs: `sbatch slurm/submit_tournament.slurm`
  - Overriding cores and games: `sbatch --cpus-per-task=32 --time=01:30:00 slurm/submit_tournament.slurm`
  - Checking status: `squeue -u $USER`, checking live output: `tail -f Mill-<jobid>.out`
  - Preemption and recovery: how `--resume` resumes from checkpoints automatically.
  - Resource estimation table for 10k games across 16, 32, 64, 128 cores.

- [ ] **Step 3: Validate shell syntax**
  Run: `bash -n slurm/submit_tournament.slurm`.

- [ ] **Step 4: Git commit**
  Commit SLURM infrastructure.

---

### Task 5: End-to-End Verification & Verification Before Completion

- [ ] **Step 1: Run complete test suite**
  Run: `./venv/bin/pytest tests/ -v` and verify all tests pass (existing 196 + new tests).

- [ ] **Step 2: Run live parallel duplicate match test via CLI**
  Run: `./venv/bin/python cli.py tournament --model hybrid-pimc --opponent magpie-tuned --games 4 --duplicate --parallel --workers 2`
  Confirm parallel execution, clean scoring, and correct telemetry.

- [ ] **Step 3: Verify git status and commit cleanliness**
  Confirm branch `alphable_V4_paper_base` is clean and ready.
