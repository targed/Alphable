# Alphable V3: Quick Start Guide

This guide gets you up and running with **Alphable V3** in minutes.

---

## 1. Environment & Installation

### Prerequisites
- Python 3.10+ (tested on Python 3.11.9)
- PyTorch 2.6+ with CUDA support (tested on CUDA 13.0 / RTX 5070 Ti)
- GCC / G++ for compiling the C++ GADDAG Cython extension

### Setup
```bash
# Clone the repository
git clone https://github.com/targed/Alphable.git
cd Alphable/Alphable_V3

# Activate virtual environment
source ../venv/bin/activate

# Install Alphable in editable development mode
pip install -e .
```

### Hardware Notice: Blackwell GPUs (RTX 50-Series)
On NVIDIA RTX 50-series GPUs (Blackwell architecture), `torch.backends.cudnn.enabled = False` is automatically configured in `src/alphable/__init__.py` to prevent dynamic symbol mismatches with `cudnnGetVersion`. Native ATen CUDA convolution kernels run at full throughput (**~1,900 samples/sec**).

---

## 2. Test the Engine Immediately

Verify that the Cython GADDAG engine, neural network, and 78 unit tests pass:

```bash
pytest
```

---

## 3. Run Your First Game

### Play Alphable vs GreedyBot
Evaluate Alphable with 1-ply lookahead search against a greedy opponent:

```bash
python -m alphable.cli.main eval baseline \
  --model models/alphable_v3_rl_gen2.pth \
  --opponent greedy \
  --games 2
```

Replay JSON and ASCII game boards are saved to `data/vs_greedy/`.

---

## 4. Evaluate Head-to-Head Checkpoints

Play a direct match between two trained model generations:

```bash
python -m alphable.cli.main eval matches \
  --model-a models/alphable_v3_rl_gen2.pth \
  --model-b models/alphable_v3_supervised_clean.pth \
  --games 10
```

---

## 5. Training in 3 Simple Commands

### Step 1: Generate Clean Supervised Samples
```bash
python -m alphable.cli.main data prepare \
  --input data/woogles/data/training_dataset.jsonl \
  --output data/supervised/samples_woogles_clean.jsonl \
  --workers 16
```

### Step 2: Supervised Pretraining
```bash
python -m alphable.cli.main train supervised \
  --data data/supervised/samples_woogles_clean.jsonl \
  --save-model models/my_supervised_model.pth \
  --epochs 10
```

### Step 3: Self-Play Curriculum & RL Fine-Tuning
```bash
# Generate mirror games
python -m alphable.cli.main selfplay generate \
  --model models/my_supervised_model.pth \
  --games 50 \
  --output data/rl/my_curriculum.jsonl \
  --device cuda

# Generate anti-greedy defense games
python -m alphable.cli.main selfplay generate \
  --model models/my_supervised_model.pth \
  --games 25 \
  --output data/rl/my_curriculum.jsonl \
  --device cuda \
  --vs-greedy \
  --keep-p0-only \
  --append

# Train RL Value Network
python -m alphable.cli.main train rl \
  --data data/rl/my_curriculum.jsonl \
  --init-model models/my_supervised_model.pth \
  --save-model models/my_rl_model.pth \
  --epochs 15
```

---

## 6. Plot Training Analytics

Generate high-resolution loss curves from training history JSON:

```bash
python -m alphable.cli.main eval plot \
  --history models/my_rl_model_history.json \
  --output reports/my_rl_progress.png
```

---

## 7. Next Steps & Detailed References

For in-depth documentation, see:
- [**Documentation Index**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/README.md)
- [**Neural Network Architecture**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/architecture/ARCHITECTURE.md)
- [**Search & Move Equity**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/architecture/SEARCH_AND_EQUITY.md)
- [**CLI Reference Manual**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/workflows/CLI_REFERENCE.md)
