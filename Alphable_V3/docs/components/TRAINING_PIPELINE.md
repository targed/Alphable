# Alphable V3: Training Pipeline Reference

This document covers all data preparation, supervised foundation training, grandmaster knowledge distillation, self-play generation, and reinforcement learning modules located in [`src/alphable/training/`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/training).

---

## Pipeline Overview

```
             ┌────────────────────────────────────────────────────────┐
             │                  Raw Match History                     │
             │   (Woogles GCG Games + Macondo Analysis JSON Logs)     │
             └──────────────────────────┬─────────────────────────────┘
                                        │
             ┌──────────────────────────┴─────────────────────────────┐
             │                                                        │
             ▼                                                        ▼
┌─────────────────────────┐                              ┌─────────────────────────┐
│   prepare_dataset.py    │                              │   distill_macondo.py    │
│  Supervised Negative    │                              │  Grandmaster Knowledge  │
│  Mining & Deficits      │                              │  Distillation (Anchor)  │
└────────────┬────────────┘                              └────────────┬────────────┘
             │                                                        │
             ▼                                                        ▼
┌─────────────────────────┐                              ┌─────────────────────────┐
│   train_supervised.py   │                              │ alphable_v3_macondo.pth │
│ Base Value Network Net  │                              │ (State-of-the-Art Net)  │
└────────────┬────────────┘                              └────────────┬────────────┘
             │                                                        │
             └──────────────────────────┬─────────────────────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │      self_play_rl.py        │
                         │ Pure Outcome Self-Play RL   │
                         │ (Anchored vs Expert Target) │
                         └─────────────────────────────┘
```

---

## 1. `distill_macondo.py` ([`src/alphable/training/distill_macondo.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/training/distill_macondo.py))

Offline Knowledge Distillation from Macondo Grandmaster Analyzer data. This module is the **primary training breakthrough** that broke the self-play cowardice trap by anchoring Alphable to superhuman Scrabble positional evaluations.

### The Problem It Solved
In pure outcome self-play RL, symmetric agents collapsed into a mutual local Nash equilibrium of timid, low-scoring defensive plays (averaging 250 points per game). Without an objective positional equity anchor, the network could not discover that opening bingo lanes with high-synergy leaves is strategically superior.

### Data Ingestion & Extraction
- Scans match directories in `data/woogles/matches/*/` containing paired `game.gcg` and `analysis.json` files.
- Replays every move of the game sequentially on a $15 \times 15$ board.
- Tracks player scores, exact bag remaining, and current player rack.
- Extracts Macondo's grandmaster equity evaluation for the position from the suggestion list.

### Mathematical Target Formulation
Macondo evaluates candidate moves in expected point equity (typical tournament range $[-60.0, +60.0]$ points). The training target combines normalized Macondo equity with the true terminal match outcome:

$$\begin{aligned}
v_{\text{macondo}} &= \tanh\left(\frac{\text{Equity}_{\text{Macondo}}}{50.0}\right) \in [-1.0, +1.0] \\
v_{\text{outcome}} &= \tanh\left(\frac{\Delta \text{Final Score}}{100.0}\right) \in [-1.0, +1.0] \\
v_{\text{target}} &= 0.75 \times v_{\text{macondo}} + 0.25 \times v_{\text{outcome}}
\end{aligned}$$

- **75% Weight on Macondo Equity:** Directly anchors the network to championship evaluation of board openness, rack leaves, and hot-spot positioning.
- **25% Weight on Match Outcome:** Preserves awareness of overall game victory and point margins.

### Feature Representation
For each position, generates:
- **Board Tensor:** $31 \times 15 \times 15$ (`inference.board_to_tensor(board)`).
- **State Vector:** 63-dimensional scalar vector (`inference.state_to_tensor(rack, score_diff, bag, unseen_dist)`).

### Training Setup & Optimization
- **Dataset Class:** `MacondoDistillationDataset` with PyTorch `DataLoader` (shuffled, batch size 64 or 128).
- **Optimizer:** `torch.optim.AdamW(lr=2e-4, weight_decay=1e-4)`.
- **Loss Function:** Mean Squared Error (`nn.MSELoss()`).
- **Learning Rate Scheduler:** `CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)`.
- **Checkpointing:** Validates on a held-out split and saves the best model checkpoint to `models/alphable_v3_macondo_v2.pth`.

### Execution
```bash
python -m alphable.training.distill_macondo \
  --matches-dir data/woogles/matches \
  --base-model models/alphable_v3_supervised_clean.pth \
  --save-model models/alphable_v3_macondo_v2.pth \
  --epochs 12 \
  --batch-size 64 \
  --lr 2e-4
```

---

## 2. `prepare_dataset.py` ([`src/alphable/training/prepare_dataset.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/training/prepare_dataset.py))

Generates compact, supervised training samples from tournament and bot Scrabble game replay logs (`.jsonl` or `.gcg`).

### Ingestion & Processing Workflow
1. **Player Identification & Mapping:** Resolves arbitrary usernames (e.g. `'BestBot'`, `'CarlSagan121520'`) and aliases to canonical player indices `0` and `1`.
2. **Exact Tile Accounting:**
   - Starts with a standard bag of 86 tiles ($100 - 14$ starting rack tiles).
   - On each play, computes exact tiles placed: $\text{tiles\_used} = \text{len}(\text{rack}) - \text{len}(\text{leave\_rack})$.
   - Accurately decrements bag size: $\text{bag} = \max(0, \text{bag} - \text{tiles\_used})$.
3. **Positive Sample Creation:**
   - Evaluates the played expert move via GADDAG and simulator.
   - Saves positive after-state with target label $+1.0$.
4. **Hard-Negative Pruning & Continuous Deficit Scaling:**
   - Simulates legal alternative plays generated by GADDAG.
   - Maintains a min-heap to keep only the top-$K$ scoring alternative moves (default $K=4$).
   - For alternative moves scoring less than the played move, assigns a continuous target scaled by point deficit:
     $$\text{deficit\_ratio} = \min\left(1.0, \frac{\text{pos\_score} - \text{neg\_score}}{\max(10, \text{pos\_score})}\right)$$
     $$\text{target}_{\text{neg}} = \max(-1.0, 1.0 - 2.0 \times \text{deficit\_ratio})$$
   - Prevents competitive high-scoring alternative plays from being falsely labeled as $-1.0$.

### Multi-Processing Support
- Uses Python `multiprocessing.Pool` with per-worker GADDAG initialization (`init_worker`).
- Processes hundreds of full games in parallel across CPU cores.

### Execution
```bash
python -m alphable.cli.main data prepare \
  --input data/woogles/data/training_dataset.jsonl \
  --output data/supervised/samples.jsonl \
  --dict resources/CSW24.txt \
  --negatives 4 \
  --workers 8
```

---

## 3. `train_supervised.py` ([`src/alphable/training/train_supervised.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/training/train_supervised.py))

Trains `AlphableValueNet` on the supervised dataset of expert after-states to build the base foundation model.

### Key Features
- **Data Loading:** PyTorch `DataLoader` with 90/10 train/validation split.
- **Optimization:**
  - Optimizer: `optim.AdamW(lr=3e-4, weight_decay=1e-4)`.
  - Loss Function: `nn.MSELoss()`.
  - Scheduler: `ReduceLROnPlateau(factor=0.5, patience=2)`.
- **Early Stopping:** Tracks best validation loss and triggers early stopping after $N$ non-improving epochs (default 4).
- **History Tracking:** Automatically exports epoch metrics (train loss, val loss, time, learning rate) to `<save_path>_history.json`.

### Execution
```bash
python -m alphable.cli.main train supervised \
  --data data/supervised/samples.jsonl \
  --save-model models/alphable_v3_supervised_clean.pth \
  --epochs 10 \
  --batch-size 128 \
  --lr 3e-4
```

---

## 4. `self_play_rl.py` ([`src/alphable/training/self_play_rl.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/training/self_play_rl.py))

Pure outcome reinforcement learning self-play trainer.

### Architecture
- **In-Memory Trajectory Buffer:** Simulates complete Scrabble matches using CUDA-accelerated batch inference.
- **State Vector Compatibility:** Configurable `--state-size 63` to utilize unseen tile bag tracking features.
- **Target Computation:**
  - Win/Loss/Spread target:
    $$z = \tanh\left(\frac{\text{Score}_{\text{player}} - \text{Score}_{\text{opponent}}}{100.0}\right)$$
- **Training Epochs:** Trains for $N$ epochs on freshly generated self-play games, updating weights with AdamW.

### Execution
```bash
python -m alphable.cli.main train rl-selfplay \
  --model models/alphable_v3_macondo_v2.pth \
  --save-model models/alphable_v3_rl_gen5.pth \
  --dict resources/CSW24.txt \
  --games 1000 \
  --state-size 63 \
  --batch-size 128 \
  --lr 1e-4 \
  --epochs 3
```

---

## 5. `self_play.py` ([`src/alphable/training/self_play.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/training/self_play.py))

Generates self-play datasets with curriculum and anti-greedy options.

### Capabilities & Modes
1. **Mirror Self-Play:**
   - Both players use the champion model with temperature annealing ($\tau=0.20$ early game $\to \tau=0.10$ late game).
2. **Anti-Greedy Curriculum (`--vs-greedy`):**
   - Player 0 uses the neural network; Player 1 plays as `GreedyBot` (highest immediate points).
   - **Contamination Shield (`--keep-p0-only`):** Crucial flag that drops Player 1's moves from the training log, preventing the network from learning greedy point-chasing habits when GreedyBot wins.
3. **Reward Blend Formulation (`compute_player_target`):**
   $$\text{Target} = (1 - \alpha) \times \text{Outcome} + \alpha \times \tanh\left(\frac{\Delta \text{Score}}{150.0}\right)$$
   With $\alpha = 0.35$.

### Execution
```bash
python -m alphable.cli.main selfplay generate \
  --model models/alphable_v3_macondo_v2.pth \
  --games 200 \
  --output data/rl/selfplay_samples.jsonl \
  --vs-greedy \
  --keep-p0-only \
  --device cuda
```

---

## 6. `train_rl.py` ([`src/alphable/training/train_rl.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/training/train_rl.py))

Trains the value network on offline self-play trajectory JSONL files produced by `self_play.py`.
- Warm-starts from previous checkpoint.
- Uses AdamW, Plateau learning rate scheduling, and early stopping.
- Saves best validation checkpoint and exports JSON history curves.

### Execution
```bash
python -m alphable.cli.main train rl \
  --data data/rl/selfplay_samples.jsonl \
  --resume-model models/alphable_v3_macondo_v2.pth \
  --save-model models/alphable_v3_rl_gen3.pth \
  --epochs 8 \
  --batch-size 128 \
  --lr 1e-4
```
