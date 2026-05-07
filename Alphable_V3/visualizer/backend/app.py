"""
Alphable Replay Visualizer - Flask Backend API
Serves game JSON files and provides endpoints for browsing games
"""

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import os
import sys
import json
from pathlib import Path
from datetime import datetime
import traceback

# Add src directory to path to import alphable modules
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

import torch
from alphable.core import inference, simulator, structure
from alphable.eval.evaluate_matches import choose_move, evaluate_moves as get_move_evals

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Base directory for game data
BASE_DIR = Path(__file__).parent.parent.parent
DEFAULT_DICT_PATH = BASE_DIR / "resources" / "CSW24.txt"
RESOURCES_DIR = BASE_DIR / "resources"
MODEL_PATH = BASE_DIR / "models" / "alphable_best_val_model.pth"

# Lazy load AI models per dictionary
engines = {}

def get_engine(dictionary_name=None):
    global engines

    if not dictionary_name:
        dictionary_name = "CSW24.txt"

    dict_path = RESOURCES_DIR / dictionary_name
    if not dict_path.exists():
        dict_path = DEFAULT_DICT_PATH
        dictionary_name = "CSW24.txt"

    if dictionary_name not in engines:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Loading Alphable engine on {device} with dictionary {dictionary_name}...")
        try:
            # We only load if model path exists
            m_path = str(MODEL_PATH) if MODEL_PATH.exists() else None
            engines[dictionary_name] = inference.AlphableInference(
                model_path=m_path,
                device=device,
                dict_path=str(dict_path)
            )
            print(f"Alphable engine loaded for {dictionary_name}.")
        except Exception as e:
            print(f"Failed to load engine for {dictionary_name}: {e}")
            raise
    return engines[dictionary_name]
DATA_DIRS = {
    "results": BASE_DIR / "data" / "results",
    "vs_greedy": BASE_DIR / "data" / "vs_greedy",
    "vs_random": BASE_DIR / "data" / "vs_random"
}


@app.route('/api/dictionaries')
def list_dictionaries():
    """Return a list of available dictionary files."""
    try:
        dicts = []
        if RESOURCES_DIR.exists():
            for f in RESOURCES_DIR.glob("*.txt"):
                dicts.append(f.name)
        return jsonify({"dictionaries": sorted(dicts)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
    
    # Sanitize filename to prevent path traversal
    safe_filename = Path(filename).name
    json_file = DATA_DIRS[category] / safe_filename
    
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
    
    # Sanitize filename to prevent path traversal
    safe_filename = Path(filename).name
    json_file = DATA_DIRS[category] / safe_filename
    
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


@app.route('/api/interactive/ai_move', methods=['POST'])
def interactive_ai_move():
    """
    Endpoint to evaluate and select the AI's next move.
    """
    try:
        data = request.json
        board = data.get('board')
        rack = data.get('rack')
        score_diff = data.get('score_diff', 0)
        bag_remaining = data.get('bag_remaining', 100)
        ai_type = data.get('ai_type', 'alphable') # 'alphable', 'random', 'greedy'
        temperature = float(data.get('temperature', 0.0))
        top_k = int(data.get('top_k', 3))
        dictionary_name = data.get('dictionary', 'CSW24.txt')

        if not board or not rack:
            return jsonify({"error": "Board and rack are required"}), 400

        eng = get_engine(dictionary_name)

        # 1. Evaluate all moves using the engine
        evals = get_move_evals(eng, board, rack, score_diff, bag_remaining)

        if not evals:
            return jsonify({
                "action": "PASS",
                "evaluated_moves": []
            })

        # Format evaluated moves for frontend
        formatted_evals = []
        for e in evals:
            move = e['move']
            formatted_evals.append({
                "word": move['word'],
                "row": move['row'],
                "col": move['col'],
                "direction": move['dir'],
                "points": e['points'],
                "value": e['value'],
                "new_rack": e['new_rack']
            })

        # 2. Select move based on ai_type and temperature
        selected_move_eval = None

        if ai_type == 'random':
            import random
            selected_move_eval = random.choice(evals)
        elif ai_type == 'greedy':
            # Sort by points, highest first
            greedy_evals = sorted(evals, key=lambda x: x['points'], reverse=True)
            # Apply temperature to top_k greedy moves
            # We mock the 'value' with points for the choose_move function
            mock_evals = []
            for ge in greedy_evals:
                mock = ge.copy()
                mock['value'] = ge['points']
                mock_evals.append(mock)

            selected_mock = choose_move(mock_evals, temperature=temperature, top_k=top_k)
            # Find the original eval
            for e in evals:
                if e['move'] == selected_mock['move']:
                    selected_move_eval = e
                    break
        else: # alphable
            selected_move_eval = choose_move(evals, temperature=temperature, top_k=top_k)

        return jsonify({
            "action": "PLAY",
            "move": {
                "word": selected_move_eval['move']['word'],
                "row": selected_move_eval['move']['row'],
                "col": selected_move_eval['move']['col'],
                "direction": selected_move_eval['move']['dir']
            },
            "points": selected_move_eval['points'],
            "value": selected_move_eval['value'],
            "new_rack": selected_move_eval['new_rack'],
            "evaluated_moves": formatted_evals
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/interactive/validate_user_move', methods=['POST'])
def validate_user_move():
    """
    Validates a user-submitted move.
    """
    try:
        data = request.json
        board = data.get('board')
        rack = data.get('rack')
        move_data = data.get('move')
        dictionary_name = data.get('dictionary', 'CSW24.txt')

        if not board or not rack or not move_data:
            return jsonify({"error": "Board, rack, and move are required"}), 400

        eng = get_engine(dictionary_name)

        # Convert move_data to engine move format
        move = {
            'word': move_data['word'].upper(),
            'row': int(move_data['row']),
            'col': int(move_data['col']),
            'dir': move_data['direction'] # 'Across' or 'Down'
        }

        # We need to verify if it's a legal move by generating all legal moves and checking
        # Or more simply, since we know the move, we can just check if it's in the legal moves list
        legal_moves = eng.move_gen.generate(board, rack)

        is_legal = False
        points = 0
        new_rack = []

        for m in legal_moves:
            if m['word'] == move['word'] and m['row'] == move['row'] and m['col'] == move['col'] and m['dir'] == move['dir']:
                is_legal = True
                _, points, new_rack = simulator.simulate_move(board, m, rack)
                break

        if is_legal:
            return jsonify({
                "valid": True,
                "points": points,
                "new_rack": new_rack
            })
        else:
            return jsonify({
                "valid": False,
                "error": "Invalid move"
            })

    except Exception as e:
        traceback.print_exc()
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
