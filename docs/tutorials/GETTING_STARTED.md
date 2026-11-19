# Getting started with Alphable V4

This guide covers setting up Alphable V4 from a fresh clone, compiling the native C engine, verifying model weights, and running Scrabble matches and evaluations.

---

## 1. System requirements

| Component | Minimum | Recommended |
| :--- | :--- | :--- |
| Operating System | Linux (Ubuntu 20.04+, Debian, Fedora, Arch), macOS (12.0+), or Windows (WSL2) | Ubuntu 22.04 LTS or macOS (Apple Silicon) |
| Python | 3.10 | 3.11 or 3.12 |
| C Compiler | GCC 9+ or Clang 11+ (`make` required) | Modern GCC or Clang |
| Memory (RAM) | 4 GB | 8 GB+ |
| GPU (Optional) | CPU execution supported natively | NVIDIA GPU with CUDA 11.8+ or 12.0+ |

---

## 2. Automated installation

Run the automated installer from the repository root:

```bash
chmod +x install.sh
./install.sh
```

The installer performs these steps:
1. Verifies a compatible Python 3.10+ runtime.
2. Creates and activates an isolated virtual environment (`venv`).
3. Installs dependencies (`torch`, `numpy`, `scipy`, `pandas`, `tqdm`, `requests`, `pyarrow`, `pytest`).
4. Compiles the native C MAGPIE solver (`vendor/magpie/bin/libmagpie.so` or `libmagpie.dylib`).
5. Confirms that neural network checkpoints exist in `alphable/models/checkpoints/`.
6. Runs smoke tests to verify move generation and policy loading.

---

## 3. Manual installation

If you prefer to configure the environment manually instead of running `install.sh`:

### Step 1: Create and activate virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install Python dependencies
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Step 3: Compile the native MAGPIE C engine
Alphable V4 uses MAGPIE for legal move generation:
```bash
# Clone MAGPIE if vendor/magpie is not yet populated
if [ ! -d "vendor/magpie/src" ]; then
    git clone https://github.com/jvc56/MAGPIE.git vendor/magpie
fi

# Build the shared library (generates bin/libmagpie.so on Linux or bin/libmagpie.dylib on macOS)
make -C vendor/magpie libmagpie
```

### Step 4: Verify the installation
Run the test suite to confirm that the C engine, neural weights, and BAMS search function properly:
```bash
pytest tests/ -v
```
All 59 unit and integration tests should pass.

---

## 4. Core commands

Activate the virtual environment before running commands:

```bash
source venv/bin/activate
```

All commands run through `cli.py` or `./cli.py` from the repository root:

### 1. Inspect available models and presets
```bash
python cli.py models
```
Lists registered checkpoints, parameters, and verified tournament ratings:
- `latest`: Calibrated Scaled 2-Ply search with volatility control (56.7% win rate vs Base MAGPIE)
- `5-frontiers`: 1,000-game benchmark baseline with pre-endgame parity and belief tracking (54.2% win rate vs Base MAGPIE)
- `rl-gen1`: Policy gradient fine-tuning with anchored teacher loss
- `scaled`: 2-ply lookahead ($K=12, N=20$)
- `v4-baseline`: 1-ply reference model (52.2% win rate)
- `static-magpie`: Classical C solver using static KLV tables (no neural evaluation)

### 2. Analyze a board position
Compare static MAGPIE evaluation with Alphable V4 BAMS evaluation:
```bash
# Analyze an opening rack
python cli.py analyze --model latest --rack "AQRTUYZ"

# Analyze a mid-game position with an existing board word
python cli.py analyze --model latest --rack "TRAINER" --board-word "QUIZ" --board-coord "8D"
```
The output displays:
- Candidate rank and coordinates
- Immediate score and rack leave
- Base MAGPIE static equity
- Monte Carlo opponent counter-threat estimate
- ResNet-18 board control score
- Final BAMS selection and divergence indicator

### 3. Play an interactive game in the terminal
```bash
python cli.py play --model latest
```
- Enter moves using standard Scrabble notation: `8H CATS` or `H8 CATS`.
- Use `-ABC` to exchange tiles.
- Type `hint` to view move recommendations with score breakdowns.
- Type `pass` to pass or `quit` to exit.

### 4. Run tournaments
Benchmark models against Base MAGPIE or each other:
```bash
# 10 games with alternating first turns
python cli.py tournament --opponent magpie --games 10

# Duplicate tournament with paired seeds and swapped seats to eliminate tile luck
python cli.py tournament --model latest --opponent magpie --games 10 --duplicate
```
Each tournament reports:
- Win rate with 95% confidence intervals
- Score differential with 95% confidence intervals
- Paired two-tailed t-test and p-value
- Saved telemetry in `data/tournaments/`

### 5. Inspect tournament history
Review previous tournament runs recorded in the persistent ledger:
```bash
# View summary ledger
python cli.py history

# Inspect details for a specific run
python cli.py history --show run_20261015_215837

# Compare two runs side-by-side with statistical deltas
python cli.py history --compare run_20261013_143000 run_20261015_215837
```

### 6. Launch the visualizer studio
Start the web interface to view games and move evaluations:
```bash
./start_visualizer.sh
# or: cd visualizer && ./run.sh
```
Open `http://localhost:5000` in your browser.

---

## 5. Troubleshooting

### `FileNotFoundError: Could not find libmagpie.so`
The C engine has not been compiled yet. Run `make -C vendor/magpie libmagpie` or `./install.sh`. Verify that `build-essential` (Linux) or Xcode command-line tools (macOS) are installed.

### Running without a GPU
Alphable V4 runs on CPU by default when CUDA is unavailable. To force CPU execution explicitly:
```bash
python cli.py tournament --opponent magpie --games 10 --device cpu
```

### Choosing a lexicon
Alphable V4 defaults to CSW24 (Collins Scrabble Words 2024). To use North American rules (NWL23):
```bash
python cli.py analyze --lexicon NWL23 --rack "RETINAS"
python cli.py tournament --lexicon NWL23 --games 20
```

### Additional documentation
- [ARCHITECTURE.md](../reference/ARCHITECTURE.md): BAMS formulation, tensor representations, and ResNet-18 architecture.
- [USER_GUIDE.md](../how_to/USER_GUIDE.md): CLI commands, search parameters, and tuning flags.
- [TOURNAMENT_BENCHMARKS_AND_COMMAND_MANUAL.md](../reference/TOURNAMENT_BENCHMARKS_AND_COMMAND_MANUAL.md): Historical benchmark logs and model registry details.
- [STATISTICAL_SIGNIFICANCE_AND_BENCHMARKING_GUIDE.md](../explanation/STATISTICAL_SIGNIFICANCE_AND_BENCHMARKING_GUIDE.md): Statistical methodology and duplicate match configuration.
