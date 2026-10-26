# Alphable Visualizer Studio 2.0

Alphable Visualizer Studio is a broadcast-quality, cross-engine Scrabble AI interface. It decouples game analysis, tournament inspection, and interactive gameplay from specific engine implementations, allowing you to seamlessly interact with **Alphable V4** (BAMS + Native C MAGPIE), **Alphable V3** (Macondo ResNet / Transformer), **Base MAGPIE**, and baseline bots from a single platform.

---

## ⚡ Quickstart

From the repository root:

```bash
./start_visualizer.sh
```

Or from the `visualizer/` folder:

```bash
cd visualizer
./run.sh
```

By default, the server serves the pre-compiled React single-page application directly from the Python/Flask backend on `http://localhost:5000` and automatically opens your browser.

### CLI Flags
- `./visualizer/run.sh --dev`: Runs the React development server on port 3000 alongside Flask on port 5000 for hot-reloading.
- `./visualizer/run.sh --build`: Recompiles the React frontend production bundle before launching.
- `./visualizer/run.sh --port 8080`: Runs the studio on a custom port.
- `./visualizer/run.sh --no-browser`: Runs headlessly without attempting to open a browser window.

---

## 🎮 Features

### 1. Interactive Play Studio (`/play`)
- Play live against any AI engine: **Alphable V4** (select any preset: `latest`, `5-frontiers`, `v4-baseline`, `rl-gen1`), **Alphable V3** (Macondo ResNet / Transformer), **Base MAGPIE**, or **Greedy**.
- Interactive 15×15 Scrabble board with premium square highlights (TW, DW, TL, DL, Center Star).
- Point-and-click or coordinate word placement with real-time lexicon validation against CSW24 / NWL23.
- **💡 Live Hint**: Instantly request the active engine's top move recommendation with expected point value and strategic equity.
- **Candidate Evaluation Table**: Inspect the top candidate moves considered by the AI with board score, leave tiles, and BAMS value scores.

### 2. Game Replay & Tournament Explorer (`/replays`)
- Unified game browser supporting:
  - Historical V3 game logs (`data/vs_greedy`, `data/vs_random`, `data/vs_nn`, `data/results`).
  - V4 official tournament series runs (`data/tournaments/run_*.json`).
- Turn-by-turn playback with transport controls: First turn (⏮), Prev turn (⏪), Play/Pause (▶/⏸), Next turn (⏩), and Last turn (⏭).
- Adjustable playback speed (0.5×, 1×, 2×, 4×).
- Interactive scrubbing timeline slider with keyboard shortcuts.
- Turn log table showing word played, score earned, and player turn breakdown.

### 3. Cross-Engine Position Comparison (`/compare`)
- Test and analyze any board position and rack.
- Click any cell to place or clear tiles, or load pre-configured scenarios (Opening, QUIZ hook, RETINAS bingo rack).
- Click **"⚡ Compare Engines"** to run side-by-side evaluations across:
  - **Alphable V4**: ResNet-18 + Cross-Attention BAMS Monte Carlo valuation.
  - **Alphable V3**: Macondo ResNet valuation with leave heuristics.
  - **Base MAGPIE**: Classical C KLV static equity top move.
  - **Score Greedy**: Maximum immediate board points.
- Compares move choices, coordinates, point yields, and equity rankings side-by-side.

---

## 🏛️ Architecture & Backend API

```
visualizer/
├── run.sh                          # Universal launcher script
├── requirements.txt                # Flask, Flask-CORS
├── backend/
│   ├── app.py                      # Flask REST API & static bundle server
│   ├── adapters/
│   │   ├── base.py                 # Abstract BaseEngineAdapter
│   │   ├── v4_adapter.py           # Alphable V4 BAMS / MAGPIE adapter
│   │   ├── v3_adapter.py           # Alphable V3 GADDAG / Macondo adapter
│   │   └── baseline_adapter.py     # Base MAGPIE & Greedy adapter
│   └── services/
│       └── replay_service.py       # Replay discovery and parsing
└── frontend/
    ├── package.json
    ├── build/                      # Production compiled assets
    └── src/
        ├── components/
        │   ├── Board.tsx           # 15×15 Scrabble grid with premium tiles
        │   ├── TileRack.tsx        # Player 7-tile rack with selection
        │   ├── PlayerHUD.tsx       # Scores, deltas, and bag count
        │   ├── CandidateTable.tsx  # Top-K candidate moves ranking table
        │   ├── EngineSelector.tsx  # Dynamic engine and checkpoint selector
        │   ├── GameReplayView.tsx  # Replay player and tournament records
        │   └── PositionAnalyzer.tsx# Side-by-side cross-engine evaluator
        └── App.tsx                 # Tabbed studio container
```

### Key API Endpoints
- `GET /api/health`: Server status and loaded engine capabilities.
- `GET /api/engines`: List available Scrabble engines (`v4`, `v3`, `magpie`, `greedy`).
- `GET /api/models?engine=<id>`: Checkpoints/presets registered for specified engine.
- `GET /api/games`: Discovered game replay summaries across categories.
- `GET /api/games/<category>/<filename>`: Complete turn-by-turn replay data.
- `GET /api/tournaments`: V4 tournament benchmark runs and confidence intervals.
- `POST /api/interactive/move`: Evaluate position and choose AI move.
- `POST /api/interactive/validate`: Check legality of human move and score points.
- `POST /api/compare/position`: Run position evaluation across multiple engines side-by-side.
