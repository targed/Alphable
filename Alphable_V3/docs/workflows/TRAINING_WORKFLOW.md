# Alphable V3: End-to-End Training Lifecycle

This workflow guide provides step-by-step instructions for executing the complete model training, fine-tuning, and evaluation lifecycle.

---

## The 5-Stage Lifecycle Overview

```
+---------------------------------------------------------------------------------+
|                                Training Lifecycle                               |
+---------------------------------------------------------------------------------+
|                                                                                 |
|  Stage 1: Replay Data Ingestion                                                 |
|    - Download expert games (2000+ Elo / BestBot) from Woogles.io.               |
|    - Parse into compact game replays (`data/woogles/data/training_dataset.jsonl`).|
|                                                                                 |
|  Stage 2: Supervised Dataset Preparation                                        |
|    - Run `prepare_dataset.py` with multiprocessing.                             |
|    - Extract positive expert plays & continuous deficit-scaled hard negatives.  |
|    - Emits: `data/supervised/samples_woogles_clean.jsonl`.                      |
|                                                                                 |
|  Stage 3: Supervised Foundation Pretraining                                     |
|    - Train `AlphableValueNet` on the clean supervised dataset on CUDA.          |
|    - Validation loss converges to ~0.029.                                       |
|    - Saves: `models/alphable_v3_supervised_clean.pth`.                          |
|                                                                                 |
|  Stage 4: Curriculum Self-Play Generation                                       |
|    - Generate 100 mirror self-play games (temperature 0.20 -> 0.10).            |
|    - Generate 50 anti-greedy curriculum games (`--vs-greedy --keep-p0-only`).   |
|    - Emits: `data/rl/curriculum_gen2.jsonl` (~3,150 samples).                   |
|                                                                                 |
|  Stage 5: Reinforcement Learning & Gatekeeper Evaluation                        |
|    - Train RL model warm-started from previous generation checkpoint.           |
|    - Saves: `models/alphable_v3_rl_gen2.pth`.                                   |
|    - Gatekeeper Benchmarks:                                                     |
|      * Direct matches vs previous model (`eval matches`).                       |
|      * 5-game test vs `GreedyBot` (`eval baseline --opponent greedy`).          |
|      * Verify win rate >= 70% and positive net score margin before promotion.   |
|                                                                                 |
+---------------------------------------------------------------------------------+
```

---

## Detailed Step-by-Step Instructions

### Step 1: Prepare Supervised Data
Using `src/alphable/training/prepare_dataset.py`, process game replays into clean after-state samples:

```bash
python -m alphable.cli.main data prepare \
  --input data/woogles/data/training_dataset.jsonl \
  --output data/supervised/samples_woogles_clean.jsonl \
  --dict resources/CSW24.txt \
  --negatives 4 \
  --workers 16
```
- **Expected Duration:** ~1–2 minutes across 16 CPU cores for 580 games.
- **Output Artifact:** `data/supervised/samples_woogles_clean.jsonl` (~9,600 samples).

### Step 2: Train Supervised Foundation Model
Train the neural network using `src/alphable/training/train_supervised.py`:

```bash
python -m alphable.cli.main train supervised \
  --data data/supervised/samples_woogles_clean.jsonl \
  --resume-model models/alphable_rl_best_val_model.pth \
  --epochs 10 \
  --batch-size 128 \
  --lr 3e-4 \
  --save-model models/alphable_v3_supervised_clean.pth
```
- **Hardware:** Runs on CUDA with Blackwell workarounds automatically engaged.
- **Convergence Target:** Validation loss $\le 0.035$.

### Step 3: Generate Curriculum Self-Play Trajectories
Generate mirror games and anti-greedy games in two quick passes:

```bash
# Part A: 100 Mirror Self-Play Games
python -m alphable.cli.main selfplay generate \
  --model models/alphable_v3_supervised_clean.pth \
  --games 100 \
  --output data/rl/curriculum_gen2.jsonl \
  --device cuda

# Part B: 50 Anti-Greedy Games (with keep-p0-only protection)
python -m alphable.cli.main selfplay generate \
  --model models/alphable_v3_supervised_clean.pth \
  --games 50 \
  --output data/rl/curriculum_gen2.jsonl \
  --device cuda \
  --vs-greedy \
  --keep-p0-only \
  --append
```
- **Crucial Flag:** `--keep-p0-only` ensures only Alphable's turns are logged, preventing GreedyBot's point-chasing plays from contaminating the RL dataset.

### Step 4: Train Reinforcement Learning Model
Train the new RL generation checkpoint using `src/alphable/training/train_rl.py`:

```bash
python -m alphable.cli.main train rl \
  --data data/rl/curriculum_gen2.jsonl \
  --init-model models/alphable_v3_supervised_clean.pth \
  --save-model models/alphable_v3_rl_gen2.pth \
  --epochs 15 \
  --lr 3e-4 \
  --batch-size 128
```

### Step 5: Gatekeeper Validation
Run the standardized evaluation suite to prove measurable progress before promoting the checkpoint:

```bash
# 1. Head-to-Head vs Previous Model (10 games)
python -m alphable.cli.main eval matches \
  --model-a models/alphable_v3_rl_gen2.pth \
  --model-b models/alphable_v3_supervised_clean.pth \
  --games 10

# 2. Automated Baseline vs GreedyBot (5 games with lookahead)
python -m alphable.cli.main eval baseline \
  --model models/alphable_v3_rl_gen2.pth \
  --opponent greedy \
  --games 5

# 3. Plot Training Loss Curves
python -m alphable.cli.main eval plot \
  --history models/alphable_v3_rl_gen2_history.json \
  --output reports/rl_gen2_progress.png
```

### Gatekeeping Acceptance Criteria:
1. **Win Rate vs GreedyBot:** Must achieve $\ge 60\%$ (RL Gen2 achieved **80%**).
2. **Average Score:** Must exceed 400 points per game (RL Gen2 achieved **447.2 pts**).
3. **Score Margin:** Cumulative point margin against GreedyBot must be positive (RL Gen2 achieved **+281 net margin**).
