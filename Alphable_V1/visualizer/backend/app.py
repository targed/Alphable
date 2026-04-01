"""
Alphable Replay Visualizer - Flask Backend API
Serves game JSON files and provides endpoints for browsing games
"""

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import os
import json
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Base directory for game data
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIRS = {
    "results": BASE_DIR / "data" / "results",
    "vs_greedy": BASE_DIR / "data" / "vs_greedy",
    "vs_random": BASE_DIR / "data" / "vs_random"
}


@app.route('/api/games', methods=['GET'])
def list_games():
    """List all available game JSON files."""
    games = []
    
    for category, directory in DATA_DIRS.items():
        if not directory.exists():
            continue
            
        for json_file in directory.glob("*.json"):
            try:
                # Read basic info from JSON
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                games.append({
                    "id": json_file.stem,  # filename without extension
                    "filename": json_file.name,
                    "category": category,
                    "path": str(json_file.relative_to(BASE_DIR)),
                    "timestamp": data.get("timestamp", ""),
                    "player_names": data.get("player_names", ["Player 0", "Player 1"]),
                    "final_score": data.get("final_score", [0, 0]),
                    "total_turns": len(data.get("turns", [])),
                    "metadata": data.get("metadata", {})
                })
            except Exception as e:
                print(f"Error reading {json_file}: {e}")
                continue
    
    # Sort by timestamp (newest first)
    games.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return jsonify({
        "games": games,
        "count": len(games)
    })


@app.route('/api/games/<category>/<filename>', methods=['GET'])
def get_game(category, filename):
    """Get a specific game's full JSON data."""
    if category not in DATA_DIRS:
        return jsonify({"error": "Invalid category"}), 404
    
    json_file = DATA_DIRS[category] / filename
    
    if not json_file.exists():
        return jsonify({"error": "Game not found"}), 404
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/stats/<category>/<filename>', methods=['GET'])
def get_game_stats(category, filename):
    """Get statistics for a specific game."""
    if category not in DATA_DIRS:
        return jsonify({"error": "Invalid category"}), 404
    
    json_file = DATA_DIRS[category] / filename
    
    if not json_file.exists():
        return jsonify({"error": "Game not found"}), 404
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Calculate statistics
        turns = data.get("turns", [])
        stats = {
            "total_turns": len(turns),
            "player_stats": [{}, {}]
        }
        
        for player_id in [0, 1]:
            player_moves = [t for t in turns if t["player"] == player_id]
            plays = [t for t in player_moves if t["action_type"] == "PLAY"]
            passes = [t for t in player_moves if t["action_type"] == "PASS"]
            exchanges = [t for t in player_moves if t["action_type"] == "EXCHANGE"]
            
            bingos = [t for t in plays if t.get("word") and len(t["word"]) == 7]
            
            total_score = sum(t.get("score", 0) for t in player_moves)
            avg_score = total_score / len(player_moves) if player_moves else 0
            
            stats["player_stats"][player_id] = {
                "name": data.get("player_names", ["Player 0", "Player 1"])[player_id],
                "total_moves": len(player_moves),
                "plays": len(plays),
                "passes": len(passes),
                "exchanges": len(exchanges),
                "bingos": len(bingos),
                "bingo_words": [t["word"] for t in bingos],
                "total_score": total_score,
                "average_score_per_move": round(avg_score, 2),
                "highest_scoring_move": max((t.get("score", 0) for t in plays), default=0),
                "final_score": data.get("final_score", [0, 0])[player_id]
            }
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "data_dirs": {k: str(v) for k, v in DATA_DIRS.items()}
    })


if __name__ == '__main__':
    # Ensure data directories exist
    for directory in DATA_DIRS.values():
        directory.mkdir(parents=True, exist_ok=True)
    
    print("Starting Alphable Replay Visualizer Backend...")
    print(f"Data directories:")
    for name, path in DATA_DIRS.items():
        print(f"  {name}: {path}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
