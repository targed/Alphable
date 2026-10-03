# Alphable V3

Alphable V3 is a Scrabble RL Engine designed with a modern Python package structure. This document provides a comprehensive overview of the new directory layout, how to set up the development environment, and how to use the new unified CLI tool to run various components like self-play, training, and evaluation.

## Table of Contents
1. [Project Layout](#project-layout)
2. [Setup & Installation](#setup--installation)
3. [Using the Unified CLI](#using-the-unified-cli)
4. [Backward Compatibility](#backward-compatibility)
5. [Visualizer](#visualizer)

## Project Layout

The project has been refactored from a flat script layout to a structured Python package (`alphable`) to improve maintainability, reduce hardcoded file-based imports, and provide a single robust entrypoint.

### Codebase Structure

- **`src/alphable/`**: The main Python package containing all pure modules and command logic.
  - **`cli/`**: Contains the central CLI router (`main.py`).
  - **`core/`**: Core Scrabble logic, simulator, structure extensions, inference mechanisms, and neural network definitions (`alphable_net.py`).
  - **`data/`**: Dataset processing logic and PyTorch DataLoader definitions.
  - **`eval/`**: Evaluation scripts (matches, baselines vs greedy/random).
  - **`logging/`**: Game logging utilities.
  - **`pipeline/`**: The automated RL calibration cycle logic.
  - **`training/`**: Logic for dataset preparation, supervised training, RL training, and self-play data generation.

- **`pyproject.toml` / `setup.py`**: Package metadata and instructions for building the Cython `structure.pyx` module.

- **`scripts/`**: Contains wrapper scripts that provide backward compatibility for the old `.py` commands. They simply shell out to the new `alphable` CLI.

- **`data/`, `models/`, `resources/`, `visualizer/`**: Root directories that hold non-code artifacts and the web visualizer application.

## Setup & Installation

Alphable V3 must be installed as a package (preferably in editable mode) so that its internal absolute imports work correctly and its Cython modules are compiled.

1. **Activate your environment**:
   Make sure your Python virtual environment or `.devcontainer` environment is active.

2. **Install requirements**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install the `alphable` package in editable mode**:
   This step builds the Cython extensions and installs the `alphable` command into your path.
   ```bash
   pip install -e .
   ```

4. **Verify Installation**:
   Test the CLI to ensure it is installed correctly:
   ```bash
   alphable -h
   ```

## Using the Unified CLI

The new `alphable` command manages all operations through a structured set of subcommands. You can use `-h` on any subcommand to see its available options.

### 1. Data Preparation
To prepare training datasets:
```bash
alphable data prepare --help
```

### 2. Training
To train the neural networks (Supervised Learning or Reinforcement Learning):
```bash
alphable train supervised --help
alphable train rl --help
```

### 3. Self-Play
To generate data via self-play:
```bash
alphable selfplay generate --help
```

### 4. Evaluation
To run matches between models, evaluate against baselines (greedy/random), or play Transformer vs NN:
```bash
alphable eval matches --help

# Evaluate against greedy or random
alphable eval baseline --opponent greedy
alphable eval baseline --opponent random

# Evaluate SmolLM2 Candidate Ranker vs NN Alphable head-to-head
alphable eval baseline \
  --opponent nn \
  --games 5 \
  --mode transformer \
  --transformer-model models/transformer_ranker_v2 \
  --model models/alphable_v3_macondo_v2.pth
```

### 5. Online Platform Play (Woogles.io)
To play autonomous matches on Woogles with ResNet or Transformer modes:
```bash
alphable play woogles --help

# 1-ply Monte Carlo search (ResNet champion model)
alphable play woogles --bot HastyBot --mode lookahead

# SmolLM2 Candidate Ranker mode (with optional --no-delay for instant blitz play)
alphable play woogles --bot HastyBot --mode transformer --no-delay
```

### 6. SmolLM2 Transformer Ranker Training
To fine-tune an autoregressive transformer on expert Scrabble decisions:
```bash
alphable train transformer-ranker --help
```

### 7. Automated Pipeline
To run a full RL calibration cycle:
```bash
alphable pipeline calibrate --help
```

## Backward Compatibility

If you have existing automation or habits built around the old root-level scripts (e.g., `python run_calibration_cycle.py`), you can continue using them for now. They have been moved to the `scripts/` directory.

To use a backward-compatible wrapper script from the `Alphable_V3` root:
```bash
python scripts/evaluate_vs_greedy.py
```
*Note: These wrappers will print a deprecation warning and then internally execute the corresponding `alphable` command.*

## Visualizer

The visualizer tool remains at the root level and is not part of the core Python package.

To start the visualizer:
```bash
./start_visualizer.sh
```
This handles installing node modules and starting both the Flask backend and the React frontend.

---

## 🏆 Current Performance Benchmarks (V3 Generation 2)

Evaluated under identical conditions against `GreedyBot` (1-ply Monte Carlo lookahead search):
- **Win Rate:** **80.0%** (4 wins / 1 loss)
- **Average Points per Game:** **447.2 pts**
- **Net Cumulative Margin:** **+281 points** (+56.2 net point differential per game)
- **Superhuman Demonstrations:** `TRAPNEST` (89 pts), `ONIGIRIS` (78 pts), `ALNAGER` (75 pts), `HOUND` (53 pts), `QINTAR` (52 pts)

---

## 📚 Exhaustive Documentation

Comprehensive guides, architectural blueprints, and workflows are available in the [`docs/`](docs/) directory:

- [**Master Documentation Index**](docs/README.md)
- [**Quick Start Guide**](docs/QUICK_START.md)
- [**Neural Network & Tensor Architecture**](docs/architecture/ARCHITECTURE.md)
- [**Search & Minimax Move Equity**](docs/architecture/SEARCH_AND_EQUITY.md)
- [**Core Modules Reference**](docs/components/CORE_MODULES.md)
- [**Training Pipeline Reference**](docs/components/TRAINING_PIPELINE.md)
- [**Evaluation & Analytics Reference**](docs/components/EVALUATION_AND_ANALYTICS.md)
- [**End-to-End Training Lifecycle**](docs/workflows/TRAINING_WORKFLOW.md)
- [**CLI Reference Manual**](docs/workflows/CLI_REFERENCE.md)
- [**Experiment History & What We Have Tried**](docs/decisions/WHAT_WE_HAVE_TRIED.md)
- [**Technical Bug Post-Mortems**](docs/decisions/BUGS_AND_POSTMORTEMS.md)
- [**Master V3 Specification**](docs/ALPHABLE_V3_DOCUMENTATION.md)
