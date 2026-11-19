#!/bin/bash
# ==============================================================================
# Missouri S&T "The Mill" HPC Cluster - SLURM Batch Job Script
# Alphable V4: High-Performance Parallel Tournament & 10,000-Game Evaluation
# ==============================================================================
#
# Resource Request Guidelines for 10,000 Duplicate Games (5,000 Duplicate Pairs):
#   - 16 cores : ~1.6 hours walltime  (--cpus-per-task=16 --time=02:30:00 --mem=16G)
#   - 32 cores : ~48 minutes walltime (--cpus-per-task=32 --time=01:15:00 --mem=32G)
#   - 64 cores : ~24 minutes walltime (--cpus-per-task=64 --time=00:45:00 --mem=64G) [Default]
#   - 128 cores: ~12 minutes walltime (--cpus-per-task=128 --time=00:25:00 --mem=128G)
#
# Submit to SLURM:
#   sbatch slurm/submit_tournament.slurm
#
# Custom Resource Override Example:
#   sbatch --cpus-per-task=32 --time=01:30:00 --mem=32G slurm/submit_tournament.slurm
# ==============================================================================

#SBATCH --job-name=alphable-10k
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --time=10:00:00
#SBATCH --mem=128G
#SBATCH --mail-type=begin,end,fail,requeue
#SBATCH --mail-user=ltkhg4@mst.edu
#SBATCH --export=all
#SBATCH --output=Mill-%j.out
#SBATCH --error=Mill-%j.err

set -e  # Exit immediately if a command exits with a non-zero status

echo "==========================================================================="
echo "   MISSOURI S&T 'THE MILL' - ALPHABLE V4 BATCH TOURNAMENT"
echo "==========================================================================="
echo "SLURM Job ID        : $SLURM_JOB_ID"
echo "SLURM Job Name      : $SLURM_JOB_NAME"
echo "Execution Node      : $(hostname)"
echo "Assigned Cores      : $SLURM_CPUS_PER_TASK"
echo "Working Directory   : $(pwd)"
echo "Start Timestamp     : $(date)"
echo "==========================================================================="

# ------------------------------------------------------------------------------
# 1. Environment & Module Discovery
# ------------------------------------------------------------------------------
echo -e "\n[Step 1/5] Checking Environment Modules..."

# On The Mill, check if environment modules are available
if command -v module >/dev/null 2>&1; then
    # Attempt to load Python 3.11 or modern Python if available
    if module avail python 2>&1 | grep -q "python/3\.11"; then
        echo "Loading module python/3.11.7..."
        module load python/3.11.7 2>/dev/null || module load python/3.11 2>/dev/null || true
    elif module avail python 2>&1 | grep -q "python/3"; then
        PY_MOD=$(module avail python 2>&1 | grep -o 'python/3\.[0-9.]*' | head -n 1)
        echo "Loading module $PY_MOD..."
        module load "$PY_MOD" 2>/dev/null || true
    fi

    # Attempt to load modern GCC (GCC 12.2.0) for native C MAGPIE build
    if module avail gcc 2>&1 | grep -q "gcc/12"; then
        echo "Loading module gcc/12.2.0..."
        module load gcc/12.2.0 2>/dev/null || module load gcc/12 2>/dev/null || true
    elif module avail gcc 2>&1 | grep -q "gcc/"; then
        GCC_MOD=$(module avail gcc 2>&1 | grep -o 'gcc/[0-9.]*' | sort -V | tail -n 1)
        if [ -n "$GCC_MOD" ]; then
            echo "Loading module $GCC_MOD..."
            module load "$GCC_MOD" 2>/dev/null || true
        fi
    fi
else
    echo "No module command found; using host environment."
fi

# Configure C compiler: prefer gcc from environment module or path over default cc
if command -v gcc >/dev/null 2>&1; then
    export CC="$(command -v gcc)"
elif command -v cc >/dev/null 2>&1; then
    export CC="$(command -v cc)"
fi
echo "Using C compiler: $CC ($($CC --version 2>&1 | head -n 1))"

# Ensure Python 3 is accessible
PYTHON_BIN=$(command -v python3 || command -v python || true)
if [ -z "$PYTHON_BIN" ]; then
    echo "ERROR: python3 could not be located in PATH." >&2
    exit 1
fi
echo "Using base Python: $PYTHON_BIN ($($PYTHON_BIN --version))"

# ------------------------------------------------------------------------------
# 2. Virtual Environment Setup & Dependencies
# ------------------------------------------------------------------------------
echo -e "\n[Step 2/5] Bootstrapping Virtual Environment..."

VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    echo "Upgrading pip and installing dependencies..."
    "./$VENV_DIR/bin/pip" install --upgrade pip
    "./$VENV_DIR/bin/pip" install -r requirements.txt
else
    echo "Found existing virtual environment at $VENV_DIR."
fi

VENV_PYTHON="./$VENV_DIR/bin/python"

# ------------------------------------------------------------------------------
# 3. Native C Engine (MAGPIE) Compilation & Cluster Compatibility Patches
# ------------------------------------------------------------------------------
echo -e "\n[Step 3/5] Verifying Native C Engine & Applying Cluster Patches..."

# Apply memory bounding and __has_builtin compatibility patches
"$PYTHON_BIN" scripts/patch_magpie_cluster.py

LIBMAGPIE="vendor/magpie/bin/libmagpie.so"
if [ ! -f "$LIBMAGPIE" ]; then
    echo "Compiling native C library $LIBMAGPIE using $CC..."
    make -C vendor/magpie clean || true
    make -C vendor/magpie CC="$CC" libmagpie
else
    echo "Verified native C engine library exists: $LIBMAGPIE"
fi

# ------------------------------------------------------------------------------
# 4. Neural Network Checkpoint & Data Directory Check
# ------------------------------------------------------------------------------
echo -e "\n[Step 4/5] Verifying Checkpoints & Data Directories..."

CKPT_FILE="alphable/models/checkpoints/v4_value_net_best.pt"
if [ ! -f "$CKPT_FILE" ]; then
    echo "WARNING: Model checkpoint $CKPT_FILE not found."
fi

mkdir -p data/tournaments/checkpoints

# ------------------------------------------------------------------------------
# 5. Execute High-Performance Parallel Tournament
# ------------------------------------------------------------------------------
echo -e "\n[Step 5/5] Launching Parallel Tournament Execution..."

# Enforce strict 1-thread-per-worker execution to prevent CPU over-subscription & thread contention
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export MAGPIE_THREADS=1
export MAGPIE_MAX_MEMORY_MB=512

# Configurable Tournament Parameters (Can be overridden via environment variables)
MODEL="${MODEL:-hybrid-pimc}"
OPPONENT="${OPPONENT:-magpie-tuned}"
GAMES="${GAMES:-10000}"
LEXICON="${LEXICON:-CSW24}"
TAG="${TAG:-10k-hpc}"
WORKERS="${SLURM_CPUS_PER_TASK:-16}"

echo "Tournament Matchup : $MODEL vs $OPPONENT"
echo "Total Games        : $GAMES (Duplicate Mode: $(($GAMES / 2)) symmetric pairs)"
echo "Parallel Workers   : $WORKERS"
echo "Lexicon            : $LEXICON"
echo "Memory / Worker    : MAGPIE_MAX_MEMORY_MB=$MAGPIE_MAX_MEMORY_MB"
echo "Threads / Worker   : MAGPIE_THREADS=$MAGPIE_THREADS, OMP_NUM_THREADS=$OMP_NUM_THREADS"
echo "Fault Recovery     : --resume ENABLED (Incremental Checkpoints in data/tournaments/checkpoints/)"

$VENV_PYTHON -u cli.py tournament \
    --model "$MODEL" \
    --opponent "$OPPONENT" \
    --games "$GAMES" \
    --duplicate \
    --parallel \
    --workers "$WORKERS" \
    --resume \
    --tag "$TAG" \
    --lexicon "$LEXICON"

echo -e "\n==========================================================================="
echo "   TOURNAMENT COMPLETED SUCCESSFULLY"
echo "   Finished Timestamp: $(date)"
echo "   Output Logs Saved : Mill-$SLURM_JOB_ID.out"
echo "==========================================================================="
