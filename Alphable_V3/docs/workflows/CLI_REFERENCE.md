# Alphable V3: CLI Reference Manual

The unified CLI entry point is `python -m alphable.cli.main` (or the executable `alphable` if installed in editable mode).

---

## Command Hierarchy

```
alphable
├── data
│   └── prepare          # Generate supervised after-state dataset
├── train
│   ├── supervised       # Train value network on supervised expert samples
│   └── rl               # Train value network on self-play outcomes
├── selfplay
│   └── generate         # Generate self-play / anti-greedy curriculum games
├── eval
│   ├── matches          # Run head-to-head match between two checkpoints
│   ├── baseline         # Run benchmark against RandomBot or GreedyBot
│   └── plot             # Plot training history curves to PNG
└── search
    └── debug            # Interactive 1-ply search inspector
```

---

## 1. `alphable data prepare`
Processes raw game replays (JSON/GCG) into compact supervised dataset samples.

```bash
python -m alphable.cli.main data prepare [OPTIONS]
```

### Options
| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--input` | `str` | `data/woogles/data/training_dataset.jsonl` | Input file with game replays |
| `--output` | `str` | `data/supervised/samples.jsonl` | Output JSONL samples file |
| `--dict` | `str` | `resources/CSW24.txt` | Dictionary text file path |
| `--negatives` | `int` | `4` | Number of hard-negative alternative plays to retain per position |
| `--workers` | `int` | `cpu_count()` | Number of parallel worker processes |
| `--chunksize` | `int` | `8` | Worker queue chunk size |
| `--max-games` | `int` | `None` | Max number of games to process (useful for testing) |

---

## 2. `alphable train supervised`
Trains the value network on expert supervised samples.

```bash
python -m alphable.cli.main train supervised [OPTIONS]
```

### Options
| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--data` | `str` | `data/supervised/samples.jsonl` | Supervised dataset path |
| `--resume-model` | `str` | `None` | Initial checkpoint to warm-start weights from |
| `--save-model` | `str` | `models/alphable_v3_supervised.pth` | Output checkpoint path |
| `--epochs` | `int` | `10` | Maximum number of training epochs |
| `--batch-size` | `int` | `128` | Training batch size (GPU recommended: 128) |
| `--lr` | `float` | `3e-4` | Initial learning rate |
| `--weight-decay` | `float` | `1e-4` | AdamW weight decay |
| `--train-split` | `float` | `0.9` | Ratio of data used for training (remainder for validation) |
| `--early-stop-patience`| `int` | `4` | Number of non-improving validation epochs before early stopping |
| `--device` | `str` | `auto` | Device to train on (`auto`, `cuda`, `cpu`) |

---

## 3. `alphable selfplay generate`
Simulates Scrabble games to generate reinforcement learning trajectories.

```bash
python -m alphable.cli.main selfplay generate [OPTIONS]
```

### Options
| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--model` | `str` | *Required* | Checkpoint path for main player |
| `--opponent-models` | `list` | `None` | Additional opponent checkpoints to sample from |
| `--games` | `int` | `100` | Number of self-play games to simulate |
| `--output` | `str` | `data/rl/rl_samples.jsonl` | Output dataset file path |
| `--append` | `flag` | `False` | Append samples to existing file instead of overwriting |
| `--vs-greedy` | `flag` | `False` | Player 1 plays using GreedyBot (highest-point plays) |
| `--keep-p0-only` | `flag` | `False` | **Crucial:** Only log Player 0's moves (prevents greedy contamination) |
| `--device` | `str` | `cuda` | Inference device (`cuda` or `cpu`) |
| `--infer-batch-size`| `int` | `256` | Max batch size for neural network evaluations |
| `--reward-mode` | `str` | `blend` | Reward function: `blend`, `outcome`, or `margin` |
| `--temperature-start`| `float`| `0.20` | Sampling temperature for opening turns |
| `--temperature-end` | `float`| `0.10` | Sampling temperature for late game turns |

---

## 4. `alphable train rl`
Trains the value network on reinforcement learning self-play outcomes.

```bash
python -m alphable.cli.main train rl [OPTIONS]
```

### Options
| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--data` | `str` | `data/rl/rl_samples.jsonl` | Self-play dataset path |
| `--init-model` | `str` | `models/alphable_v3_supervised.pth`| Checkpoint to initialize weights |
| `--save-model` | `str` | `models/alphable_v3_rl_gen2.pth` | Output checkpoint path |
| `--epochs` | `int` | `15` | Maximum number of training epochs |
| `--batch-size` | `int` | `128` | Batch size |
| `--lr` | `float` | `3e-4` | Learning rate |
| `--weight-decay` | `float` | `1e-4` | AdamW weight decay |
| `--early-stop` | `int` | `4` | Validation patience |

---

## 5. `alphable eval matches`
Runs head-to-head matches between two model checkpoints.

```bash
python -m alphable.cli.main eval matches [OPTIONS]
```

### Options
| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--model-a` | `str` | *Required* | Checkpoint path for Model A |
| `--model-b` | `str` | *Required* | Checkpoint path for Model B |
| `--games` | `int` | `50` | Number of games (first move alternates each game) |
| `--temperature` | `float` | `0.0` | Move sampling temperature (0.0 = greedy argmax) |
| `--top-k` | `int` | `3` | Pool size when temperature > 0 |
| `--dict` | `str` | `resources/CSW24.txt` | Scrabble lexicon dictionary |

---

## 6. `alphable eval baseline`
Evaluates a model against automated benchmark bots.

```bash
python -m alphable.cli.main eval baseline [OPTIONS]
```

### Options
| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--model` | `str` | *Required* | Model checkpoint to evaluate |
| `--opponent` | `str` | `greedy` | Opponent type: `greedy` or `random` |
| `--games` | `int` | `10` | Number of evaluation games |
| `--mode` | `str` | `lookahead` | Search mode: `lookahead` (1-ply) or `bc_0ply` (0-ply) |
| `--output-dir` | `str` | `data/vs_<opponent>` | Output directory for replays and summaries |

---

## 7. `alphable eval plot`
Generates training history curves.

```bash
python -m alphable.cli.main eval plot [OPTIONS]
```

### Options
| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--history` | `str` | *Required* | Path to `<model>_history.json` |
| `--output` | `str` | `reports/progress.png` | Destination PNG image file |
