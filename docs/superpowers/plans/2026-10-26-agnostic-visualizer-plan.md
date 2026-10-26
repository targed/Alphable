# Engine-Agnostic Alphable Visualizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone, engine-agnostic Scrabble visualizer and studio in `visualizer/` that supports both Alphable V4 (BAMS + MAGPIE) and Alphable V3 (Macondo + Transformer), providing interactive play, historical game replays, and side-by-side position analysis.

**Architecture:** A lightweight Python/Flask backend with a pluggable `EngineAdapter` architecture (`V4Adapter`, `V3Adapter`, `BaselineAdapter`) coupled to a broadcast-grade React + TypeScript single-page studio application. The Flask server serves the compiled React production bundle directly for zero-dependency execution.

**Tech Stack:** Python 3.10+, Flask, Flask-CORS, PyTorch, C ctypes (MAGPIE), React 18, TypeScript, CSS3 modern variables.

**Spec:** [`docs/superpowers/specs/2026-10-26-agnostic-visualizer-design.md`](file:///home/targed/Documents/Git/Alphable/docs/superpowers/specs/2026-10-26-agnostic-visualizer-design.md)

## Global Constraints

- Standalone top-level directory: all visualizer code must reside in `visualizer/`.
- No modification of core engine algorithms in `Alphable_V4/` or `Alphable_V3/`.
- Fully decoupled: if V3 or V4 is missing or partially configured, the visualizer must degrade gracefully and run with the available engine(s).
- Production runtime requires zero Node.js: pre-built React assets are served directly by Flask via `./visualizer/run.sh`.
- Test verification: every task includes test coverage verifying functionality before proceeding.

---

### Task 1: Project Scaffolding & Virtual Environment Dependencies

**Files:**
- Create: `visualizer/requirements.txt`
- Create: `visualizer/backend/__init__.py`
- Create: `visualizer/backend/adapters/__init__.py`
- Create: `visualizer/backend/services/__init__.py`
- Test: `visualizer/tests/test_scaffolding.py`

**Interfaces:**
- Consumes: Workspace Python environment.
- Produces: Base directory hierarchy and dependency specification for `visualizer/`.

- [ ] **Step 1: Write the failing test**

Create `visualizer/tests/test_scaffolding.py`:
```python
import os
from pathlib import Path

def test_visualizer_directory_structure():
    vis_dir = Path(__file__).resolve().parent.parent
    assert (vis_dir / "requirements.txt").exists()
    assert (vis_dir / "backend").is_dir()
    assert (vis_dir / "backend" / "adapters").is_dir()
    assert (vis_dir / "backend" / "services").is_dir()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest visualizer/tests/test_scaffolding.py -v`  
Expected: FAIL (No such file or directory)

- [ ] **Step 3: Implement minimal code**

1. Create `visualizer/requirements.txt`:
```text
flask>=3.0.0
flask-cors>=4.0.0
```
2. Create `__init__.py` files in `visualizer/backend/`, `visualizer/backend/adapters/`, and `visualizer/backend/services/`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest visualizer/tests/test_scaffolding.py -v`  
Expected: PASS

---

### Task 2: Base Engine Adapter & Alphable V4 Adapter

**Files:**
- Create: `visualizer/backend/adapters/base.py`
- Create: `visualizer/backend/adapters/v4_adapter.py`
- Create: `visualizer/backend/adapters/baseline_adapter.py`
- Test: `visualizer/tests/test_v4_adapter.py`

**Interfaces:**
- Consumes: `alphable_v4.engine.magpie_bindings`, `alphable_v4.engine.game_state`, `alphable_v4.search.bams`.
- Produces: `BaseEngineAdapter`, `V4Adapter`, and `BaselineAdapter`.

- [ ] **Step 1: Write the failing test**

Create `visualizer/tests/test_v4_adapter.py`:
```python
from visualizer.backend.adapters.v4_adapter import V4Adapter
from visualizer.backend.adapters.baseline_adapter import BaselineAdapter

def test_v4_adapter_initialization_and_metadata():
    adapter = V4Adapter()
    assert adapter.get_id() == "v4"
    assert "Alphable V4" in adapter.get_name()
    models = adapter.list_available_models()
    assert len(models) > 0
    assert any(m["id"] == "latest" for m in models)

def test_v4_adapter_move_selection_and_validation():
    adapter = V4Adapter()
    board = [[None for _ in range(15)] for _ in range(15)]
    rack = ["A", "Q", "R", "T", "U", "Y", "Z"]
    res = adapter.select_move(board, rack, model_name="v4-baseline")
    assert res["action"] in ("PLAY", "PASS", "EXCHANGE")
    assert "candidates" in res
    assert len(res["candidates"]) > 0

    # Validate first candidate move
    top_move = res["candidates"][0]
    val = adapter.validate_move(board, rack, top_move)
    assert val["valid"] is True
    assert val["points"] > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest visualizer/tests/test_v4_adapter.py -v`  
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement minimal code**

1. Create `visualizer/backend/adapters/base.py` with `BaseEngineAdapter` abstract class.
2. Create `visualizer/backend/adapters/v4_adapter.py`:
   - Wraps `MagpieEngine` and `BAMSSearch` using relative resolution to `Alphable_V4`.
   - Exposes `select_move` and `validate_move`.
3. Create `visualizer/backend/adapters/baseline_adapter.py`:
   - Exposes Base MAGPIE and Score Greedy bots.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest visualizer/tests/test_v4_adapter.py -v`  
Expected: PASS

---

### Task 3: Alphable V3 Engine Adapter

**Files:**
- Create: `visualizer/backend/adapters/v3_adapter.py`
- Test: `visualizer/tests/test_v3_adapter.py`

**Interfaces:**
- Consumes: `Alphable_V3/src/alphable.core.inference`, `Alphable_V3/src/alphable.core.simulator`.
- Produces: `V3Adapter` class conforming to `BaseEngineAdapter`.

- [ ] **Step 1: Write the failing test**

Create `visualizer/tests/test_v3_adapter.py`:
```python
from visualizer.backend.adapters.v3_adapter import V3Adapter

def test_v3_adapter_metadata_and_capabilities():
    adapter = V3Adapter()
    assert adapter.get_id() == "v3"
    assert "Alphable V3" in adapter.get_name()
    models = adapter.list_available_models()
    assert isinstance(models, list)

def test_v3_adapter_move_generation():
    adapter = V3Adapter()
    board = [[None for _ in range(15)] for _ in range(15)]
    rack = ["C", "A", "T", "S", "E", "R", "D"]
    res = adapter.select_move(board, rack)
    assert res["action"] in ("PLAY", "PASS", "EXCHANGE")
    if res["action"] == "PLAY":
        assert "word" in res["move"]
        assert res["points"] > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest visualizer/tests/test_v3_adapter.py -v`  
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement minimal code**

Create `visualizer/backend/adapters/v3_adapter.py`:
- Add `Alphable_V3/src` dynamically to `sys.path`.
- Lazy-load GADDAG dictionary and Macondo checkpoints from `Alphable_V3/models/`.
- Translate V3 dictionary move records into standard visualizer format `{word, row, col, direction}`.
- If V3 dependencies are missing, provide graceful degraded status.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest visualizer/tests/test_v3_adapter.py -v`  
Expected: PASS

---

### Task 4: Replay & Tournament Discovery Service

**Files:**
- Create: `visualizer/backend/services/replay_service.py`
- Test: `visualizer/tests/test_replay_service.py`

**Interfaces:**
- Consumes: Game JSON files in `Alphable_V3/data/` and tournament JSONs in `Alphable_V4/data/tournaments/`.
- Produces: Unified replay list and turn-by-turn game state parser.

- [ ] **Step 1: Write the failing test**

Create `visualizer/tests/test_replay_service.py`:
```python
from visualizer.backend.services.replay_service import ReplayService

def test_replay_discovery():
    service = ReplayService()
    games = service.list_all_games()
    assert isinstance(games, list)
    assert len(games) > 0
    # Must contain category, id, timestamp, player_names, scores
    g0 = games[0]
    assert "id" in g0
    assert "category" in g0
    assert "final_score" in g0

def test_load_single_game():
    service = ReplayService()
    games = service.list_all_games()
    first_game = games[0]
    game_data = service.get_game_details(first_game["category"], first_game["filename"])
    assert game_data is not None
    assert "turns" in game_data or "results" in game_data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest visualizer/tests/test_replay_service.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement minimal code**

Create `visualizer/backend/services/replay_service.py`:
- Scans `Alphable_V3/data/vs_greedy`, `vs_random`, `matches`, `results`.
- Scans `Alphable_V4/data/tournaments/` and parses tournament run histories and individual game replays.
- Normalizes turn structure: turn index, player ID, action type, word, position, score, cumulative score, racks, and board representation.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest visualizer/tests/test_replay_service.py -v`  
Expected: PASS

---

### Task 5: Flask Backend API & Endpoints

**Files:**
- Create: `visualizer/backend/app.py`
- Test: `visualizer/tests/test_api_endpoints.py`

**Interfaces:**
- Consumes: `V4Adapter`, `V3Adapter`, `BaselineAdapter`, `ReplayService`.
- Produces: REST API endpoints:
  - `GET /api/health`
  - `GET /api/engines`
  - `GET /api/models?engine=<engine_id>`
  - `GET /api/games`
  - `GET /api/games/<category>/<filename>`
  - `POST /api/interactive/move`
  - `POST /api/interactive/validate`
  - `POST /api/compare/position`
  - `GET /` and `/<path:path>` static asset fallback.

- [ ] **Step 1: Write the failing test**

Create `visualizer/tests/test_api_endpoints.py`:
```python
import json
import pytest
from visualizer.backend.app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_api_health(client):
    res = client.get('/api/health')
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert "v4" in data["available_engines"]

def test_api_interactive_move(client):
    payload = {
        "engine": "v4",
        "model": "v4-baseline",
        "board": [[None for _ in range(15)] for _ in range(15)],
        "rack": ["A", "Q", "R", "T", "U", "Y", "Z"]
    }
    res = client.post('/api/interactive/move', json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert "action" in data
    assert "candidates" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest visualizer/tests/test_api_endpoints.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement minimal code**

Implement `visualizer/backend/app.py`:
- Set up Flask app and CORS.
- Wire in adapters: `v4`, `v3`, `magpie`, `greedy`.
- Wire in replay service.
- Implement `/api/compare/position` which runs position evaluation across requested engines side-by-side.
- Add production static file route serving `visualizer/frontend/build`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest visualizer/tests/test_api_endpoints.py -v`  
Expected: PASS

---

### Task 6: Modern Frontend Studio Scaffolding & Design System

**Files:**
- Create: `visualizer/frontend/package.json`
- Create: `visualizer/frontend/tsconfig.json`
- Create: `visualizer/frontend/public/index.html`
- Create: `visualizer/frontend/src/types.ts`
- Create: `visualizer/frontend/src/index.css`
- Create: `visualizer/frontend/src/index.tsx`

**Interfaces:**
- Consumes: Node.js and TypeScript compiler.
- Produces: CSS design system tokens (slate dark mode, premium board colors, wooden tiles) and TypeScript domain types.

- [ ] **Step 1: Write types and design tokens**

Create `visualizer/frontend/src/types.ts`:
- Define `BoardState`, `Move`, `CandidateMove`, `GameReplay`, `Turn`, `EngineMetadata`, `ModelInfo`.
Create `visualizer/frontend/src/index.css`:
- Modern CSS variables: `--bg-main`, `--bg-card`, `--accent-blue`, `--accent-gold`, `--tw-color`, `--dw-color`, `--tl-color`, `--dl-color`, `--tile-wood`.
- Inter / Outfit clean typography and fluid layouts.

- [ ] **Step 2: Build verification**

Run `npm install` inside `visualizer/frontend` to verify package resolution.

---

### Task 7: Interactive Board, Rack & Evaluation Components

**Files:**
- Create: `visualizer/frontend/src/components/Board.tsx`
- Create: `visualizer/frontend/src/components/TileRack.tsx`
- Create: `visualizer/frontend/src/components/PlayerHUD.tsx`
- Create: `visualizer/frontend/src/components/CandidateTable.tsx`
- Create: `visualizer/frontend/src/components/EngineSelector.tsx`

**Interfaces:**
- Consumes: `BoardState`, `CandidateMove`, engine API endpoints.
- Produces: Reusable UI widgets for Scrabble board display, tile placement, and move evaluation.

- [ ] **Step 1: Implement Board component**
  - Render 15×15 grid with distinct coordinates (A-O columns, 1-15 rows).
  - Premium square badges: TW (red), DW (pink), TL (blue), DL (light blue), Star (gold).
  - Ivory/wooden tile styling with point subscript numbers.
  - Interactive cell click / drag target for human plays.

- [ ] **Step 2: Implement TileRack & HUD**
  - Render 7-tile rack with tile selection.
  - Player scores, score deltas, bingo badges, and turn indicators.

- [ ] **Step 3: Implement CandidateTable & EngineSelector**
  - Dropdown to choose between Alphable V4, Alphable V3, Base MAGPIE, and Greedy bot.
  - Table showing Top-K candidate moves, word, points, leave, BAMS / equity score, and win probability.

---

### Task 8: Replay Explorer, Position Analyzer & Main Studio App

**Files:**
- Create: `visualizer/frontend/src/components/GameReplayView.tsx`
- Create: `visualizer/frontend/src/components/PositionAnalyzer.tsx`
- Create: `visualizer/frontend/src/App.tsx`

**Interfaces:**
- Consumes: Board, CandidateTable, ReplayService API.
- Produces: 3 studio tabs:
  1. **Interactive Studio**: Live play against AI with hints and move validation.
  2. **Game Replay**: Scrubbing timeline, autoplay speeds, and turn list.
  3. **Position Analyzer**: Side-by-side V4 vs V3 position evaluation.

- [ ] **Step 1: Implement GameReplayView**
  - Game browser list with search/filter.
  - Scrubbing timeline slider with keyboard shortcuts (ArrowLeft, ArrowRight, Space).
  - Score differential line chart across turns.

- [ ] **Step 2: Implement PositionAnalyzer**
  - Board editor + rack input.
  - Button to "Compare Engines", displaying V4 BAMS choice vs V3 Neural choice vs Base MAGPIE side-by-side.

- [ ] **Step 3: Assemble App.tsx**
  - Studio top navigation bar with engine health indicator and tab switching.

---

### Task 9: Production Bundle Build & Universal Launcher

**Files:**
- Create: `visualizer/run.sh`
- Build: `visualizer/frontend/build/`
- Create: `visualizer/README.md`

**Interfaces:**
- Consumes: Flask backend and compiled frontend.
- Produces: Production bundle and executable launcher script `./visualizer/run.sh`.

- [ ] **Step 1: Compile Frontend Bundle**

Run: `cd visualizer/frontend && npm run build`  
Expected: Generates static bundle in `visualizer/frontend/build/`

- [ ] **Step 2: Create Universal Launcher `visualizer/run.sh`**

Script handles:
- Detecting Python `venv`.
- Checking if `frontend/build` exists; builds if missing.
- Starting Flask on specified port (default: 5000).
- Launching default browser unless `--no-browser` passed.
- Supporting `--dev` mode for hot-reload development.

- [ ] **Step 3: Make executable**

Run: `chmod +x visualizer/run.sh`

---

### Task 10: End-to-End Verification & Verification Gate

**Files:**
- Test: `visualizer/tests/test_e2e_visualizer.py`

- [ ] **Step 1: Run comprehensive backend test suite**

Run: `pytest visualizer/tests/ -v`  
Expected: 100% pass across scaffolding, V4 adapter, V3 adapter, replay service, and API endpoints.

- [ ] **Step 2: Test live server execution**

Start visualizer in test mode, query `http://127.0.0.1:5000/api/health` and verify static `index.html` loads.

- [ ] **Step 3: Document usage in `visualizer/README.md`**

Complete guide on starting the visualizer, using each mode, and troubleshooting.
