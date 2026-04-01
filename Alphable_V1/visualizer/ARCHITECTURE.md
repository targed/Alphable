# Alphable Replay Visualizer - Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ALPHABLE SCRABBLE AI SYSTEM                       │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ Game Execution
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         GAME SCRIPTS                                 │
├─────────────────────────────────────────────────────────────────────┤
│  • evaluate_vs_greedy.py  - AlphaZero vs Greedy Bot                 │
│  • evaluate_vs_random.py  - AlphaZero vs Random Bot                 │
│  • watch_bot.py           - Self-play matches                       │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ Uses
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      GAME LOGGER MODULE                              │
├─────────────────────────────────────────────────────────────────────┤
│  game_logger.py                                                      │
│  • Captures turn-by-turn state                                      │
│  • Records moves, racks, scores                                     │
│  • Stores board states                                              │
│  • Calculates statistics                                            │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ Outputs JSON
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA STORAGE                                 │
├─────────────────────────────────────────────────────────────────────┤
│  data/                                                               │
│  ├── vs_greedy/*.json    - Games vs Greedy Bot                      │
│  ├── vs_random/*.json    - Games vs Random Bot                      │
│  └── results/*.json      - Self-play games                          │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ Reads JSON
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       BACKEND API (Flask)                            │
├─────────────────────────────────────────────────────────────────────┤
│  visualizer/backend/app.py                                           │
│                                                                      │
│  Endpoints:                                                          │
│  • GET /api/games              - List all games                     │
│  • GET /api/games/<id>         - Get full game data                 │
│  • GET /api/stats/<id>         - Get game statistics                │
│  • GET /api/health             - Health check                       │
│                                                                      │
│  Port: 5000                                                          │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ REST API (JSON)
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React/TypeScript)                       │
├─────────────────────────────────────────────────────────────────────┤
│  visualizer/frontend/src/                                            │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ App.tsx - Main Application                                    │  │
│  │ • Game selection state                                        │  │
│  │ • API communication                                           │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                           │                                          │
│         ┌─────────────────┴─────────────────┐                        │
│         ▼                                   ▼                        │
│  ┌──────────────┐                    ┌──────────────┐               │
│  │  GameList    │                    │  GameViewer  │               │
│  │              │                    │              │               │
│  │ • Browse     │                    │ • Main view  │               │
│  │ • Select     │                    │ • Orchestr.  │               │
│  └──────────────┘                    └──────────────┘               │
│                                             │                        │
│                      ┌──────────────────────┼──────────────────────┐ │
│                      ▼                      ▼                      ▼ │
│              ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│              │  PlayerHUD   │      │    Board     │      │   MoveLog    │
│              │              │      │              │      │              │
│              │ • Score      │      │ • 15x15 grid │      │ • History    │
│              │ • Rack       │      │ • Tiles      │      │ • Click-jump │
│              │ • Avatar     │      │ • Premium    │      │ • Stats      │
│              └──────────────┘      └──────────────┘      └──────────────┘
│                                             │                            │
│                                             ▼                            │
│                                   ┌──────────────┐                      │
│                                   │  Playback    │                      │
│                                   │  Controls    │                      │
│                                   │              │                      │
│                                   │ • Timeline   │                      │
│                                   │ • Transport  │                      │
│                                   │ • Speed      │                      │
│                                   └──────────────┘                      │
│                                                                         │
│  Port: 3000                                                             │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ Renders
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         WEB BROWSER                                  │
├─────────────────────────────────────────────────────────────────────┤
│  User Interface:                                                     │
│  • Interactive game board with premium squares                       │
│  • Player HUDs with scores and racks                                │
│  • Playback controls (play/pause, timeline, speed)                  │
│  • Move log with click-to-jump                                      │
│  • Smooth animations and visual effects                             │
└─────────────────────────────────────────────────────────────────────┘


DATA FLOW:
──────────

1. Game Execution → GameLogger → JSON Files
2. Flask Backend reads JSON Files → Serves via REST API
3. React Frontend fetches from API → Renders UI
4. User interactions → State updates → UI re-renders


TECHNOLOGY STACK:
────────────────

Backend:
• Python 3.8+
• Flask (web framework)
• flask-cors (CORS support)

Frontend:
• React 18
• TypeScript 5
• CSS3 (animations)

Data Format:
• JSON (game logs)
• REST API (communication)
