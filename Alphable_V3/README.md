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
To run matches between models or evaluate against a baseline (greedy/random):
```bash
alphable eval matches --help
alphable eval baseline --opponent random
alphable eval baseline --opponent greedy
```

### 5. Automated Pipeline
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
*For detailed architecture notes on how the Scrabble AI evaluates after-states and uses GADDAG, see the [ALPHABLE_V3_DOCUMENTATION.md](ALPHABLE_V3_DOCUMENTATION.md).*
