# Alphable V3: Woogles Bot Operations & Live Runbook

This guide describes how to operate **Alphable V3** autonomously on [Woogles.io](https://woogles.io), Scrabble's premier competitive online tournament platform.

---

## 1. System Overview

Alphable interfaces with Woogles using an asynchronous Playwright browser automation adapter ([`src/alphable/platform/woogles/adapter.py`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/platform/woogles/adapter.py)) managed by [`OnlineGameRunner`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/platform/runner.py).

```
   ┌──────────────────────────────────────────────────────────────┐
   │                          Woogles.io                          │
   │               (Lobby, Live Board, Macondo API)               │
   └──────────────────────────────▲───────────────────────────────┘
                                  │ DOM Events & Playwright
   ┌──────────────────────────────┴───────────────────────────────┐
   │                 WooglesAdapter (adapter.py)                  │
   │   - Persistent Chrome profile (~/.alphable/woogles_profile)  │
   │   - Fast rack read, board OCR & keyboard input simulation    │
   │   - GCG export & post-game Macondo Analysis harvesting       │
   └──────────────────────────────▲───────────────────────────────┘
                                  │ Move Orders & Telemetry
   ┌──────────────────────────────┴───────────────────────────────┐
   │             OnlineGameRunner (runner.py)                     │
   │   - Multi-game series manager (1 to 100 games)               │
   │   - Turn timeout watchdog & crash isolation                  │
   │   - Win/Loss series summary aggregation                      │
   └──────────────────────────────▲───────────────────────────────┘
                                  │
                   Alphable Engine (search.py)
```

---

## 2. Prerequisites & First-Time Setup

### A. Environment & Playwright
Ensure you are using the repository virtual environment:
```bash
cd /home/targed/Documents/Git/Alphable/Alphable_V3
source ../venv/bin/activate
playwright install chromium
```

### B. Persistent Profile & One-Time Login
Alphable uses a dedicated browser profile directory at `~/.alphable/woogles_profile`. This stores your session cookies and authentication tokens so you do not need to log in repeatedly.

To establish your session for the first time:
1. Run a headed match or interactive takeover:
   ```bash
   python -m alphable.cli.main play woogles --takeover --games 1
   ```
2. When Chromium opens, log in to your Woogles account manually.
3. Once logged in, your session is saved in `~/.alphable/woogles_profile`. All subsequent headless or headed runs will automatically authenticate as your user.

---

## 3. Running Online Match Series Against HastyBot

### Standard Championship Match Series (Lookahead Mode)
To launch a 15-game series against `HastyBot` using the production champion ResNet model:

```bash
python -m alphable.cli.main play woogles \
  --bot HastyBot \
  --games 15 \
  --model models/alphable_v3_macondo_v2.pth \
  --dict resources/CSW24.txt \
  --mode lookahead \
  --top-k 5 --simulations 10
```

### Transformer Candidate Ranker Match Series
To run matches using the fine-tuned SmolLM2 Transformer Candidate Ranker:

```bash
python -m alphable.cli.main play woogles \
  --bot HastyBot \
  --games 5 \
  --mode transformer \
  --transformer-model models/transformer_ranker_v2 \
  --dict resources/CSW24.txt
```

### Zero-Delay Play (`--no-delay`)
By default, Alphable injects a natural thinking delay (`--delay-min 2.0 --delay-max 6.0`) to emulate human cadence. For automated testing or high-speed benchmark matches, disable the pacing delay completely:

```bash
python -m alphable.cli.main play woogles \
  --bot HastyBot \
  --mode transformer \
  --no-delay \
  --dict resources/CSW24.txt
```

### Flag Breakdown & Best Practices
- `--bot HastyBot`: Target opponent (`HastyBot`, `BestBot`, `BeginnerBot`).
- `--mode {lookahead,bc_0ply,transformer}`:
  - `lookahead`: 1-ply Monte Carlo lookahead with CRN, selective 2-ply, and exact endgame minimax.
  - `transformer`: SmolLM2 Candidate Ranker evaluating top GADDAG candidate plays with autoregressive attention.
  - `bc_0ply`: Sub-second 0-ply direct evaluation.
- `--transformer-model`: Path to local fine-tuned transformer weights (default: `models/transformer_ranker_v2`) or HuggingFace repo.
- `--no-delay`: Bypasses pacing delay sleep timers entirely, submitting moves immediately upon computation.
- `--delay-min / --delay-max`: Minimum/maximum natural thinking delay in seconds (ignored if `--no-delay` is passed).
- `--dict / --dictionary`: Lexicon file (`CSW24.txt` or `NWL23.txt`). The adapter automatically opens the Woogles challenge modal and clicks the corresponding Ant Design lexicon option (`CSW 24` or `NWL 23`).

---

## 4. Reading the Live Console Output

During live gameplay, Alphable prints rich, turn-by-turn strategic telemetry to the terminal:

```text
Match 1/15: Alphable vs HastyBot
Mode: lookahead, Dictionary: CSW24, Time: 15+0
=================================================================

--- Turn 1: Waiting for our turn... ---
Rack: [AEEIIOU] | Tiles in bag: 86
Generated 52 legal moves.
Generated 1 exchange candidate(s).
Selected Top 5 Candidates for Deep Simulation.
Candidate 1: EUOI at 6,7 | Points: 8 | Leave: -10.2 | Def: +2.0 | 0-Ply Val: 0.512 | 1-Ply Sim Equity: -46.4
Candidate 2: EUOI at 7,5 | Points: 8 | Leave: -10.2 | Def: +2.0 | 0-Ply Val: 0.473 | 1-Ply Sim Equity: -34.0
Candidate 3: EUOI at 7,7 | Points: 8 | Leave: -10.2 | Def: +2.0 | 0-Ply Val: 0.425 | 1-Ply Sim Equity: -33.8
Candidate 4: EUOI at 7,4 | Points: 8 | Leave: -10.2 | Def: +2.0 | 0-Ply Val: 0.330 | 1-Ply Sim Equity: -72.1
Candidate 5: EXCHANGE(E,A,I,I,O,U) at 7,7 | Points: 0 | Leave: +1.6 | Def: +0.0 | 0-Ply Val: 0.203 | 1-Ply Sim Equity: -29.2

Selective 2-Ply Triggered: Candidate 2 and 3 equity gap is 0.2 <= 8.0 pts.
Selected Best Move: EUOI at 7,5 (Equity: -34.0)
Submitting move: EUOI at 7,5...
Move confirmed on board! Current score: 8 - 0
```

### Key Console Indicators
1. **Rack & Bag Count:** Live tracking of our 7 hand tiles and remaining bag size.
2. **Candidate Breakdown:**
   - `Points`: Immediate points scored.
   - `Leave`: Super-Leaves empirical rack equity.
   - `Def`: Triple Word / Double Word defensive exposure bonus/penalty.
   - `0-Ply Val`: Value network evaluation of the after-state.
   - `1-Ply Sim Equity`: Net equity after simulating $N$ opponent counterattacks under CRN.
3. **Selective 2-Ply Trigger:** Indicates candidate equities are close ($\le 8.0$ pts), triggering deep second-ply counter-response evaluation.
4. **Exact Endgame Solver:** When `Tiles in bag: 0`, the console will report:
   ```text
   Endgame detected (bag=0, opp rack: XY). Solving exact minimax...
   Exact Endgame Move Selected: 'WORD' (0.0008s execution, margin: +14.0)
   ```

---

## 5. Match Artifacts & Telemetry Harvesting

Upon game completion, Alphable automatically exports four comprehensive data files to `data/woogles/matches/<timestamp>_<game_id>/`:

| File | Purpose |
| :--- | :--- |
| `game.gcg` | Standard tournament Scrabble Game Championship format record containing all moves, coordinates, and scores. |
| `analysis.json` | Complete post-game Macondo Grandmaster evaluations for every turn. Used to measure equity loss and train new distillation models. |
| `replay.json` | Structured JSON log containing board states, candidate moves, and predictions for the Web Visualizer. |
| `summary.json` | Match metadata (final scores, winner, total turns, elapsed time). |

### Series Summary
When the multi-game series completes, Alphable saves a consolidated report to:
`data/woogles/summaries/run_<timestamp>_series.json`
```json
{
  "total_games": 15,
  "wins": 8,
  "losses": 7,
  "draws": 0,
  "win_rate": 0.533,
  "avg_score_diff": 12.4,
  "avg_alphable_score": 454.8,
  "avg_opponent_score": 442.4
}
```

---

## 6. Error Recovery & Fault Tolerance

The Woogles platform runner incorporates robust error isolation to ensure unattended overnight runs complete successfully:

1. **Match Isolation (`runner.py`):**
   - Individual match crashes (e.g. transient network timeouts or opponent disconnects) do not crash the series runner.
   - The runner logs the error, safely resets the browser to the lobby URL (`https://woogles.io`), and launches the next match in the series.
2. **Ghost Tile Collision Prevention:**
   - In earlier versions, tiles left in the exchange modal rack could pollute active rack reads.
   - Fixed: Rack queries target `#board-container #rack .rack-tile:not(.ant-modal *)` to guarantee only active hand tiles are read.
3. **Modal Dialog Clearing:**
   - If an exchange modal or game-over modal remains on screen between matches, the adapter automatically dismisses it or refreshes the page.
4. **Playwright Selector Resiliency:**
   - Replaced fragile text selectors with valid Playwright pseudo-classes: `:text('Play a computer')` and `:text('Create game')`.
5. **Ant Design Lexicon Dropdown Synchronization:**
   - On Woogles, the challenge lexicon is an Ant Design dropdown component (`#seekForm_lexicon`). Native `<select>` manipulation fails.
   - The adapter clicks `.ant-select-selector`, waits for `.ant-select-item-option`, and clicks the matching lexicon item (`NWL 23` vs `CSW 24`).
6. **Zero-Delay Pacing Bypass:**
   - When `--no-delay` is passed, `runner.py` bypasses all sleep timers (`actual_sleep = 0.0`), eliminating any artificial pause between move computation and submission.

---

## 7. Useful Command Cheat Sheet

```bash
# 1. Standard 15-game series against HastyBot in lookahead mode
python -m alphable.cli.main play woogles \
  --bot HastyBot \
  --games 15 \
  --model models/alphable_v3_macondo_v2.pth \
  --mode lookahead \
  --top-k 5 --simulations 10

# 2. SmolLM2 Transformer Ranker series against HastyBot
python -m alphable.cli.main play woogles \
  --bot HastyBot \
  --games 5 \
  --mode transformer \
  --transformer-model models/transformer_ranker_v2 \
  --dict resources/CSW24.txt

# 3. High-speed zero-delay match on Woogles
python -m alphable.cli.main play woogles \
  --bot HastyBot \
  --mode transformer \
  --no-delay \
  --dict resources/CSW24.txt

# 4. Play against BestBot on North American Lexicon (NWL23)
python -m alphable.cli.main play woogles \
  --bot BestBot \
  --games 5 \
  --dict resources/NWL23.txt \
  --mode lookahead

# 5. Fast 10-game validation in headless mode
python -m alphable.cli.main play woogles \
  --bot HastyBot \
  --games 10 \
  --headless \
  --model models/alphable_v3_macondo_v2.pth
```
