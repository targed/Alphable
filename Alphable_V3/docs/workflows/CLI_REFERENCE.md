# Alphable V3: Complete CLI Reference Manual

The unified CLI entry point is `python -m alphable.cli.main` (run with the virtual environment python: `/home/targed/Documents/Git/Alphable/venv/bin/python`).

---

## Command Hierarchy

```
alphable
├── play
│   └── woogles          # Play autonomous Scrabble matches on Woogles.io
├── data
│   └── prepare          # Ingest replays and build supervised dataset
├── train
│   ├── supervised       # Train foundation value network on supervised expert samples
│   ├── distill-macondo  # Distill Macondo Grandmaster Analyzer evaluations into value net
│   ├── rl               # Train value network on self-play JSONL trajectories
│   └── rl-selfplay      # AlphaZero-style in-memory self-play outcome RL
├── selfplay
│   └── generate         # Simulate self-play / anti-greedy curriculum games
├── eval
│   ├── matches          # Run head-to-head match series between two model checkpoints
│   ├── baseline         # Run benchmark matches against RandomBot or GreedyBot
│   └── plot             # Plot training history curves to PNG
├── search
│   └── debug            # Interactive 1-ply Monte Carlo search inspector
└── pipeline
    └── calibrate        # Run automated calibration and hyperparameter tuning cycle
```

---

## 1. `alphable play woogles`

Autonomous online Scrabble engine interface running on [Woogles.io](https://woogles.io) via Playwright browser automation.

```bash
python -m alphable.cli.main play woogles [OPTIONS]
```

### Options Reference
| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--bot` | `str` | `HastyBot` | Opponent bot name (`HastyBot`, `BestBot`, `BeginnerBot`). |
| `--model` | `str` | `models/alphable_v3_macondo_v2.pth` | Path to neural network checkpoint to use. |
| `--dict` | `str` | `resources/CSW24.txt` | Dictionary text file (`resources/CSW24.txt` or `resources/NWL2023.txt`). |
| `--mode` | `str` | `lookahead` | Decision engine mode: `lookahead` (1-ply Monte Carlo), `bc_0ply` (fast argmax), or `transformer` (SmolLM2 attention candidate ranker). |
| `--transformer-model` | `str` | `HuggingFaceTB/SmolLM2-135M-Instruct` | HuggingFace model repo or local directory for transformer ranker mode. |
| `--top-k` | `int` | `5` | Number of candidate moves evaluated in lookahead / transformer search. |
| `--simulations` | `int` | `10` | Number of opponent leave simulations per candidate under CRN (lookahead mode). |
| `--value-weight` | `float` | `25.0` | Weight multiplier $W$ applied to strategic leave values. |
| `--games` | `int` | `1` | Number of matches to play in sequence before terminating. |
| `--time-control` | `str` | `15+0` | Time control string (e.g. `15+0`, `5+0`, `3+0`). |
| `--game-mode` | `str` | `realtime` | Game mode: `realtime` or `correspondence`. |
| `--opponent` | `str` | `bot` | Opponent type: `bot` or `human`. |
| `--takeover` | `flag` | `False` | Launch browser and let human log in/seek, then Alphable takes over. |
| `--auto-seek` | `flag` | `False` | Post an open public challenge in the lobby for human matchmaking. |
| `--game-url` | `str` | `None` | Join and play directly on an existing game URL. |
| `--headless` | `flag` | `False` | Run browser in background without visible window (headed is default). |
| `--delay-min` | `float` | `2.0` | Minimum natural thinking delay in seconds before submitting move. |
| `--delay-max` | `float` | `6.0` | Maximum natural thinking delay in seconds before submitting move. |
| `--profile-dir` | `str` | `~/.alphable/woogles_profile` | Directory for persistent browser login session. |
| `--output-dir` | `str` | `data/woogles/games` | Directory to save match replays and summaries. |
| `--no-gcg` | `flag` | `False` | Disable automatic GCG file export upon match completion. |
| `--no-analysis`| `flag` | `False` | Disable automatic post-game Macondo Analyzer evaluations export. |
| `--keep-open` | `flag` | `True` | Keep browser open between games. Use `--no-keep-open` to close. |

### Practical Examples
```bash
# Play a 15-game series against HastyBot in lookahead mode
python -m alphable.cli.main play woogles \
  --bot HastyBot \
  --games 15 \
  --model models/alphable_v3_macondo_v2.pth \
  --dict resources/CSW24.txt \
  --mode lookahead \
  --top-k 5 --simulations 10

# Fast evaluation in 0-ply mode (sub-second moves)
python -m alphable.cli.main play woogles \
  --bot HastyBot \
  --games 5 \
  --model models/alphable_v3_macondo_v2.pth \
  --mode bc_0ply \
  --delay-min 1.0 --delay-max 2.0
```

---

## 2. `alphable train distill-macondo`

Distills Macondo Grandmaster Analyzer ground-truth equities from completed Woogles games into `AlphableValueNet`.

```bash
python -m alphable.cli.main train distill-macondo [OPTIONS]
```

### Options Reference
| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--matches-dir` | `str` | `data/woogles/matches` | Directory containing match subdirectories with `game.gcg` and `analysis.json`. |
| `--cache-path` | `str` | `data/macondo_distill_cache.pt` | Path to cache extracted PyTorch tensor dataset for fast reloading. |
| `--base-model` | `str` | `models/alphable_v3_supervised_clean.pth` | Base checkpoint to fine-tune from. |
| `--output-model`| `str` | `models/alphable_v3_macondo_v2.pth` | Output checkpoint path for distilled network. |
| `--epochs` | `int` | `12` | Number of fine-tuning epochs. |
| `--batch-size` | `int` | `64` | Training batch size. |
| `--lr` | `float` | `2e-4` | Initial learning rate with Cosine Annealing. |

### Practical Example
```bash
python -m alphable.cli.main train distill-macondo \
  --matches-dir data/woogles/matches \
  --base-model models/alphable_v3_supervised_clean.pth \
  --output-model models/alphable_v3_macondo_v2.pth \
  --epochs 12 \
  --batch-size 64 \
  --lr 2e-4
```

---

## 3. `alphable train rl-selfplay`

Runs pure outcome-driven self-play reinforcement learning on CUDA.

```bash
python -m alphable.cli.main train rl-selfplay [OPTIONS]
```

### Options Reference
| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--model` | `str` | `models/alphable_v3_macondo_v2.pth` | Champion model to initialize self-play. |
| `--save-model` | `str` | `models/alphable_v3_rl_gen5.pth` | Output checkpoint destination. |
| `--dict` | `str` | `resources/CSW24.txt` | Dictionary lexicon path. |
| `--games` | `int` | `1000` | Number of self-play games to simulate. |
| `--state-size` | `int` | `63` | State vector dimension (`63` for bag tracking, `36` for legacy). |
| `--batch-size` | `int` | `128` | Training batch size for PyTorch updates. |
| `--lr` | `float` | `1e-4` | Learning rate for AdamW optimizer. |
| `--epochs` | `int` | `4` | Training epochs over the generated self-play games. |

### Practical Example
```bash
python -m alphable.cli.main train rl-selfplay \
  --model models/alphable_v3_macondo_v2.pth \
  --save-model models/alphable_v3_rl_gen5.pth \
  --dict resources/CSW24.txt \
  --games 1000 \
  --state-size 63 \
  --epochs 4
```

---

## 4. `alphable train transformer-ranker`

Fine-tunes the autoregressive `SmolLM2-135M` candidate ranker on grandmaster human match decisions extracted from Woogles replays.

```bash
python -m alphable.cli.main train transformer-ranker [OPTIONS]
```

### Options Reference
| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--model-name` | `str` | `HuggingFaceTB/SmolLM2-135M-Instruct` | Base HuggingFace transformer model repository. |
| `--matches-dir`| `str` | `data/woogles/matches` | Directory containing Woogles match replay directories with `analysis.json`. |
| `--output-dir` | `str` | `models/transformer_ranker_v1` | Directory to save fine-tuned HuggingFace model and tokenizer checkpoints. |
| `--dict` | `str` | `resources/CSW24.txt` | Dictionary path for GADDAG move generation during candidate extraction. |
| `--epochs` | `int` | `3` | Number of fine-tuning epochs. |
| `--batch-size` | `int` | `8` | Training batch size. |
| `--lr` | `float` | `5e-5` | Learning rate for AdamW optimizer with cosine schedule. |
| `--max-turns` | `int` | `None` | Optional limit on the number of training turns (useful for fast debugging). |
| `--candidate-k`| `int` | `5` | Number of candidate moves included in each decision prompt. |

### Practical Example
```bash
python -m alphable.cli.main train transformer-ranker \
  --matches-dir data/woogles/matches \
  --output-dir models/transformer_ranker_v1 \
  --epochs 3 \
  --batch-size 8 \
  --lr 5e-5
```

---

## 5. `alphable data prepare`

Processes raw game replays (JSON/GCG) into compact supervised dataset samples with hard-negative mining and continuous deficit scaling.

```bash
python -m alphable.cli.main data prepare [OPTIONS]
```

### Options Reference
| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--input` | `str` | `data/woogles/data/training_dataset.jsonl` | Input file with game replays. |
| `--output` | `str` | `data/supervised/samples.jsonl` | Output JSONL samples file. |
| `--dict` | `str` | `resources/CSW24.txt` | Dictionary text file path. |
| `--negatives` | `int` | `4` | Number of hard-negative alternative plays to retain per position. |
| `--workers` | `int` | `cpu_count()` | Number of parallel worker processes. |
| `--chunksize` | `int` | `8` | Worker queue chunk size. |
| `--max-games` | `int` | `None` | Max number of games to process. |

### Practical Example
```bash
python -m alphable.cli.main data prepare \
  --input data/woogles/data/training_dataset.jsonl \
  --output data/supervised/samples.jsonl \
  --dict resources/CSW24.txt \
  --negatives 4 --workers 8
```

---

## 5. `alphable train supervised`

Trains `AlphableValueNet` on the supervised dataset of expert after-states.

```bash
python -m alphable.cli.main train supervised [OPTIONS]
```

### Options Reference
| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--data` | `str` | `data/supervised/samples.jsonl` | Supervised dataset path. |
| `--resume-model` | `str` | `None` | Initial checkpoint to warm-start weights from. |
| `--save-model` | `str` | `models/alphable_v3_supervised_clean.pth` | Output checkpoint path. |
| `--epochs` | `int` | `10` | Maximum number of training epochs. |
| `--batch-size` | `int` | `128` | Training batch size. |
| `--lr` | `float` | `3e-4` | Initial learning rate. |
| `--weight-decay` | `float` | `1e-4` | AdamW weight decay. |
| `--train-split` | `float` | `0.9` | Ratio of data used for training (remainder for validation). |
| `--early-stop-patience`| `int` | `4` | Non-improving epochs before early stopping. |
| `--device` | `str` | `auto` | Training device (`auto`, `cuda`, `cpu`). |

---

## 6. `alphable eval matches`

Evaluates two checkpoints against each other in head-to-head match series.

```bash
python -m alphable.cli.main eval matches [OPTIONS]
```

### Options Reference
| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--model-a` | `str` | *Required* | Path to Model A checkpoint. |
| `--model-b` | `str` | *Required* | Path to Model B checkpoint. |
| `--games` | `int` | `20` | Number of games to play (alternating Turn 0). |
| `--dict` | `str` | `resources/CSW24.txt` | Dictionary lexicon path. |
| `--infer-batch-size`| `int` | `256` | Inference batch size. |

### Practical Example
```bash
python -m alphable.cli.main eval matches \
  --model-a models/alphable_v3_macondo_v2.pth \
  --model-b models/alphable_v3_supervised_clean.pth \
  --games 20
```

---

## 7. `alphable eval baseline`

Runs benchmark series against automated test baselines (`greedy` or `random`).

```bash
python -m alphable.cli.main eval baseline [OPTIONS]
```

### Options Reference
| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--model` | `str` | *Required* | Checkpoint path to evaluate. |
| `--opponent` | `str` | `greedy` | Opponent type: `greedy` or `random`. |
| `--games` | `int` | `10` | Number of games to simulate. |
| `--mode` | `str` | `lookahead` | Search mode: `lookahead` or `bc_0ply`. |
| `--top-k` | `int` | `5` | Top-K candidate moves evaluated in lookahead. |
| `--simulations` | `int` | `10` | Simulations per candidate. |

---

## 8. `alphable eval plot`

Generates publication-quality PNG charts of training and validation loss curves.

```bash
python -m alphable.cli.main eval plot [OPTIONS]
```

### Options Reference
| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--history` | `str` | *Required* | Path to JSON history file exported during training. |
| `--output` | `str` | `reports/progress.png` | Destination image filepath for PNG plot. |

### Practical Example
```bash
python -m alphable.cli.main eval plot \
  --history models/alphable_v3_macondo_v2_history.json \
  --output reports/macondo_v2_progress.png
```
