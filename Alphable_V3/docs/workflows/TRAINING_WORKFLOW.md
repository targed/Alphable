# Alphable V3: End-to-End Training Lifecycle

This workflow guide provides step-by-step instructions for executing the complete model training, fine-tuning, knowledge distillation, and evaluation lifecycle.

---

## The 6-Stage Lifecycle Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                Training Lifecycle                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Stage 1: Replay Data Ingestion                                                 │
│    - Download expert games (2000+ Elo / BestBot) from Woogles.io.               │
│    - Parse into compact game replays (`data/woogles/data/training_dataset.jsonl`).│
│                                                                                 │
│  Stage 2: Supervised Dataset Preparation                                        │
│    - Run `prepare_dataset.py` with multiprocessing.                             │
│    - Extract positive expert plays & continuous deficit-scaled hard negatives.  │
│    - Emits: `data/supervised/samples_woogles_clean.jsonl`.                      │
│                                                                                 │
│  Stage 3: Supervised Foundation Pretraining                                     │
│    - Train `AlphableValueNet` on the clean supervised dataset on CUDA.          │
│    - Validation loss converges to ~0.029.                                       │
│    - Saves: `models/alphable_v3_supervised_clean.pth`.                          │
│                                                                                 │
│  Stage 4: Curriculum Self-Play Generation                                       │
│    - Generate 100 mirror self-play games (temperature 0.20 -> 0.10).            │
│    - Generate 50 anti-greedy curriculum games (`--vs-greedy --keep-p0-only`).   │
│    - Emits: `data/rl/curriculum_gen2.jsonl`.                                    │
│                                                                                 │
│  Stage 5: Reinforcement Learning & Gatekeeper Evaluation                        │
│    - Train RL model warm-started from previous generation checkpoint.           │
│    - Gatekeeper: Verify win rate >= 70% vs GreedyBot.                           │
│                                                                                 │
│  Stage 6: Grandmaster Macondo Knowledge Distillation (Anchor Breakthrough)      │
│    - Harvest `game.gcg` + `analysis.json` from Woogles matches.                 │
│    - Fine-tune with `distill_macondo.py` to prevent self-play policy collapse.  │
│    - Saves: `models/alphable_v3_macondo_v2.pth`.                                │
│    - Ultimate Gatekeeper: Parity / victory vs HastyBot on Woogles.              │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
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
- **Output Artifact:** `data/supervised/samples_woogles_clean.jsonl` (~9,600 samples).

### Step 2: Train Supervised Foundation Model
Train the neural network using `src/alphable/training/train_supervised.py`:

```bash
python -m alphable.cli.main train supervised \
  --data data/supervised/samples_woogles_clean.jsonl \
  --save-model models/alphable_v3_supervised_clean.pth \
  --epochs 10 \
  --batch-size 128 \
  --lr 3e-4
```
- **Hardware:** Runs on CUDA with Blackwell RTX 50-series support automatically configured.
- **Convergence Target:** Validation loss $\le 0.035$.

### Step 3: Generate Curriculum Self-Play Trajectories
Generate mirror games and anti-greedy games:

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
Train the RL model using `src/alphable/training/train_rl.py`:

```bash
python -m alphable.cli.main train rl \
  --data data/rl/curriculum_gen2.jsonl \
  --resume-model models/alphable_v3_supervised_clean.pth \
  --save-model models/alphable_v3_rl_gen2.pth \
  --epochs 15 \
  --lr 3e-4 \
  --batch-size 128
```

### Step 5: Gatekeeper Validation vs GreedyBot
Run the standardized evaluation suite to prove measurable progress before online deployment:

```bash
# 1. Automated Baseline vs GreedyBot (10 games with lookahead)
python -m alphable.cli.main eval baseline \
  --model models/alphable_v3_rl_gen2.pth \
  --opponent greedy \
  --games 10

# 2. Plot Training Loss Curves
python -m alphable.cli.main eval plot \
  --history models/alphable_v3_rl_gen2_history.json \
  --output reports/rl_gen2_progress.png
```
- **Gatekeeping Acceptance:** Win rate $\ge 70\%$ against GreedyBot with positive cumulative score differential.

---

### Step 6: Grandmaster Macondo Distillation (Production Deployment)
When moving from local bot play to championship online tournament bots (e.g. `HastyBot`), pure self-play tends to converge into a timid local Nash equilibrium. To break free and anchor the network to grandmaster evaluations:

```bash
python -m alphable.cli.main train distill-macondo \
  --matches-dir data/woogles/matches \
  --base-model models/alphable_v3_supervised_clean.pth \
  --output-model models/alphable_v3_macondo_v2.pth \
  --epochs 12 \
  --batch-size 64 \
  --lr 2e-4
```

### Final Acceptance Criteria on Woogles:
1. **Live Series vs HastyBot (15 games):**
   ```bash
   python -m alphable.cli.main play woogles \
     --bot HastyBot \
     --games 15 \
     --model models/alphable_v3_macondo_v2.pth \
     --dict resources/CSW24.txt \
     --mode lookahead \
     --top-k 5 --simulations 10
   ```
2. **Win Rate:** Must achieve $\ge 50\%$ against HastyBot.
3. **Average Score:** Must average $>440$ points per game.
4. **Macondo Equity Loss:** Average turn loss must be $\le 1.0$ point per turn.
