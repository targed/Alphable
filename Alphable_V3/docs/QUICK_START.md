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

### Option A: Standard 1-Ply Lookahead MCTS (ResNet Model)
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

### Option B: SmolLM2 Transformer Candidate Ranker
Play live on Woogles using the fine-tuned autoregressive transformer ranker:

```bash
python -m alphable.cli.main play woogles \
  --bot HastyBot \
  --games 5 \
  --mode transformer \
  --transformer-model models/transformer_ranker_v2 \
  --dict resources/CSW24.txt
```

### Option C: Instant Zero-Delay Play (`--no-delay`)
Disable artificial pacing to submit moves immediately upon calculation:

```bash
python -m alphable.cli.main play woogles \
  --bot HastyBot \
  --mode transformer \
  --no-delay \
  --dict resources/CSW24.txt
```

### What You Will See
- The browser opens and automatically challenges `HastyBot`.
- Alphable reads the board, hand rack, and scores directly from the DOM.
- The engine evaluates candidate plays and submits moves smoothly (or instantly if `--no-delay` is passed).
- When the bag hits 0, the deterministic exact endgame minimax solver kicks in, solving out winning sequences in $<0.001$ seconds.
- Replay JSON, GCG match records, and Macondo Analyzer reports are saved to `data/woogles/matches/`.

---

## 3. Offline Benchmark Evaluation

### Transformer vs Neural Network Alphable Head-to-Head
Play the SmolLM2 Candidate Ranker directly against the 1-ply Monte Carlo ResNet engine:

```bash
python -m alphable.cli.main eval baseline \
  --opponent nn \
  --games 5 \
  --mode transformer \
  --transformer-model models/transformer_ranker_v2 \
  --model models/alphable_v3_macondo_v2.pth \
  --dict resources/CSW24.txt
```
Outputs turn logs, tile exchanges, and full match summaries to `data/vs_nn/`.

### Alphable vs GreedyBot
To test Alphable locally against a greedy point-maximizing baseline:

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
