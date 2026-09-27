# Alphable V3: Quick Start Guide

This guide gets you up and running with **Alphable V3** in 2 minutes.

---

## 1. Environment & Setup

### Prerequisites
- Python 3.10+ (tested on Python 3.11.9)
- PyTorch 2.6+ with CUDA support (tested on RTX 5070 Ti / CUDA 13.0)
- GCC / G++ (for Cython GADDAG shared library compilation)
- Playwright Chromium (`playwright install chromium`)

### Quick Setup Commands
```bash
cd /home/targed/Documents/Git/Alphable/Alphable_V3

# Activate project virtual environment
source ../venv/bin/activate

# Verify test suite (all 205 unit tests should pass)
pytest tests/
```

### Hardware Optimization: NVIDIA RTX 50-Series (Blackwell)
On RTX 50-series GPUs, PyTorch's native ATen CUDA convolution kernels run with maximum throughput without cuDNN library version mismatches (`torch.backends.cudnn.enabled = False` is automatically configured on startup).

---

## 2. Play Against HastyBot on Woogles

Launch an autonomous match series on [Woogles.io](https://woogles.io) using the production champion model `alphable_v3_macondo_v2.pth`:

```bash
python -m alphable.cli.main play woogles \
  --bot HastyBot \
  --games 5 \
  --model models/alphable_v3_macondo_v2.pth \
  --dict resources/CSW24.txt \
  --mode lookahead \
  --top-k 5 --simulations 10
```

### What You Will See
- The browser opens and automatically challenges `HastyBot`.
- Alphable reads the board, hand rack, and scores directly from the DOM.
- 1-ply Monte Carlo search evaluates candidate moves using Common Random Numbers (CRN), Super-Leaves stem equities, and defense modeling.
- When the bag hits 0, the deterministic exact endgame minimax solver kicks in, solving out winning sequences in $<0.001$ seconds.
- Replay JSON, GCG match records, and Macondo Analyzer reports are saved to `data/woogles/matches/`.

---

## 3. Offline Benchmark Evaluation

### Alphable vs GreedyBot
To test Alphable locally against a greedy point-maximizing opponent:

```bash
python -m alphable.cli.main eval baseline \
  --model models/alphable_v3_macondo_v2.pth \
  --opponent greedy \
  --games 10 \
  --mode lookahead
```
Outputs match replays and ASCII board logs to `data/vs_greedy/`.

### Head-to-Head Checkpoint Evaluation
Play two neural network models against each other with alternating first turns:

```bash
python -m alphable.cli.main eval matches \
  --model-a models/alphable_v3_macondo_v2.pth \
  --model-b models/alphable_v3_supervised_clean.pth \
  --games 20
```

---

## 4. Model Training & Distillation

### Grandmaster Macondo Knowledge Distillation (Recommended)
Fine-tune the neural network on Macondo Grandmaster Analyzer evaluations collected from Woogles:

```bash
python -m alphable.cli.main train distill-macondo \
  --matches-dir data/woogles/matches \
  --base-model models/alphable_v3_supervised_clean.pth \
  --output-model models/alphable_v3_macondo_v2.pth \
  --epochs 12 \
  --batch-size 64 \
  --lr 2e-4
```

### Supervised Foundation Pretraining
To train from raw game replays:
```bash
# 1. Prepare supervised samples with negative mining
python -m alphable.cli.main data prepare \
  --input data/woogles/data/training_dataset.jsonl \
  --output data/supervised/samples.jsonl \
  --workers 8

# 2. Train supervised model
python -m alphable.cli.main train supervised \
  --data data/supervised/samples.jsonl \
  --save-model models/my_supervised_model.pth \
  --epochs 10
```

---

## 5. Web Visualizer

Inspect match replays, board positions, and candidate move equities in an interactive React UI:

```bash
# Terminal 1: Backend API
cd visualizer/backend
python app.py

# Terminal 2: Frontend
cd visualizer/frontend
npm run dev
```
Open `http://localhost:5173` to explore games.
