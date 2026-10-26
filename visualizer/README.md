# Alphable Visualizer Studio

Alphable Visualizer Studio is an engine-agnostic Scrabble research laboratory and interactive visualizer. It provides a unified workbench for playing against, analyzing, comparing, and benchmarking Scrabble artificial intelligence systems.

The studio decouples game analysis, tournament verification, and board visualization from specific engine implementations. It communicates through an adapter layer with:
- **Alphable V4**: BAMS (Bayesian Adversarial Monte Carlo Search) with native C MAGPIE move generation, neural value networks, 2-ply nested rollouts, and asymmetric volatility control.
- **Alphable V3**: ResNet-18 board valuation and transformer leave rankers over Macondo GADDAG move generation.
- **Base MAGPIE**: Classical C engine utilizing KLV static equity.
- **Score Greedy**: Baseline immediate score maximizer.

---

## Table of Contents
1. [Quickstart](#quickstart)
2. [Core Features](#core-features)
   - [Match Arena](#1-match-arena)
   - [Lexicon and Word Definition Inspector](#2-lexicon-and-word-definition-inspector)
   - [Behind-the-Scenes Engine Thoughts](#3-behind-the-scenes-engine-thoughts)
   - [Tournament Analytics and Significance](#4-tournament-analytics-and-significance)
   - [Game Replays](#5-game-replays)
   - [Position Lab](#6-position-lab)
3. [User Workflows and How-To Guides](#user-workflows-and-how-to-guides)
4. [Architecture and Backend API](#architecture-and-backend-api)
5. [Engineering History and Design Rationale](#engineering-history-and-design-rationale)
6. [Testing and Verification](#testing-and-verification)

---

## Quickstart

### Prerequisites
- Linux OS with Python 3.10+ (recommended: project virtual environment in `venv/`)
- Node.js 18+ and npm (only needed if building or developing the frontend)

### Launching the Studio
From the repository root:
```bash
./start_visualizer.sh
```

Or from the `visualizer/` directory:
```bash
cd visualizer
./run.sh
```

By default, the backend server starts on `http://localhost:5000`, serves the compiled React single-page application directly, and launches your default web browser.

### Command-Line Options
The launcher script supports several flags:
- `./visualizer/run.sh --dev`: Runs the React development server on port 3000 alongside the Flask backend on port 5000 with hot reloading enabled.
- `./visualizer/run.sh --build`: Recompiles the React production bundle before starting the server.
- `./visualizer/run.sh --port 8080`: Binds the Flask server to a custom port.
- `./visualizer/run.sh --host 127.0.0.1`: Binds to a specific network interface.
- `./visualizer/run.sh --no-browser`: Suppresses automatic browser launch (ideal for headless servers or remote SSH sessions).

---

## Core Features

### 1. Match Arena
The Match Arena supports live Scrabble games under official tournament rules:
- **Flexible Matchups**: Play Human vs AI, AI vs AI bot battles, or Human vs Human. Both players can be assigned different engines (Alphable V4, Alphable V3, Base MAGPIE, Greedy) or model checkpoints (`latest`, `5-frontiers`, `v4-baseline`, `rl-gen1`).
- **Interactive Board**: 15x15 standard grid with official premium multipliers: Triple Word (TW), Double Word (DW), Triple Letter (TL), Double Letter (DL), and center start star.
- **Continuous Delay Slider**: Replaces fixed step delays with a continuous slider from 0.0 seconds (Real-time) to 3.0 seconds in 0.1-second steps. At 0.0s, the engine executes turns at native calculation speed without artificial pacing.
- **Tile Bag Conservation**: Preserves an exact 100-tile set across player racks, the board, and the bag throughout the entire match.
- **Bag Inspector Modal**: Displays real-time breakdown of remaining tiles, grouped by vowels, consonants, and power tiles (J, Q, X, Z, blanks), along with current draw odds.
- **Duplicate Position Swap**: Pauses the current match and queries both selected engines on the exact board state and rack simultaneously, presenting side-by-side candidate selections to evaluate how each engine handles the identical situation.
- **Timeline and Safe Rewind**: Displays the full move log. Clicking any turn's dedicated Rewind button restores that turn's board, rack, score, and bag state.

### 2. Lexicon and Word Definition Inspector
The studio features a built-in dictionary verification and definition lookup system:
- **Supported Lexicons**: Full validation against official **CSW24** (Collins Scrabble Words 2024, 280,887 words) and **NWL23** (North American Tournament Word List 2023, 196,601 words).
- **Definition Display**: Shows word validity badges (`VALID PLAY` vs `INVALID / PHONEY`), letter length, base tile score sum, part of speech (noun, verb, adjective, etc.), and official definition text.
- **Morphological Stemming**: Automatically derives inflections (plurals ending in `-S` or `-IES`, verb conjugations in `-ED` or `-ING`) when looking up inflected tournament forms.
- **Curated Tournament Glosses**: Built-in glosses for Collins-exclusive and historical Scrabble vocabulary (e.g., `SAULIES`, `CATERANS`, `OUGIYAS`).
- **Auto-Define Mode**: When enabled via the header toggle, any word played on the board (by human or AI) is automatically parsed and defined without requiring manual user input.
- **Non-Destructive Word Inspection**: Clicking any word in the Candidate Move Table, the Game Timeline, or the Engine Stats table instantly opens its definition in the inspector without altering the active match state.
- **Global Lookup Modal**: A top-navigation "Word Lookup" button opens a standalone dictionary search modal from any screen in the application.

### 3. Behind-the-Scenes Engine Thoughts
Located in the right panel alongside candidate evaluations, the **Engine Thoughts** view surfaces internal search telemetry:
- **Search Architecture**: Identifies the decision path executed by the engine, such as BAMS Monte Carlo Rollout (2-Ply Nested), Deterministic Endgame Solver, Pre-Endgame Parity Adjuster, or Classical KLV Static Equity.
- **Latency Telemetry**: Millisecond-precision search latency, color-coded by computation budget.
- **Game Phase Tracking**: Identifies the current strategic phase: Opening/Midgame (bag > 5), Pre-Endgame Parity (1 <= bag <= 5), or Exact Deterministic Endgame (unseen tiles <= 7).
- **BAMS Search Score vs Static Equity**: Shows the differential between the final adversarial Monte Carlo value and the raw static leave equity, highlighting strategic trade-offs where BAMS sacrifices immediate points for positional advantage or opponent containment.
- **Asymmetric Volatility Indicator**: Reports whether volatility control is biasing the engine toward board closure (when leading) or openness (when trailing).
- **Bayesian Opponent Belief Racks**: Renders the tile racks sampled from the Bayesian Belief Network during Monte Carlo simulation, illustrating the opponent distributions the engine anticipated.
- **Deep Evaluation Table**: Detailed breakdown of top moves evaluated during search, reporting immediate score, mean opponent reply threat, 2-ply net exchange value, value network future board control, and composite BAMS score.

### 4. Tournament Analytics and Significance
Clicking any tournament record in the Replay & Tournaments tab opens a comprehensive statistical analytics dashboard:
- **Hero Matchup Summary**: Head-to-head comparison of Champion vs Opponent wins, win percentages, mean scores per game, and bingo frequencies.
- **Win Rate Gauge with 95% Confidence Interval**: Visual horizontal meter featuring a 50.0% parity indicator and a shaded 95% confidence band `[ci_lower, ci_upper]`.
- **Hypothesis Testing Card**: Displays the paired Student t-statistic, two-tailed p-value ($p < 0.0001$), formal hypothesis notation ($H_0: \Delta=0 \text{ vs } H_1: \Delta \neq 0$), and clear statistical significance verdicts.
- **Score Margin Histogram**: Frequency distribution chart displaying duplicate pair net spread buckets (from `< -60` to `> +60` points).
- **Duplicate Pair Match Browser**: Searchable, paginated table detailing all duplicate matches: pair index, random seed, Game A/B point totals for each engine, net spread, and match outcome.

### 5. Game Replays
Browse and inspect historical games from Alphable V3 matches and Alphable V4 benchmark logs:
- Complete playback transport controls (First, Previous, Play/Pause, Next, Last).
- Adjustable playback speed from 0.5x to 4.0x.
- Interactive turn scrub slider.
- Step-by-step board reconstruction and player rack history.

### 6. Position Lab
A position editor and cross-engine evaluator:
- Click squares on the 15x15 board to place or clear custom letters.
- Enter custom 7-tile racks.
- Load pre-configured tactical positions: opening scenarios, high-scoring hook opportunities, power-tile racks, or bingo leaves.
- Click **Compare Engines** to dispatch parallel queries across Alphable V4, Alphable V3, Base MAGPIE, and Score Greedy, viewing their recommended moves and equity rankings side-by-side.

---

## User Workflows and How-To Guides

### How to Run an AI vs AI Match with Real-Time Auto-Play
1. Open the studio and select the **Match Arena** tab.
2. In the top controls bar, set **P1** to your preferred engine (e.g., `Alphable V4 (BAMS)`) and **P2** to an opponent (e.g., `Base MAGPIE`).
3. Drag the **Delay** slider all the way to the left until it displays `Real-time`.
4. Click **Auto-play**. The engines will play turns consecutively as fast as moves are computed.
5. Click **Pause** at any point to halt playback and inspect the board.

### How to Inspect Word Validity and Definitions
There are three ways to look up words:
- **Automatic Inspection**: In the right panel, select the **Word Inspector** tab and ensure **Auto-define** is checked. Every word played on the board will automatically load with its definition and lexicon status.
- **Click to Inspect**: Click on any word in the Candidate Moves table or in the Game Timeline. The studio will open the Word Inspector and look up the word immediately without disrupting the game.
- **Manual Search**: Click **Word Lookup** in the top navigation bar. Enter any word and press Enter to query both CSW24 and NWL23 lexicons.

### How to Analyze What the Engine Was Thinking
1. After stepping an AI turn or pausing auto-play, look at the right-hand panel.
2. Click the **Engine Thoughts** tab.
3. Review the latency, evaluated candidate count, game phase, and BAMS score delta.
4. Check the **Bayesian Opponent Rack Samples** section to see what tiles the belief network assumed the opponent was holding.
5. Consult the **Deep Search Evaluation Breakdown** table to understand why the winning move was chosen over alternative high-scoring plays.

### How to Compare Engine Decisions on the Same Turn
1. During any game in the Match Arena, click **Duplicate Swap**.
2. A modal will open displaying the current board state and active rack.
3. Both engines will evaluate the position concurrently.
4. Review the points, leaves, and candidate rankings side-by-side.
5. Click **Apply Play** under either engine's proposal to branch the live game using that engine's decision.

### How to Inspect Tournament Statistical Significance
1. Navigate to the **Replay & Tournaments** tab.
2. In the left sidebar, click the **Tournaments** sub-tab.
3. Click on any tournament card (e.g., `3000g-duplicate-championship` or `10000g-duplicate`).
4. The **Tournament Analytics** dashboard will open, showing the 95% confidence interval gauge, t-statistic, p-value verdict, score spread histogram, and duplicate match tables.

---

## Architecture and Backend API

### Directory Structure
```
visualizer/
├── run.sh                          # Universal launcher script
├── requirements.txt                # Python dependencies (Flask, Flask-CORS)
├── backend/
│   ├── app.py                      # Flask REST API server and static asset host
│   ├── adapters/
│   │   ├── base.py                 # Abstract BaseEngineAdapter and rack sanitizer
│   │   ├── v4_adapter.py           # Alphable V4 BAMS and C MAGPIE adapter
│   │   ├── v3_adapter.py           # Alphable V3 Macondo / ResNet adapter
│   │   └── baseline_adapter.py     # Base MAGPIE (KLV) and Greedy adapter
│   └── services/
│       ├── dictionary_service.py   # CSW24/NWL23 lexicon and definition manager
│       └── replay_service.py       # Replay and tournament indexing service
├── frontend/
│   ├── package.json
│   ├── build/                      # Compiled production assets served by Flask
│   └── src/
│       ├── types.ts                # TypeScript domain interfaces
│       ├── App.tsx                 # Studio container, tabs, and state orchestrator
│       └── components/
│           ├── Board.tsx           # 15x15 interactive Scrabble board
│           ├── TileRack.tsx        # 7-tile player rack
│           ├── PlayerHUD.tsx       # Scores, active indicator, tile bag tracker
│           ├── ArenaControls.tsx   # Match setup, speed slider, action buttons
│           ├── CandidateTable.tsx  # Candidate moves evaluation table
│           ├── EngineStatsView.tsx # Engine thoughts, Bayesian racks, search telemetry
│           ├── WordInspector.tsx   # Word definition and lexicon validity component
│           ├── TournamentModal.tsx # Tournament statistics, p-values, histogram dashboard
│           ├── DuplicateModal.tsx  # Side-by-side duplicate position evaluator
│           ├── BagModal.tsx        # Remaining tile bag distribution inspector
│           ├── GameReplayView.tsx  # Game logs and tournament series browser
│           └── PositionAnalyzer.tsx# Custom board and position lab
└── tests/
    ├── test_api_endpoints.py       # API route, dictionary, and move tests
    ├── test_e2e_visualizer.py      # End-to-end engine generation tests
    ├── test_replay_service.py      # Replay service indexing tests
    ├── test_scaffolding.py         # Directory and bundle structure verification
    ├── test_v3_adapter.py          # V3 adapter compliance tests
    └── test_v4_adapter.py          # V4 adapter, bag conservation, and error recovery tests
```

### Key REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Returns server health, timestamp, and registered engines. |
| `GET` | `/api/engines` | Returns list of available engine adapters and capabilities. |
| `GET` | `/api/models?engine=<id>` | Lists checkpoints and presets registered for the specified engine. |
| `GET` | `/api/dictionary/lookup?word=<w>&lexicon=<l>` | Checks word validity in CSW24/NWL23 and returns definitions and points. |
| `GET` | `/api/games` | Returns list of discovered replay logs across V3 and V4. |
| `GET` | `/api/games/<category>/<filename>` | Returns full turn-by-turn replay data for a game. |
| `GET` | `/api/tournaments` | Returns tournament benchmark runs, p-values, and win rates. |
| `POST` | `/api/interactive/move` | Evaluates a board and rack state, returning the chosen move and search telemetry. |
| `POST` | `/api/interactive/validate` | Checks legality and point yield of a candidate play. |
| `POST` | `/api/compare/position` | Dispatches a position to multiple engines concurrently for side-by-side comparison. |

---

## Engineering History and Design Rationale

### 1. Decoupling from V3 into a Standalone Architecture
- **Problem**: The original visualizer was embedded inside `Alphable_V3/visualizer/`, tightly coupled to V3's internal file layout, Macondo GADDAG bindings, and model checkpoints. With the introduction of Alphable V4 (featuring native C MAGPIE and BAMS search), reimplementing a duplicate visualizer inside `Alphable_V4` would have fragmented code and prevented direct comparisons.
- **Solution**: Extracted the visualizer into a dedicated top-level `visualizer/` module utilizing the **Adapter Pattern** (`BaseEngineAdapter`). Engine-specific logic is encapsulated in isolated adapters (`v4_adapter.py`, `v3_adapter.py`, `baseline_adapter.py`). The frontend communicates strictly via unified JSON contracts, making it straightforward to plug in future engines.

### 2. Solving Tile Bag Duplication (MAGPIE Error 51)
- **Problem**: In early interactive testing, deals were generated by creating random 7-tile racks for Player 1 and Player 2 without deducting them from the remaining tile bag. Over 15 to 20 turns, MAGPIE's state reconstruction detected tile counts exceeding standard limits (e.g., 3 blanks or 14 E's), causing the C engine to abort with `(error 51): rack not available in the bag`.
- **Solution**: 
  1. Implemented strict 100-tile set conservation (`DEFAULT_BAG` distribution) starting from turn 1. Player 1 and Player 2 draw from the same bag, leaving exactly 86 tiles in reserve. Replenishing racks draws exclusively from the real bag pool.
  2. Implemented `sanitize_rack_for_board()` in `base.py` as defensive middleware: it checks the current board tile counts and replaces any tile in the player's rack that would exceed the physical 100-tile limit with an available letter before dispatching to the C engine.

### 3. Fixing the Infinite Autoplay Loop on Game Completion
- **Problem**: When a match reached its conclusion (bag empty and a player playing out their last tile, or consecutive passes), the auto-play loop in `App.tsx` continued attempting to step moves with an empty rack `[]`. In Flask, `if not board or not rack:` evaluated `not []` as `True`, returning HTTP 400 Bad Request and causing an infinite network loop.
- **Solution**:
  1. Updated backend route handling to `if board is None or rack is None:`, allowing empty racks to pass through.
  2. In `v4_adapter.py` and `baseline_adapter.py`, an empty rack immediately returns action `PASS` with `200 OK` and `metadata: {"game_over": True}`.
  3. Added game termination detection in `App.tsx`: halts auto-play immediately when two consecutive passes occur or when a player plays out with an empty bag, applying standard Scrabble penalty deductions to calculate final scores.

### 4. Fixing the Safe Rewind and Word Click Bug
- **Problem**: The Game Timeline table had an `onClick` handler attached to the entire `<tr>` element that rewound match state to that turn and truncated future moves. When users clicked on a played word to look up its definition, the click event bubbled to the row, causing the match to rewind and erasing the move history.
- **Solution**: Removed the row-level `onClick`. Added a dedicated **Rewind** button in its own column for intentional time-travel. Wrapped move words in an independent element with `stopPropagation()` that routes strictly to the Word Inspector without touching game state.

### 5. Continuous Speed Slider
- **Problem**: Fixed discrete delay buttons (`0.5s`, `1.0s`, `2.0s`) were too slow for automated bot tournaments and too coarse for high-throughput testing.
- **Solution**: Replaced the buttons with a continuous range slider spanning 0.0s to 3.0s. At 0.0s, the client yields a single animation frame (15ms) to render DOM updates before immediately requesting the next engine move, enabling rapid self-play execution.

### 6. Statistical Significance for Duplicate Tournaments
- **Problem**: Simple win-rate percentages in Scrabble can be misleading due to tile draw variance. Proving that an engine upgrade provides a genuine competitive edge over classical KLV static equity requires statistical significance testing on duplicate pair matches (where both engines play the exact same tiles from both sides).
- **Solution**: Built the `TournamentModal` analytics dashboard. It calculates and renders 95% confidence intervals, two-tailed paired Student t-tests, and net score spread histograms from tournament run data, providing rigorous verification of engine strength.

---

## Testing and Verification

All backend endpoints, engine adapters, and data pipelines are verified through an automated pytest suite.

### Running Backend Tests
From the repository root:
```bash
PYTHONPATH=. venv/bin/pytest visualizer/tests/ -v
```
All 21 visualizer unit and end-to-end tests should pass.

### Running Engine Tests
To verify Alphable V4 core engine compatibility:
```bash
PYTHONPATH=. venv/bin/pytest Alphable_V4/tests/ -v
```
All 59 core engine tests should pass.

### Building the Frontend
To compile the React frontend production bundle:
```bash
cd visualizer/frontend
npm run build
```
Build output is saved to `visualizer/frontend/build/` and served automatically by the Flask backend.
