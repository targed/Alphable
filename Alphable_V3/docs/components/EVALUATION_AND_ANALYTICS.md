# Alphable V3: Evaluation & Analytics Reference

This document covers evaluation runners, benchmark harnesses, replay logging, and analytical visualization tools located in [`src/alphable/eval/`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/eval), [`src/alphable/logging/`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/logging), and [`src/alphable/cli/`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/cli).

---

## 1. `evaluate_matches.py` ([`src/alphable/eval/evaluate_matches.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/eval/evaluate_matches.py))

Direct head-to-head match evaluation between two distinct model checkpoints (e.g. Model A vs Model B).

### Features
- **Alternating First Player:** Alternates which model plays first (Turn 0) on every game to eliminate first-move advantage bias.
- **Move Selection:** Uses shared `evaluate_moves` with equity formula $\text{Equity} = \text{Points} + 25.0 \times V(s')$.
- **Metrics Computed:**
  - Model A Wins / Model B Wins / Draws
  - Model A Win Rate
  - Average Score Differential ($\text{Score}_A - \text{Score}_B$)

### CLI Syntax
```bash
python -m alphable.cli.main eval matches \
  --model-a models/alphable_v3_rl_gen2.pth \
  --model-b models/alphable_v3_supervised_clean.pth \
  --games 20 \
  --infer-batch-size 256
```

---

## 2. `evaluate_vs_baseline.py` ([`src/alphable/eval/evaluate_vs_baseline.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/eval/evaluate_vs_baseline.py))

Benchmark evaluation harness testing an Alphable model against standardized automated baselines (`random` or `greedy`).

### Features
- **Opponent Types:**
  - `random`: Randomly selects any legal Scrabble play.
  - `greedy`: Evaluates all legal plays and selects the play with the maximum immediate points.
- **Search Modes:**
  - `bc_0ply`: Fast 0-ply argmax evaluation using the value network.
  - `lookahead`: 1-ply Monte Carlo lookahead search with minimax opponent reply equity deduction.
- **Logging & Artifacts:**
  - Outputs detailed move-by-move replay JSON and human-readable ASCII game boards in TXT format to `data/vs_<opponent>/`.
  - Generates comprehensive run summaries tracking win rate, score margins, average points per move, and bingo counts.

### CLI Syntax
```bash
python -m alphable.cli.main eval baseline \
  --model models/alphable_v3_rl_gen2.pth \
  --opponent greedy \
  --games 10
```

---

## 3. `analyze.py` ([`src/alphable/eval/analyze.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/eval/analyze.py))

Automated analytics tool that parses training history JSON files and generates presentation-ready loss and metric progression plots.

### Features
- Handles both supervised training histories (`train_loss`, `val_loss`, `mean_target`, `mean_pred`) and RL histories (`train_loss`, `val_loss`, `time`).
- Renders dual-axis charts with training loss, validation loss convergence, and epoch durations using Matplotlib.
- Accessible directly via the CLI subcommand `alphable eval plot`.

### CLI Syntax
```bash
python -m alphable.cli.main eval plot \
  --history models/alphable_v3_rl_gen2_history.json \
  --output reports/rl_gen2_progress.png
```

---

## 4. `game_logger.py` ([`src/alphable/logging/game_logger.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/logging/game_logger.py))

Structured game logging system recording every event of a Scrabble match for replay analysis and visualization.

### Data Logged
- **Game Metadata:** Player names, model paths, search simulation settings, dictionary used, timestamp.
- **Per-Turn Move Records (`MoveEntry`):**
  - Turn index and active player.
  - Rack before play.
  - Tiles played, word formed, start row/column, and direction.
  - Points earned and new cumulative score.
  - Top candidate moves considered by the neural network with predicted values.
  - Board visualizer string representation.
- **Replay JSON Export:** Saves full structured game state for use by the Web Visualizer.

---

## 5. `main.py` ([`src/alphable/cli/main.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/cli/main.py))

Unified entry point for all Alphable operations. Dispatches subcommands cleanly to their respective modules:
- `alphable data prepare`: Dataset generation via `prepare_dataset.py`
- `alphable train supervised`: Supervised learning via `train_supervised.py`
- `alphable train rl`: Reinforcement learning via `train_rl.py`
- `alphable selfplay generate`: Self-play curriculum via `self_play.py`
- `alphable eval matches`: Head-to-head match evaluation via `evaluate_matches.py`
- `alphable eval baseline`: Automated benchmark evaluation via `evaluate_vs_baseline.py`
- `alphable eval plot`: Loss curve generation via `analyze.py`
- `alphable search debug`: Interactive search debugging tool
