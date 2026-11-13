# Running Alphable Tournaments on Missouri S&T "The Mill"

This directory contains automated batch job scripts and configuration for running large-scale, multi-core Scrabble tournaments on the Missouri S&T **The Mill** high-performance computing cluster.

---

## 1. Quick Start

To submit a 10,000-game duplicate tournament between **Alphable V4 Hybrid PIMC** and **Maximally Tuned Base MAGPIE**:

```bash
# Submit standard 64-core job (default configuration)
sbatch slurm/submit_tournament.slurm
```

The script will automatically:
1. Detect and load environment modules (Python 3.11, GCC).
2. Create and configure the virtual environment (`venv/`) if it does not already exist.
3. Verify or compile the native C MAGPIE engine (`vendor/magpie/bin/libmagpie.so`).
4. Launch the parallel multi-process duplicate tournament across all allocated CPU cores.
5. Stream completed match pairs incrementally to disk.
6. Assemble the final publication-ready tournament report and exit immediately upon completion, releasing cluster resources.

---

## 2. Resource Projections for 10,000 Games

Based on empirical benchmarks (**8.67 seconds per game**, 17.34 seconds per duplicate pair, 5,000 duplicate pairs total):

| Cores Requested | SLURM Directive | Expected Runtime | Recommended Walltime | Recommended Memory |
| :--- | :--- | :--- | :--- | :--- |
| **16 cores** | `--cpus-per-task=16` | $\approx 1.6\text{ hours}$ | `#SBATCH --time=02:30:00` | `#SBATCH --mem=16G` |
| **32 cores** | `--cpus-per-task=32` | $\approx 48\text{ minutes}$ | `#SBATCH --time=01:15:00` | `#SBATCH --mem=32G` |
| **64 cores** (Default) | `--cpus-per-task=64` | $\approx 24\text{ minutes}$ | `#SBATCH --time=00:45:00` | `#SBATCH --mem=64G` |
| **128 cores** | `--cpus-per-task=128` | $\approx 12\text{ minutes}$ | `#SBATCH --time=00:25:00` | `#SBATCH --mem=128G` |

> [!NOTE]
> SLURM only allocates and accounts for walltime while the job is actually executing. When the script terminates, the allocation is freed immediately.

---

## 3. Customizing Tournament Submissions

You can override hardware requests and tournament parameters directly from the command line without modifying the script file:

### Override CPU Cores and Walltime
```bash
# Request 32 cores for 1 hour 30 minutes
sbatch --cpus-per-task=32 --time=01:30:00 --mem=32G slurm/submit_tournament.slurm
```

### Change Game Count or Matchup
Use environment variables with `--export=ALL,...`:
```bash
# Run a quick 1,000-game test between V4 Champion and Base MAGPIE
sbatch --cpus-per-task=16 --time=00:30:00 \
    --export=ALL,GAMES=1000,MODEL=latest,OPPONENT=magpie,TAG=v4-vs-magpie-1k \
    slurm/submit_tournament.slurm
```

---

## 4. Fault Tolerance & Automatic Resumption

Cluster preemption, node failures, or walltime expirations will **never lose progress**:
* Completed pairs are written atomically to:
  `data/tournaments/checkpoints/<model>_vs_<opponent>_<tag>.checkpoint.jsonl`
* If a job ends prematurely at pair 3,200 of 5,000, submitting the job again with `sbatch slurm/submit_tournament.slurm` will read the checkpoint, skip all 3,200 finished pairs, and run only the remaining 1,800 pairs.

---

## 5. Monitoring & Job Management

```bash
# View active jobs for your user
squeue -u $USER

# Follow live tournament output stream
tail -f Mill-<job_id>.out

# Inspect job efficiency and execution metrics
sacct -j <job_id> --format=JobID,JobName,AllocCPUS,Elapsed,State,ExitCode

# Cancel a running job
scancel <job_id>
```

---

## 6. Viewing Tournament Results

Once the run completes, inspect the telemetry and statistical analysis using the Alphable CLI:

```bash
# List historical tournament runs
./venv/bin/python cli.py history

# View full breakdown of the latest run
./venv/bin/python cli.py history --show <run_id>
```
