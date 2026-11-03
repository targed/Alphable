# Getting Started with Alphable V4

This guide walks you through setting up Alphable V4 from a fresh clone, compiling the native C engine, verifying model weights, and running your first Scrabble matches.

---

## 1. System Requirements

| Component | Minimum | Recommended |
| :--- | :--- | :--- |
| **Operating System** | Linux (Ubuntu 20.04+, Debian, Fedora, Arch) or macOS (12.0+) or Windows (via WSL2) | Ubuntu 22.04 LTS or macOS (Apple Silicon M-series) |
| **Python** | 3.10 | 3.11 or 3.12 |
| **C/C++ Compiler** | GCC 9+ or Clang 11+ (`make` required) | Modern GCC / Clang |
| **Memory (RAM)** | 4 GB | 8 GB+ |
| **GPU (Optional)** | CPU execution supported natively | NVIDIA GPU with CUDA 11.8+ / 12.0+ (for sub-2ms tensor inference) |

---

## 2. One-Command Automated Setup

From inside the `Alphable_V4` directory, run the automated installation script:

```bash
cd Alphable_V4
chmod +x install.sh
./install.sh
```

### What this script does:
1. Detects Python 3.10+ on your system.
2. Creates and activates an isolated virtual environment (`venv`).
3. Installs all required dependencies (`torch`, `numpy`, `scipy`, `pandas`, `tqdm`, `requests`, `pyarrow`, `pytest`).
4. Compiles the native C MAGPIE solver (`vendor/magpie/bin/libmagpie.so` or `libmagpie.dylib`).
5. Checks model weight checkpoints in `models/checkpoints/`.
6. Executes smoke tests to verify move generation and policy loading.

---

## 3. Manual Step-by-Step Installation

If you prefer to configure your environment manually instead of running `install.sh`:

### Step 1: Create and Activate Virtual Environment
```bash
cd Alphable_V4
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install Python Dependencies
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Step 3: Compile the Native MAGPIE C Engine
Alphable V4 uses MAGPIE for sub-millisecond legal move generation:
```bash
# If vendor/magpie is empty, clone it:
if [ ! -d "vendor/magpie/src" ]; then
    git clone https://github.com/jvc56/MAGPIE.git vendor/magpie
fi

# Build the shared library (generates bin/libmagpie.so on Linux or bin/libmagpie.dylib on macOS):
make -C vendor/magpie libmagpie
```

### Step 4: Verify Your Installation
Run the unit test suite to verify that the C engine, neural weights, and BAMS search are working together:
```bash
export PYTHONPATH=.
pytest tests/ -v
```
All 59 unit tests should pass.

---

## 4. Your First 5 Minutes: Core Commands

All CLI commands are executed through `cli.py`:

```bash
# Ensure your environment is active and PYTHONPATH is set:
source venv/bin/activate
export PYTHONPATH=.
```

### 1. Inspect Available Models and Presets
```bash
python cli.py models
```
Displays all registered checkpoints, parameters, and verified tournament ratings:
- `latest`: Calibrated Scaled 2-Ply + Volatility (⭐ Production Champion)
- `5-frontiers`: Verified 1,000-Game Benchmark Model (54.2% Win Rate vs Base MAGPIE)
- `rl-gen1`: Anchored Self-Play Policy Gradient checkpoint
- `scaled`: Grandmaster deep 2-ply lookahead ($K=12, N=20$)
- `v4-baseline`: 1-Ply reference model ($52.2\%$ WR)
- `static-magpie`: Classical C-based KLV solver (zero neural evaluation)

---

### 2. Analyze Any Board Position
Compare what classical Base MAGPIE plays versus what the Alphable V4 AI plays:
```bash
# Analyze an opening rack:
python cli.py analyze --model latest --rack "AQRTUYZ"

# Analyze a mid-game position with an existing board word:
python cli.py analyze --model latest --rack "TRAINER" --board-word "QUIZ" --board-coord "8D"
```
The output displays a side-by-side evaluation table:
- Candidate rank and coordinates
- Immediate score and leave
- Base MAGPIE static equity
- Monte Carlo opponent counter-threat
- ResNet-18 neural board control score
- Final BAMS selection and divergence indicator

---

### 3. Play an Interactive Game in the Terminal
Play a full game of Scrabble against Alphable V4:
```bash
python cli.py play --model latest
```
- Enter moves using standard Scrabble notation: `8H CATS` or `H8 CATS`.
- Type `hint` if you want the AI to suggest a move with equity reasoning.
- Type `pass` to pass or `quit` to exit.

---

### 4. Run a Head-to-Head Tournament
Benchmark the AI against Base MAGPIE or another model:
```bash
# Run 10 games with alternating first turns:
python cli.py tournament --opponent magpie --games 10

# Run a duplicate (pair-swapped) tournament to eliminate tile draw luck:
python cli.py tournament --model latest --opponent magpie --games 10 --duplicate
```
At the end of each tournament, the CLI computes:
- Win rate with 95% Confidence Intervals
- Score differential with 95% Confidence Intervals
- Paired two-tailed t-test and p-value
- Automatic saving to `data/tournaments/`

---

### 5. Inspect and Compare Past Benchmarks
Review all completed tournament runs in the persistent ledger:
```bash
# View the summary ledger of all runs:
python cli.py history

# Inspect full details of a specific run:
python cli.py history --show run_20261015_215837

# Compare two tournament runs side-by-side with mathematical deltas:
python cli.py history --compare run_20261013_143000 run_20261015_215837
```

---

## 5. Troubleshooting & FAQ

### Q: `FileNotFoundError: Could not find libmagpie.so`
**Cause**: The C engine has not been compiled yet.  
**Fix**: Run `make -C vendor/magpie libmagpie` or `./install.sh`. Ensure `build-essential` (Linux) or Xcode CLI tools (macOS) are installed.

### Q: Can I run Alphable V4 on a machine without a GPU?
**Yes.** The Value Network runs on CPU automatically if CUDA is not available. To explicitly force CPU mode:
```bash
python cli.py tournament --opponent magpie --games 10 --device cpu
```

### Q: Which lexicon is used by default?
Alphable V4 defaults to **CSW24** (Collins Scrabble Words 2024, the international standard). To switch to North American rules (**NWL23**):
```bash
python cli.py analyze --lexicon NWL23 --rack "RETINAS"
python cli.py tournament --lexicon NWL23 --games 20
```

### Q: Where do I find the full documentation?
- [ARCHITECTURE.md](file:///home/targed/Documents/Git/Alphable/Alphable_V4/docs/ARCHITECTURE.md): Deep dive into the BAMS search equation and ResNet-18 architecture.
- [USER_GUIDE.md](file:///home/targed/Documents/Git/Alphable/Alphable_V4/docs/USER_GUIDE.md): In-depth guide to all CLI commands, parameters, and tuning flags.
- [TOURNAMENT_BENCHMARKS_AND_COMMAND_MANUAL.md](file:///home/targed/Documents/Git/Alphable/Alphable_V4/docs/TOURNAMENT_BENCHMARKS_AND_COMMAND_MANUAL.md): Full tournament logs and model registry details.
- [STATISTICAL_SIGNIFICANCE_AND_BENCHMARKING_GUIDE.md](file:///home/targed/Documents/Git/Alphable/Alphable_V4/docs/STATISTICAL_SIGNIFICANCE_AND_BENCHMARKING_GUIDE.md): Why Scrabble has high variance and how paired duplicate matches eliminate tile luck.
