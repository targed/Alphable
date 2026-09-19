# Alphable V3: Architecture, Training, and Usage

This document explains how Alphable V3 works end-to-end, what each command does, and how to run the full pipeline from supervised learning to reinforcement learning.

---

## 1. High-Level Architecture

Alphable V3 is an after-state value system for Scrabble.

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
   - 4 open premium-square channels (DL, TL, DW, TW, cleared once occupied).
2. State vector `[36]`:
   - 26 rack counts (A-Z).
   - 1 blank count.
   - Score differential (normalized by 500.0).
   - Bag remaining (normalized by 100.0).
   - Leave rack length / 7.0.
   - Vowel count / 7.0.
   - Consonant count / 7.0.
   - Has blank flag (1.0 or 0.0).
   - Has 'S' flag (1.0 or 0.0).
   - Duplicate letter penalty / 7.0.
   - Empty leave flag (1.0 if bingo/out, else 0.0).

Network output:

- A scalar in `[-1, 1]` from `tanh`.

Interpretation by phase:

- Supervised phase output behaves like expert-preference value.
- RL phase output is trained with configurable targets:
  - outcome-only (`-1/0/1`),
  - normalized point margin,
  - or a blended outcome+margin target (recommended).

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
- CLI supports explicit dictionary/input/output paths plus fallback candidate lists.
- Safe multiprocessing is supported via `--workers` for faster processing on commodity CPUs.

Key CLI options:

- `--dict <path>`: Explicit dictionary path.
- `--dict-candidates <p1> <p2> ...`: Fallback dictionary search order.
- `--input <path>`: Explicit input JSONL path.
- `--input-candidates <p1> <p2> ...`: Fallback input search order.
- `--output <path>`: Output samples JSONL path.
- `--negatives <N>`: Hard negatives per positive sample (default: `4`).
- `--workers <N>`: Worker processes (default: `cpu_count()-1`).
- `--chunksize <N>`: Worker chunksize (default: `32`).
- `--max-games <N>`: Limit games for smoke tests.

Recommended runs:

```bash
# Full run (fast, stable default)
alphable data prepare --workers 8 --chunksize 64

# Explicit paths and dictionary
alphable data prepare \
   --dict resources/CSW24.txt \
   --input data/whoogles/training_HastyBot100k_CSW24.jsonl \
   --output data/supervised/samples.jsonl \
   --negatives 4 \
   --workers 8 --chunksize 64

# Quick smoke test
alphable data prepare --max-games 200 --workers 1 --output data/supervised/samples_smoke.jsonl
```

### 3.2 Supervised training

Script: `train_supervised.py`

What it does:

1. Loads compact dataset via `dataset.py`.
2. Expands tensors on-the-fly in dataloading.
3. Trains with weighted MSE, target smoothing, LR scheduler, and early stopping.
4. Saves best checkpoint to `models/alphable_best_val_model.pth`.

Key CLI options:

- `--data <path>`: Supervised samples JSONL path.
- `--save-model <path>`: Full checkpoint output path.
- `--save-dir <path>`: Output directory when `--save-model` is omitted.
- `--resume-model <path>`: Warm-start checkpoint.
- `--batch-size <N>`: Batch size (auto if omitted).
- `--train-split <float>`: Train split ratio (default `0.9`).
- `--epochs <N>`: Number of epochs.
- `--lr <float>` / `--weight-decay <float>`: Optimizer settings.
- `--positive-weight <float>` / `--negative-weight <float>`: Class weights.
- `--target-scale <float>`: Label smoothing scale.
- `--early-stop-patience <N>`: Early stopping patience.
- `--device auto|cpu|cuda`: Explicit device selection.

Recommended runs:

```bash
# Default training run
alphable train supervised

# Explicit data and output path
alphable train supervised \
   --data data/supervised/samples.jsonl \
   --save-model models/alphable_best_val_model.pth

# Resume training with tuned settings
alphable train supervised \
   --resume-model models/alphable_best_val_model.pth \
   --epochs 30 --batch-size 128 --lr 0.001 --early-stop-patience 6
```

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
4. Assigns terminal targets to each stored state using `--reward-mode`:
   - `outcome`: winner `1.0`, loser `-1.0`, draw `0.0`.
   - `margin`: `tanh((my_final - opp_final) / margin_scale)`.
   - `blend` (recommended):
     `target = (1 - margin_mix) * outcome + margin_mix * margin_norm`.
5. Writes RL samples to `data/rl/rl_samples.jsonl`.

Self-play quality controls:

- Temperature schedule:
  - `--temperature-start` and `--temperature-end` linearly anneal exploration through the game.
- Opponent diversity:
  - `--opponent-models` samples from a checkpoint pool for stronger and less self-referential training.

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
alphable data prepare
alphable train supervised
python search.py
```

With explicit supervised training paths:

```bash
alphable train supervised --data data/supervised/samples.jsonl --save-model models/alphable_best_val_model.pth
```

For a faster dataset build on multi-core CPU:

```bash
alphable data prepare --workers 8 --chunksize 64
```

Note: `search.py` now defaults to the RL checkpoint in lookahead mode. To explicitly inspect BC behavior:

```bash
python search.py --model models/alphable_best_val_model.pth --mode bc_0ply
```

### 6.2 RL data generation

```bash
alphable selfplay generate \
   --games 1000 \
   --output data/rl/rl_samples.jsonl \
   --top-k 5 \
   --temperature-start 0.20 \
   --temperature-end 0.10 \
   --reward-mode blend \
   --margin-scale 150 \
   --margin-mix 0.35 \
   --infer-batch-size 128
```

For faster CPU generation, run games in parallel workers:

```bash
alphable selfplay generate --games 1000 --workers 8 --chunksize 8 --device cpu
```

For faster single-GPU generation, use interleaved games (single process, larger batched inference):

```bash
alphable selfplay generate --games 1000 --device cuda --workers 1 --concurrent-games 16 --infer-batch-size 256
```

Notes:

- On CUDA, self-play now forces `--workers 1` to avoid GPU contention/OOM from multiple model processes.
- Use `--device auto` (default), `--device cpu`, or `--device cuda`.
- `--concurrent-games > 1` enables interleaved single-process play, which is usually the fastest single-GPU mode.
- Tune `--concurrent-games` and `--infer-batch-size` together to maximize throughput without OOM.
- `--flush-every-games N` forces periodic output flushes so long runs visibly write progress to disk.

Optional opponent-pool self-play:

```bash
alphable selfplay generate \
   --games 1000 \
   --opponent-models models/alphable_best_val_model.pth models/alphable_rl_best_val_model.pth \
   --reward-mode blend --margin-scale 150 --margin-mix 0.35
```

Greedy-curriculum self-play (P1 forced greedy, keep only Alphable/P0 samples):

```bash
alphable selfplay generate \
   --games 2000 \
   --output data/rl/rl_vs_greedy.jsonl \
   --model models/alphable_best_val_model.pth \
   --vs-greedy --keep-p0-only \
   --top-k-vs-greedy 20 \
   --temperature-start-vs-greedy 0.50 \
   --temperature-end-vs-greedy 0.10 \
   --reward-mode blend --margin-scale 150 --margin-mix 0.35 \
   --device cuda --workers 1 --concurrent-games 16 --infer-batch-size 128
```

Notes for greedy curriculum:

- `--vs-greedy` makes player 1 a deterministic greedy bot.
- `--keep-p0-only` avoids training on greedy-player states.
- `--top-k-vs-greedy` and `--temperature-*-vs-greedy` widen exploration only for this mode.

Synthetic Data Generation (Greedy vs Greedy):
To generate strong bootstrap/synthetic data where both sides play high-scoring baseline moves, use `--greedy-vs-greedy`:

```bash
alphable selfplay generate \
   --games 2000 \
   --output data/rl/rl_greedy_vs_greedy.jsonl \
   --model models/alphable_best_val_model.pth \
   --greedy-vs-greedy \
   --reward-mode blend --margin-scale 150 --margin-mix 0.35 \
   --device cuda --workers 1 --concurrent-games 16 --infer-batch-size 128
```

_(This is purely synthetic simulation, making it a fast way to gather very high-scoring play trajectories.)_

If you hit GPU memory limits on positions with many legal moves:

```bash
alphable selfplay generate --games 1000 --output data/rl/rl_samples.jsonl --top-k 5 --temperature-start 0.20 --temperature-end 0.10 --reward-mode blend --margin-scale 150 --margin-mix 0.35 --infer-batch-size 128
```

Useful options:

```bash
alphable selfplay generate --games 200 --append
alphable selfplay generate --games 100 --max-turns 250 --seed 123
alphable selfplay generate --games 300 --reward-mode outcome
alphable selfplay generate --games 300 --reward-mode margin --margin-scale 150
alphable selfplay generate --games 500 --workers 8 --chunksize 8 --device cpu
alphable selfplay generate --games 1000 --device cuda --workers 1 --concurrent-games 16 --infer-batch-size 256
```

Quick throughput tuning recipe (single GPU):

1. Start with `--concurrent-games 8 --infer-batch-size 128`.
2. Increase to `--concurrent-games 16` and then `24` while keeping `--workers 1`.
3. If stable, raise `--infer-batch-size` to `256`.
4. If you hit OOM, lower `--infer-batch-size` first, then lower `--concurrent-games`.

Recommended mixed-curriculum data blend (to avoid overfitting to one opponent style):

```bash
# 40% mirror/pool self-play
alphable selfplay generate --games 1000 --output data/rl/rl_mix_selfplay.jsonl --opponent-models models/alphable_best_val_model.pth models/alphable_rl_best_val_model.pth --reward-mode blend --margin-scale 150 --margin-mix 0.35 --device cuda --workers 1 --concurrent-games 16 --infer-batch-size 128

# 40% vs greedy curriculum
alphable selfplay generate --games 1000 --output data/rl/rl_mix_vs_greedy.jsonl --model models/alphable_best_val_model.pth --vs-greedy --keep-p0-only --top-k-vs-greedy 20 --temperature-start-vs-greedy 0.50 --temperature-end-vs-greedy 0.10 --reward-mode blend --margin-scale 150 --margin-mix 0.35 --device cuda --workers 1 --concurrent-games 16 --infer-batch-size 128

# 20% stronger checkpoint pool
alphable selfplay generate --games 500 --output data/rl/rl_mix_strong_pool.jsonl --opponent-models models/alphable_rl_best_val_model.pth models/alphable_rl_best_val_model_HastyBot_CSW100K.pth --reward-mode blend --margin-scale 150 --margin-mix 0.35 --device cuda --workers 1 --concurrent-games 16 --infer-batch-size 128
```

### 6.3 RL training

```bash
alphable train rl --data data/rl/rl_samples.jsonl --init-model models/alphable_rl_best_val_model.pth --save-model models/alphable_rl_best_val_model.pth
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
alphable eval matches --model-a models/alphable_best_val_model.pth --model-b models/alphable_rl_best_val_model.pth --games 50
```

For lower-memory evaluation:

```bash
alphable eval matches --model-a models/alphable_best_val_model.pth --model-b models/alphable_rl_best_val_model.pth --games 50 --infer-batch-size 128
```

### 6.5 Calibration iteration (recommended)

Run one full RL calibration cycle:

```bash
alphable selfplay generate --games 1000 --append --output data/rl/rl_samples.jsonl --top-k 5 --temperature-start 0.20 --temperature-end 0.10 --reward-mode blend --margin-scale 150 --margin-mix 0.35 --infer-batch-size 128
alphable train rl --data data/rl/rl_samples.jsonl --init-model models/alphable_rl_best_val_model.pth --save-model models/alphable_rl_best_val_model.pth
alphable eval matches --model-a models/alphable_best_val_model.pth --model-b models/alphable_rl_best_val_model.pth --games 200 --infer-batch-size 128
```

### 6.6 One-command calibration cycle with logs

Use the orchestrator script to run self-play, RL training, and match evaluation in one command with live output and saved log files.

```bash
alphable pipeline calibrate
```

What it writes:

- `logs/calibration_runs/<timestamp>/self_play.log`
- `logs/calibration_runs/<timestamp>/train_rl.log`
- `logs/calibration_runs/<timestamp>/evaluate.log`
- `logs/calibration_runs/<timestamp>/summary.json`

Example custom run:

```bash
alphable pipeline calibrate --games 500 --eval-games 100 --infer-batch-size 128
```

Fast smoke run (new dataset file, 1 epoch, tiny eval):

```bash
alphable pipeline calibrate --games 1 --overwrite --rl-data data/rl/rl_cycle_smoke.jsonl --epochs 1 --batch-size 16 --eval-games 2
```

If a step fails, the script stops and records the exit code in `summary.json`.

### 6.7 Behavior auditing with replay logs (Phase 1 + 2)

Generate V2-native replay logs against random and greedy baselines:

```bash
alphable eval baseline --opponent random --games 10 --model models/alphable_rl_best_val_model.pth --mode lookahead --infer-batch-size 128
alphable eval baseline --opponent greedy --games 10 --model models/alphable_rl_best_val_model.pth --mode lookahead --infer-batch-size 128
```

Outputs are written to:

- `data/vs_random/*.json` and `data/vs_random/*.txt`
- `data/vs_greedy/*.json` and `data/vs_greedy/*.txt`
- `data/vs_random/summaries/*.json` and `data/vs_greedy/summaries/*.json`

Replay JSON is visualizer-compatible and includes:

- per-turn `rack_before`, `rack_after`, `board_state`, and score delta
- action metadata (`PLAY`/`PASS`, word/position/direction)
- Alphable diagnostics (`alphable_value`, `top_candidates`)

Summary JSON files include:

- per-game summary: winner, margin, bingos, average score/move, replay paths
- per-run summary: wins/losses/ties, win rate, average margin, all game summary file paths

Launch the visualizer backend and inspect games:

```bash
cd visualizer/backend
python app.py
```

Then open `http://localhost:5000` and load games from `vs_random` / `vs_greedy`.

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
- `game_logger.py`: V2 replay logger (visualizer-compatible JSON schema).
- `evaluate_vs_baseline.py`: Shared V2 evaluator for random/greedy baselines.
- `evaluate_vs_random.py`: Wrapper for V2 random-baseline evaluation.
- `evaluate_vs_greedy.py`: Wrapper for V2 greedy-baseline evaluation.
