# Alphable V3: Evaluation & Analytics Reference

This document covers evaluation runners, benchmark harnesses, replay logging, online platform analysis, and analytical visualization tools located in [`src/alphable/eval/`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/eval), [`src/alphable/platform/`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/platform), [`src/alphable/logging/`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/logging), and the visualizer frontend.

---

## 1. `evaluate_matches.py` ([`src/alphable/eval/evaluate_matches.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/eval/evaluate_matches.py))

Direct head-to-head match evaluation between two distinct model checkpoints (e.g. Model A vs Model B) to validate model updates before deployment.

### Features
- **Alternating First Player:** Alternates which model plays first (Turn 0) on every game to eliminate first-move advantage bias.
- **Move Selection:** Uses shared `evaluate_moves` with equity formula $\text{Equity} = \text{Points} + 25.0 \times V(s')$.
- **Metrics Computed:**
  - Model A Wins / Model B Wins / Draws
  - Model A Win Rate
  - Average Score Differential ($\text{Score}_A - \text{Score}_B$)
  - Bingo counts per player

### CLI Execution
```bash
python -m alphable.cli.main eval matches \
  --model-a models/alphable_v3_macondo_v2.pth \
  --model-b models/alphable_v3_supervised_clean.pth \
  --games 20 \
  --infer-batch-size 256
```

---

## 2. `evaluate_vs_baseline.py` ([`src/alphable/eval/evaluate_vs_baseline.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/eval/evaluate_vs_baseline.py))

Benchmark evaluation harness testing an Alphable agent against automated baselines (`random`, `greedy`) or pitting the SmolLM2 Candidate Ranker directly against the ResNet Neural Network engine (`nn`).

### Features
- **Opponent Types:**
  - `random`: Randomly selects any legal Scrabble play.
  - `greedy`: Evaluates all legal plays and selects the play with the maximum immediate points.
  - `nn` / `nn_lookahead`: Full Alphable Neural Network player using 1-ply Monte Carlo lookahead search under Common Random Numbers (CRN).
  - `nn_0ply`: Neural Network player using fast 0-ply value network evaluation.
- **Search Modes:**
  - `bc_0ply`: Fast 0-ply argmax evaluation using the value network.
  - `lookahead`: 1-ply Monte Carlo lookahead search with minimax opponent reply equity deduction.
  - `transformer`: SmolLM2 Candidate Ranker evaluating top candidate plays via single-token autoregressive attention.
- **First-Class Scrabble Actions:**
  - Full support for `PLAY`, `PASS`, and `EXCHANGE`.
  - On `EXCHANGE` actions (e.g. `EXCHANGE(A,I,I,O,O,O)` to fix bad leaves), the engine draws replacements from the tile bag, returns the exchanged tiles, and tracks rack state accurately without board placement errors.
- **Logging & Artifacts:**
  - Outputs detailed move-by-move replay JSON and human-readable ASCII game boards in TXT format to `data/vs_<opponent>/`.
  - Generates comprehensive run summaries tracking win rate, score margins, average points per move, and bingo counts.

### CLI Execution
```bash
# 1. Evaluate Transformer vs ResNet NN Alphable head-to-head
python -m alphable.cli.main eval baseline \
  --opponent nn \
  --games 5 \
  --mode transformer \
  --transformer-model models/transformer_ranker_v2 \
  --model models/alphable_v3_macondo_v2.pth \
  --dict resources/CSW24.txt

# 2. Evaluate Transformer vs Greedy baseline
python -m alphable.cli.main eval baseline \
  --opponent greedy \
  --games 10 \
  --mode transformer \
  --transformer-model models/transformer_ranker_v2 \
  --dict resources/CSW24.txt

# 3. Standard 1-ply Monte Carlo NN search vs Greedy baseline
python -m alphable.cli.main eval baseline \
  --model models/alphable_v3_macondo_v2.pth \
  --opponent greedy \
  --games 20 \
  --mode lookahead \
  --top-k 5 --simulations 10
```

---

## 3. Platform Evaluation & Woogles Runner (`runner.py` & `adapter.py`)

Located in [`src/alphable/platform/runner.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/platform/runner.py) and [`src/alphable/platform/woogles/adapter.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/platform/woogles/adapter.py).

This subsystem runs autonomous match series on Woogles.io against bots like `HastyBot` or human opponents, and collects high-resolution telemetry.

### Data Artifacts Generated Per Match
For every completed game, a directory is created under `data/woogles/matches/<timestamp>_<game_id>/`:
1. **`game.gcg`:** Official Scrabble Game Championship format record containing every rack, move coordinates, word, turn points, and running cumulative scores.
2. **`analysis.json`:** Comprehensive post-game evaluation extracted from Woogles' grandmaster **Macondo Analyzer**. For every turn, contains Macondo's top recommended moves, expected point equities, and winning percentages.
3. **`replay.json`:** Detailed board-by-board states and move decisions for use by the Alphable web visualizer.
4. **`summary.json`:** Per-game summary (winner, final scores, turn count, duration).

### Series Summaries (`series.json`)
At the end of an $N$-game series, a consolidated summary is saved to `data/woogles/summaries/run_<timestamp>_series.json`:
- Overall Wins / Losses / Draws and Win Rate percentage.
- Average Score Differential and Average Score per Game.
- Match list with individual scores and links to GCG/analysis files.

### Macondo Equity Loss Measurement
By analyzing `analysis.json`, we compute the **equity leakage per turn** relative to Macondo's optimal play:

$$\Delta \text{Equity}_{\text{turn}} = \text{Equity}_{\text{Macondo Top 1}} - \text{Equity}_{\text{Alphable Move}}$$

- **Historical Benchmark:**
  - Baseline V3: Lost **$-4.85$ pts/turn** against HastyBot (20% win rate).
  - 5-Pillars Engine: Reduced loss to **$-2.30$ pts/turn** (41.3% win rate).
  - Final CRN + Blank Fixes: Reduced loss to **$< -1.0$ pt/turn**, achieving parity and winning series against HastyBot!

---

## 4. `analyze.py` ([`src/alphable/eval/analyze.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/eval/analyze.py))

Automated analytics tool that parses training history JSON files and generates presentation-ready loss and metric progression plots.

### Features
- Handles both supervised training histories (`train_loss`, `val_loss`, `mean_target`, `mean_pred`) and RL histories (`train_loss`, `val_loss`, `time`).
- Renders dual-axis charts with training loss, validation loss convergence, and epoch durations using Matplotlib.
- Accessible directly via the CLI subcommand `alphable eval plot`.

### CLI Execution
```bash
python -m alphable.cli.main eval plot \
  --history models/alphable_v3_macondo_v2_history.json \
  --output reports/macondo_v2_progress.png
```

---

## 5. `game_logger.py` ([`src/alphable/logging/game_logger.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/logging/game_logger.py))

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
- **Replay JSON Export:** Saves full structured game state for consumption by the Web Visualizer.

---

## 6. Alphable Web Visualizer

Located in [`visualizer/`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/visualizer).

A modern, interactive React/Vite web application that allows developers and Scrabble analysts to step through matches turn-by-turn.

### Visualizer Features
- **Interactive Board Grid:** Highlights newly placed tiles, multipliers covered, and cross-words formed.
- **Candidate Move Inspector:** Displays all top-$K$ candidate moves evaluated by 1-ply search, along with their raw points, leave equity, defense bonus, and neural network value.
- **Score Differential Timeline:** Interactive graph showing lead changes and momentum shifts over the course of the match.
- **Tile Bag Tracker:** Displays all remaining unseen tiles and odds of drawing key letters.

### Running the Visualizer
```bash
# Terminal 1: Launch Backend API
cd visualizer/backend
python app.py

# Terminal 2: Launch Frontend
cd visualizer/frontend
npm run dev
```
Open `http://localhost:5173` in your browser to view match replays.
