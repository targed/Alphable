#!/usr/bin/env bash
# ==============================================================================
# Alphable V4: Automated Environment Setup & Compilation Script
# Supports: Linux (Ubuntu/Debian/Fedora/Arch) and macOS (Apple Silicon / Intel)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==========================================================================="
echo "   ALPHABLE V4: AUTOMATED SETUP & INSTALLATION"
echo "==========================================================================="
echo "Project Directory: $SCRIPT_DIR"
echo ""

# ------------------------------------------------------------------------------
# 1. Python Version Check (>= 3.10 required)
# ------------------------------------------------------------------------------
echo "==> Step 1: Checking Python Version..."

PYTHON_BIN=""
for candidate in python3 python python3.11 python3.12 python3.10; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PY_VER=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || true)
        MAJOR=$(echo "$PY_VER" | cut -d. -f1)
        MINOR=$(echo "$PY_VER" | cut -d. -f2)
        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 10 ]; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "ERROR: Python 3.10 or higher is required to run Alphable V4."
    echo "Please install Python 3.10+ (via pyenv, apt, brew, or conda) and re-run this script."
    exit 1
fi

echo "✓ Found compatible Python: $PYTHON_BIN ($($PYTHON_BIN --version))"

# ------------------------------------------------------------------------------
# 2. Virtual Environment Setup
# ------------------------------------------------------------------------------
echo ""
echo "==> Step 2: Setting Up Virtual Environment..."

VENV_DIR="$SCRIPT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    echo "✓ Created virtual environment."
else
    echo "✓ Found virtual environment at $VENV_DIR"
fi

# Activate venv
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
VENV_PYTHON="$VENV_DIR/bin/python"

# ------------------------------------------------------------------------------
# 3. Python Package Installation
# ------------------------------------------------------------------------------
echo ""
echo "==> Step 3: Installing Python Dependencies..."
"$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel --quiet
"$VENV_PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
echo "✓ Python dependencies installed successfully."

# ------------------------------------------------------------------------------
# 4. MAGPIE Engine Compilation
# ------------------------------------------------------------------------------
echo ""
echo "==> Step 4: Checking MAGPIE C Engine Shared Library..."

MAGPIE_DIR="$SCRIPT_DIR/vendor/magpie"
SO_FILE="$MAGPIE_DIR/bin/libmagpie.so"
DYLIB_FILE="$MAGPIE_DIR/bin/libmagpie.dylib"

if [ -d "$MAGPIE_DIR" ]; then
    "$PYTHON_BIN" "$SCRIPT_DIR/scripts/patch_magpie_cluster.py"

    if [ ! -f "$SO_FILE" ] && [ ! -f "$DYLIB_FILE" ]; then
        echo "Building native MAGPIE shared library ('make libmagpie')..."
        make -C "$MAGPIE_DIR" CC="${CC:-gcc}" libmagpie
        echo "✓ Compiled native MAGPIE shared library."
    else
        echo "✓ MAGPIE shared library is already compiled."
    fi
fi

# ------------------------------------------------------------------------------
# 5. Checkpoints Verification
# ------------------------------------------------------------------------------
echo ""
echo "==> Step 5: Verifying Neural Network Checkpoints..."

VALUE_CKPT="$SCRIPT_DIR/alphable_v4/models/checkpoints/v4_value_net_best.pt"
BELIEF_CKPT="$SCRIPT_DIR/alphable_v4/models/checkpoints/v4_belief_net_best.pt"

if [ -f "$VALUE_CKPT" ] && [ -f "$BELIEF_CKPT" ]; then
    echo "✓ Value Network Checkpoint present: $(basename "$VALUE_CKPT") ($("$VENV_PYTHON" -c "import os; print(f'{os.path.getsize(\"$VALUE_CKPT\")/(1024*1024):.1f} MB')"))"
    echo "✓ Belief Network Checkpoint present: $(basename "$BELIEF_CKPT")"
else
    echo "WARNING: One or more model checkpoints are missing from alphable_v4/models/checkpoints/."
fi

# ------------------------------------------------------------------------------
# 6. Sanity Smoke Test
# ------------------------------------------------------------------------------
echo ""
echo "==> Step 6: Running Smoke Tests..."
PYTHONPATH="$SCRIPT_DIR" "$VENV_PYTHON" -m pytest "$SCRIPT_DIR/tests/platform/test_cli.py" -q
echo "✓ Smoke tests passed!"

# ------------------------------------------------------------------------------
# Success Banner
# ------------------------------------------------------------------------------
echo ""
echo "==========================================================================="
echo "   🎉 ALPHABLE V4 INSTALLATION COMPLETE & VERIFIED!"
echo "==========================================================================="
echo ""
echo "To begin using Alphable V4, activate your environment:"
echo "   source $VENV_DIR/bin/activate"
echo "   export PYTHONPATH=$SCRIPT_DIR:\$PYTHONPATH"
echo ""
echo "Try out these commands:"
echo "   1. View Model Registry:      python cli.py models"
echo "   2. Analyze Any Rack/Board:   python cli.py analyze --model latest --rack AQRTUYZ"
echo "   3. Play Against V4:          python cli.py play --model latest"
echo "   4. Run a Tournament:         python cli.py tournament --opponent magpie --games 10"
echo "   5. View Historical Runs:     python cli.py history"
echo "   6. Run Full Unit Tests:      pytest tests/ -v"
echo ""
echo "Read the guides in docs/:"
echo "   • docs/GETTING_STARTED.md     -> Complete walkthrough for newcomers"
echo "   • docs/USER_GUIDE.md           -> In-depth command & configuration guide"
echo "   • docs/TOURNAMENT_BENCHMARKS_AND_COMMAND_MANUAL.md -> Master benchmark logs"
echo "==========================================================================="
