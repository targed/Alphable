# Alphable Replay Visualizer (ARV)

A broadcast-quality graphical interface for analyzing AlphaZero Scrabble games.

## Features Implemented

### Phase 1: JSON Game Logger ✅
- **GameLogger class** (`game_logger.py`) captures complete game state
- Integrated into `evaluate_vs_greedy.py`, `evaluate_vs_random.py`, and `watch_bot.py`
- Generates JSON files with moves, racks, scores, and board states

### Phase 2: Web Viewer (MVP) ✅
- **Backend**: Flask API serving game data
- **Frontend**: React/TypeScript application

### Requirements Coverage

#### Board View (REQ-101 to REQ-105) ✅
- ✅ REQ-101: 15x15 grid rendering
- ✅ REQ-102: Premium squares color-coded (TW=Red, DW=Pink, TL=Blue, DL=Light Blue)
- ✅ REQ-103: Tiles as rounded squares with tan background and black text
- ✅ REQ-104: Move highlighting with glowing borders and animations
- ✅ REQ-105: Coordinate system (1-15 rows, A-O columns)

#### Player HUD (REQ-201 to REQ-205) ✅
- ✅ REQ-201: Two player panels (left and right)
- ✅ REQ-202: Prominent score display
- ✅ REQ-203: Score delta floating text animation (+42, etc.)
- ✅ REQ-204: Rack view (7 tiles visible)
- ✅ REQ-205: Player name/avatar display

#### Playback Controls (REQ-401 to REQ-403) ✅
- ✅ REQ-401: Timeline slider for scrubbing through turns
- ✅ REQ-402: Transport controls (⏮ ⏪ ▶️ ⏩ ⏭)
- ✅ REQ-403: Playback speed selector (0.5x, 1x, 2x, 5x)

#### Move Log (REQ-501 to REQ-502) ✅
- ✅ REQ-501: Scrollable move list with standard notation, click-to-jump
- ✅ REQ-502: End-game statistics (bingos, avg score, etc.)

#### Broadcaster Features (REQ-301 to REQ-303) ⚠️
- ✅ REQ-302: Bag tracker showing tiles remaining
- ⏳ REQ-301: Word definitions (ready for API integration)
- ⏳ REQ-303: Win probability bar (ready when AI evaluation data available)

## Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

1. Install Python dependencies:
```bash
cd visualizer/backend
pip install -r requirements.txt
```

2. Run the Flask server:
```bash
python app.py
```

The backend will start on `http://localhost:5000`

### Frontend Setup

1. Install Node dependencies:
```bash
cd visualizer/frontend
npm install
```

2. Start the React development server:
```bash
npm start
```

The frontend will open at `http://localhost:3000`

## Usage

### Generating Game Replays

1. Run any evaluation script to generate JSON logs:
```bash
python evaluate_vs_greedy.py
python evaluate_vs_random.py
python watch_bot.py
```

2. JSON files will be saved to:
   - `data/vs_greedy/` - AlphaZero vs Greedy Bot games
   - `data/vs_random/` - AlphaZero vs Random Bot games
   - `data/results/` - Self-play games

### Watching Games

1. Start both backend and frontend servers
2. Open `http://localhost:3000` in your browser
3. Select a game from the list
4. Use playback controls to watch the game:
   - **Timeline slider**: Jump to any turn
   - **▶️ Play**: Auto-play through the game
   - **Speed selector**: Adjust playback speed
   - **Move log**: Click any move to jump to that turn

## Architecture

```
visualizer/
├── backend/                # Flask API server
│   ├── app.py             # Main API with endpoints
│   └── requirements.txt   # Python dependencies
│
└── frontend/              # React TypeScript app
    ├── public/            # Static files
    ├── src/
    │   ├── components/    # React components
    │   │   ├── Board.tsx           # 15x15 grid with premium squares
    │   │   ├── GameList.tsx        # Game selection menu
    │   │   ├── GameViewer.tsx      # Main game viewer
    │   │   ├── MoveLog.tsx         # Move history panel
    │   │   ├── PlayerHUD.tsx       # Player info and score
    │   │   └── PlaybackControls.tsx # Timeline and transport controls
    │   ├── types.ts       # TypeScript definitions
    │   ├── App.tsx        # Main app component
    │   └── index.tsx      # Entry point
    └── package.json       # Node dependencies
```

## API Endpoints

- `GET /api/games` - List all available games
- `GET /api/games/<category>/<filename>` - Get full game data
- `GET /api/stats/<category>/<filename>` - Get game statistics
- `GET /api/health` - Health check

## Next Steps (Phase 3 & 4)

### Planned Enhancements
- [ ] Word definition lookup (integrate dictionary API)
- [ ] Win probability visualization (when AI evaluation data available)
- [ ] Enhanced animations and polish
- [ ] Statistics dashboard
- [ ] Game comparison view
- [ ] Export replays as video

## Technologies Used

- **Backend**: Flask, Python 3
- **Frontend**: React 18, TypeScript 5
- **Styling**: CSS3 with animations
- **Architecture**: RESTful API, Component-based UI

## License

Part of the Alphable project.
