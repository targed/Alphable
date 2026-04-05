# Alphable V2: Architecture, Training, and Usage

This document explains how Alphable V2 works end-to-end, what each script does, and how to run the full pipeline from supervised learning to reinforcement learning.

---

## 1. High-Level Architecture

Alphable V2 is an after-state value system for Scrabble.

1. Generate legal moves with GADDAG.
2. Simulate each move into an after-state board.
3. Encode board + scalar state into tensors.
4. Score after-states with a neural value network.
5. Select moves based on the current operating mode:
   - Behavior Cloning mode: 0-ply argmax.
   - RL value mode: optional 1-ply lookahead.

Core modules:

- `structure.py` and `structure.pyx`: GADDAG dictionary and legal move generation.
- `simulator.py`: Move application and primary scoring.
- `inference.py`: Tensorization and model inference.
- `alphable_net.py`: Residual CNN + dense state head architecture.

---

## 2. Model Inputs and Outputs

Input tensors:

1. Board tensor `[31, 15, 15]`:
   - 26 letter channels A-Z.
   - 1 blank channel.
   - 4 premium-square channels (DL, TL, DW, TW).
2. State vector `[29]`:
   - 26 rack counts.
   - 1 blank count.
   - Score differential.
   - Bag remaining.

Network output:

- A scalar in `[-1, 1]` from `tanh`.

Interpretation by phase:

- Supervised phase output behaves like expert-preference value.
- RL phase output is trained toward game outcome value.

---

## 3. Phase 2: Supervised Behavior Cloning

### 3.1 Dataset generation

Script: `prepare_dataset.py`

What it does:

1. Reads human games from Woogles-derived input.
2. Builds one positive sample per move (`target=1.0`).
3. Builds hard negatives per move (`target=-1.0`) from top scoring alternatives.
4. Writes compact samples to `data/supervised/samples.jsonl`.

Current design notes:

- Hard negatives are top-4 per positive in the current tuning setup.
- Dictionary parsing supports NWL line format (`WORD definition...`).

### 3.2 Supervised training

Script: `train_supervised.py`

What it does:

1. Loads compact dataset via `dataset.py`.
2. Expands tensors on-the-fly in dataloading.
3. Trains with weighted MSE, target smoothing, LR scheduler, and early stopping.
4. Saves best checkpoint to `models/alphable_best_val_model.pth`.

Current training features:

- Positive/negative weighting for class imbalance.
- Smoothed targets to reduce output saturation.
- Early stopping based on validation loss.

### 3.3 Search in BC mode

Script: `search.py`

Current default mode is `bc_0ply`.

- It ranks immediate after-state values and chooses argmax.
- It does not use opponent-reply negation in this default BC mode.

---

## 4. Phase 3: RL Data and Training

### 4.1 Self-play data generation

Script: `self_play.py`

What it does:

1. Loads the current checkpoint.
2. Plays model-vs-model games with top-k temperature sampling.
3. Saves every turn state.
4. Assigns terminal outcome target to each stored state:
   - Winner states `target=1.0`.
   - Loser states `target=-1.0`.
   - Draw states `target=0.0`.
5. Writes RL samples to `data/rl/rl_samples.jsonl`.

### 4.2 RL fine-tuning

Script: `train_rl.py`

What it does:

1. Loads RL samples from self-play.
2. Warm-starts from `models/alphable_best_val_model.pth` by default.
3. Trains with standard MSE for outcome regression.
4. Saves best checkpoint to `models/alphable_rl_best_val_model.pth`.

---

## 5. Match Evaluation

Script: `evaluate_matches.py`

What it does:

1. Loads two checkpoints.
2. Plays head-to-head matches with alternating first player.
3. Reports wins/losses/draws and average score differential.

Use this to compare:

- Supervised checkpoint vs RL checkpoint.
- New architecture tweaks vs baseline.

---

## 6. Commands: End-to-End Workflow

### 6.1 Supervised pipeline

```bash
python prepare_dataset.py
python train_supervised.py
python search.py
```

Note: `search.py` now defaults to the RL checkpoint in lookahead mode. To explicitly inspect BC behavior:

```bash
python search.py --model models/alphable_best_val_model.pth --mode bc_0ply
```

### 6.2 RL data generation

```bash
python self_play.py --games 1000 --output data/rl/rl_samples.jsonl --top-k 5 --temperature 0.20 --infer-batch-size 128
```

If you hit GPU memory limits on positions with many legal moves:

```bash
python self_play.py --games 1000 --output data/rl/rl_samples.jsonl --top-k 5 --temperature 0.20 --infer-batch-size 128
```

Useful options:

```bash
python self_play.py --games 200 --append
python self_play.py --games 100 --max-turns 250 --seed 123
```

### 6.3 RL training

```bash
python train_rl.py --data data/rl/rl_samples.jsonl --init-model models/alphable_rl_best_val_model.pth --save-model models/alphable_rl_best_val_model.pth
```

If the RL checkpoint does not exist yet, `train_rl.py` automatically falls back to `models/alphable_best_val_model.pth`.

### 6.3.1 RL search defaults (stability tuned)

Default `search.py` behavior is now:

- checkpoint: `models/alphable_rl_best_val_model.pth`
- mode: `lookahead`
- eval simulations: `32`
- opponent reply aggregation: top `5`
- inference batch size: `128`

Example explicit run:

```bash
python search.py --model models/alphable_rl_best_val_model.pth --mode lookahead --eval-sims 32 --opp-reply-top-k 5 --infer-batch-size 128
```

### 6.4 Compare checkpoints

```bash
python evaluate_matches.py --model-a models/alphable_best_val_model.pth --model-b models/alphable_rl_best_val_model.pth --games 50
```

For lower-memory evaluation:

```bash
python evaluate_matches.py --model-a models/alphable_best_val_model.pth --model-b models/alphable_rl_best_val_model.pth --games 50 --infer-batch-size 128
```

### 6.5 Calibration iteration (recommended)

Run one full RL calibration cycle:

```bash
python self_play.py --games 1000 --append --output data/rl/rl_samples.jsonl --top-k 5 --temperature 0.20 --infer-batch-size 128
python train_rl.py --data data/rl/rl_samples.jsonl --init-model models/alphable_rl_best_val_model.pth --save-model models/alphable_rl_best_val_model.pth
python evaluate_matches.py --model-a models/alphable_best_val_model.pth --model-b models/alphable_rl_best_val_model.pth --games 200 --infer-batch-size 128
```

### 6.6 One-command calibration cycle with logs

Use the orchestrator script to run self-play, RL training, and match evaluation in one command with live output and saved log files.

```bash
python run_calibration_cycle.py
```

What it writes:

- `logs/calibration_runs/<timestamp>/self_play.log`
- `logs/calibration_runs/<timestamp>/train_rl.log`
- `logs/calibration_runs/<timestamp>/evaluate.log`
- `logs/calibration_runs/<timestamp>/summary.json`

Example custom run:

```bash
python run_calibration_cycle.py --games 500 --eval-games 100 --infer-batch-size 128
```

Fast smoke run (new dataset file, 1 epoch, tiny eval):

```bash
python run_calibration_cycle.py --games 1 --overwrite --rl-data data/rl/rl_cycle_smoke.jsonl --epochs 1 --batch-size 16 --eval-games 2
```

If a step fails, the script stops and records the exit code in `summary.json`.

---

## 7. Operational Guidance

Recommended progression:

1. Stabilize supervised model quality first.
2. Generate RL data in batches.
3. RL fine-tune from best supervised checkpoint.
4. Compare checkpoints with head-to-head matches.
5. Switch search mode to lookahead for RL checkpoints only after outcome-value behavior is validated.

Practical stopping condition for a phase:

1. Validation improvements flatten over repeated runs.
2. Match win-rate improvements flatten over repeated runs.
3. Chosen move quality appears stable on held-out real board states.

---

## 8. File Map

- `alphable_net.py`: Neural architecture.
- `dataset.py`: Compact JSONL to tensor dataset adapter.
- `prepare_dataset.py`: Human-game supervised data generation.
- `train_supervised.py`: Supervised BC training.
- `search.py`: BC 0-ply and lookahead search logic.
- `self_play.py`: Self-play RL sample generation.
- `train_rl.py`: Outcome-based RL fine-tuning.
- `evaluate_matches.py`: Checkpoint-vs-checkpoint match evaluator.
