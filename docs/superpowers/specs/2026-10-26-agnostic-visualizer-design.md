# Engine-Agnostic Alphable Visualizer Design Spec

**Date**: 2026-10-26  
**Status**: Approved (Brainstorming Phase Complete)  
**Target Path**: `visualizer/` (Top-level repository directory)

---

## 1. Executive Summary & Feasibility

### Is it possible and is it a good idea?
**Yes, entirely feasible and strongly recommended.**
Scrabble domain rules (15×15 grid, letter point values, bonus squares, CSW24/NWL23 lexicons, coordinates, and turn progression) are identical across engine generations. The only divergence is the move generator and equity valuation:
- **Alphable V3**: Python/Cython GADDAG move generator + Macondo ResNet / SmolLM2 Transformer candidate ranker + heuristic leaves.
- **Alphable V4**: Native C MAGPIE engine (`libmagpie.so`, 0.72ms move generation) + Bayesian opponent rack inference (CRN) + BAMS 2-ply search + ResNet-18 Cross-Attention value network.

By extracting the visualizer to a standalone top-level `visualizer/` folder, we:
1. Decouple visualization from the algorithmic engines, preventing code duplication or version drift.
2. Provide a single interface to compare V4 (the new champion) and V3 (the baseline) side-by-side on any game or board position.
3. Enable live interactive play against either engine, Base MAGPIE, or Greedy bots.
4. Support unified replay of historical V3 game logs and V4 tournament runs.

---

## 2. System Architecture

```
Alphable/
├── visualizer/                         # Standalone engine-agnostic visualizer
│   ├── run.sh                          # Universal launcher (checks build, starts server, opens browser)
│   ├── requirements.txt                # Flask, Flask-CORS
│   ├── backend/                        # Python API server
│   │   ├── app.py                      # Flask routes and static asset serving
│   │   ├── adapters/                   # Pluggable engine adapters
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # Abstract BaseEngineAdapter
│   │   │   ├── v4_adapter.py           # Alphable V4 BAMS / MAGPIE adapter
│   │   │   ├── v3_adapter.py           # Alphable V3 Macondo / Transformer adapter
│   │   │   └── baseline_adapter.py     # Base MAGPIE & Greedy bots
│   │   └── services/                   # Business logic services
│   │       ├── __init__.py
│   │       ├── replay_service.py       # Discovers and parses V3 JSONs and V4 tournament runs
│   │       └── dictionary_service.py   # Word validation and definitions
│   └── frontend/                       # Modern React + TypeScript UI
│       ├── package.json
│       ├── tsconfig.json
│       ├── public/
│       └── src/
│           ├── index.tsx & index.css   # Studio typography, dark theme tokens
│           ├── types.ts                # TypeScript domain models
│           ├── components/
│           │   ├── Board.tsx           # 15x15 Scrabble board with premium highlights & animations
│           │   ├── TileRack.tsx        # Interactive player tile rack (drag/click placement)
│           │   ├── EngineSelector.tsx  # Dynamic switch between V4, V3, MAGPIE, Greedy
│           │   ├── CandidateTable.tsx  # Live move candidate ranker & equity breakdown
│           │   ├── GameReplayView.tsx  # Scrubbing replay with score graph & turn log
│           │   ├── PositionAnalyzer.tsx# Side-by-side V3 vs V4 position evaluator
│           │   └── PlayerHUD.tsx       # Live scorecards, score deltas, and bingos
│           └── App.tsx                 # Studio navigation tabs (Play, Replay, Compare)
```

---

## 3. Backend Adapter Specification (`backend/adapters/`)

All engine interactions are abstracted through `BaseEngineAdapter`:

```python
class BaseEngineAdapter(ABC):
    @abstractmethod
    def get_id(self) -> str:
        """Unique identifier, e.g. 'v4' or 'v3'."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Human-readable name, e.g. 'Alphable V4 (BAMS + MAGPIE)'."""
        pass

    @abstractmethod
    def list_available_models(self) -> List[Dict[str, Any]]:
        """Returns registered presets/checkpoints with sizes and status."""
        pass

    @abstractmethod
    def select_move(
        self,
        board: List[List[Optional[str]]],
        rack: List[str],
        score_diff: int = 0,
        bag_remaining: int = 100,
        model_name: Optional[str] = None,
        lexicon: str = "CSW24",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Computes AI move and returns:
        - action: 'PLAY' | 'PASS' | 'EXCHANGE'
        - move: {word, row, col, direction}
        - points: int
        - equity: float
        - candidates: List[CandidateMove]
        """
        pass

    @abstractmethod
    def validate_move(
        self,
        board: List[List[Optional[str]]],
        rack: List[str],
        move: Dict[str, Any],
        lexicon: str = "CSW24"
    ) -> Dict[str, Any]:
        """Validates move legality, scores points, and computes remaining rack."""
        pass
```

### V4 Adapter (`v4_adapter.py`)
- Direct integration with `alphable_v4.engine.magpie_bindings.MagpieEngine` and `alphable_v4.search.bams.BAMSSearch`.
- Supports all V4 presets (`latest`, `5-frontiers`, `v4-baseline`, `rl-gen1`, `scaled-champion`).
- Candidate beam inspection returns BAMS score, Huber equity, and leave values.

### V3 Adapter (`v3_adapter.py`)
- Lazy loads `Alphable_V3/src/alphable` with Macondo ResNet or SmolLM2 Transformer.
- Preserves existing V3 self-play evaluation semantics and temperature sampling.

### Baseline Adapter (`baseline_adapter.py`)
- Provides pure Base MAGPIE (KLV static equity) and Greedy bot policies.

---

## 4. Frontend Studio Features & Aesthetics

### Visual Identity
- **Studio Theme**: Modern slate-dark palette (`#0f172a`, `#1e293b`, `#334155`), glowing sapphire and amber accents.
- **Board Design**: Clear 15×15 grid with distinct, elegant premium tiles:
  - Triple Word (TW): Warm Crimson (`#dc2626`)
  - Double Word (DW): Rose (`#f43f5e`)
  - Triple Letter (TL): Deep Azure (`#2563eb`)
  - Double Letter (DL): Sky Blue (`#0284c7`)
  - Center Star: Burnished Gold (`#d97706`)
- **Tiles**: Ivory wooden aesthetic with distinct subscript point numbers for Scrabble tournament authenticity.

### Three Primary Modes (Tabs)
1. **Interactive Studio (`/play`)**:
   - Play directly against V4, V3, Base MAGPIE, or Greedy bot.
   - Click/drag tile placement with live point calculation and legality indicator.
   - Real-time "Ask AI for Hint" and "Show Candidate Evaluations" drawer.
2. **Replay & Tournament Explorer (`/replays`)**:
   - Lists games from `Alphable_V3/data/` (vs_greedy, vs_random, results) AND `Alphable_V4/data/tournaments/`.
   - Scrubbing timeline, autoplay controls (0.5×, 1×, 2×, 5×), turn jumping.
   - Interactive score swing chart tracking cumulative score differential turn by turn.
3. **Position & Model Comparison (`/compare`)**:
   - Set up custom board positions and racks.
   - Run V4 (BAMS) vs V3 (ResNet) vs Base MAGPIE side-by-side on the exact same position, displaying move choices, latency, and evaluated equity.

---

## 5. Launcher & Portability (`visualizer/run.sh`)
- Executable shell script:
  - Verifies workspace `venv`.
  - Serves pre-built React bundle directly from Flask at `http://localhost:5000` (single process, zero Node runtime needed for users).
  - Flags:
    - `--dev`: Starts React dev server on port 3000 alongside Flask on port 5000 for hot-reloading.
    - `--build`: Rebuilds the React frontend bundle.
    - `--port <p>`: Custom port selection.
    - `--no-browser`: Headless mode for remote servers.
