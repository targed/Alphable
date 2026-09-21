"""
Alphable Replay Visualizer - Flask Backend API
Serves game JSON files, interactive gameplay endpoints, and static React frontend assets.
"""

import os
import sys
import json
import random
from pathlib import Path
from datetime import datetime
import traceback

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

# Add src directory to path to import alphable modules
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR / "src"))

import torch
from alphable.core import inference, simulator, structure
from alphable.training.self_play import evaluate_moves as get_move_evals, choose_move_with_temperature

FRONTEND_BUILD_DIR = BASE_DIR / "visualizer" / "frontend" / "build"
RESOURCES_DIR = BASE_DIR / "resources"
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"
DEFAULT_DICT_PATH = RESOURCES_DIR / "CSW24.txt"

app = Flask(
    __name__,
    static_folder=str(FRONTEND_BUILD_DIR / "static") if (FRONTEND_BUILD_DIR / "static").exists() else None,
    static_url_path="/static"
)
CORS(app)  # Enable CORS for all origins in development and local usage

# Known / discovered game replay directories under data/
DATA_DIRS = {
    "results": DATA_DIR / "results",
    "vs_greedy": DATA_DIR / "vs_greedy",
    "vs_random": DATA_DIR / "vs_random",
    "matches": DATA_DIR / "matches",
}

# Cache for inference engines keyed by (model_path, dictionary_path, value_weight)
engines = {}


def get_default_model_name():
    """Pick the highest-quality existing model checkpoint."""
    priority = [
        "alphable_v3_expert.pth",
        "alphable_v3_rl_gen2.pth",
        "alphable_best_val_model.pth",
        "alphable_rl_best_val_model.pth",
    ]
    for name in priority:
        if (MODELS_DIR / name).exists():
            return name
    if MODELS_DIR.exists():
        for p in sorted(MODELS_DIR.glob("*.pth")):
            return p.name
    return None


def get_engine(model_name=None, dictionary_name=None, value_weight=60.0):
    """
    Lazy-load and cache AlphableInference engines per dictionary, model, and value_weight.
    """
    global engines

    if not dictionary_name:
        dictionary_name = "CSW24.txt"

    dict_path = RESOURCES_DIR / dictionary_name
    if not dict_path.exists():
        dict_path = DEFAULT_DICT_PATH
        dictionary_name = "CSW24.txt"

    if not model_name:
        model_name = get_default_model_name()

    model_file = (MODELS_DIR / model_name) if model_name else None
    m_path = str(model_file) if (model_file and model_file.exists()) else None
    vw = float(value_weight) if value_weight is not None else 60.0

    cache_key = (m_path, str(dict_path), vw)

    if cache_key not in engines:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Loading engine on {device} (model={model_name}, dict={dictionary_name}, value_weight={vw})...")
        eng = inference.AlphableInference(
            model_path=m_path,
            device=device,
            dict_path=str(dict_path),
            value_weight=vw
        )
        engines[cache_key] = eng
        print(f"Engine cached successfully for {cache_key}.")

    return engines[cache_key]


def discover_game_dirs():
    """Discover all directories under data/ that may contain replay files."""
    discovered = dict(DATA_DIRS)
    if DATA_DIR.exists():
        for item in DATA_DIR.iterdir():
            if item.is_dir() and item.name != 'summaries' and item.name != '__pycache__':
                if item.name not in discovered:
                    discovered[item.name] = item
    return discovered


# ==========================================
# API Routes
# ==========================================

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint providing status and loaded engines."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "default_model": get_default_model_name(),
        "engines_cached": len(engines),
        "frontend_built": FRONTEND_BUILD_DIR.exists(),
        "dictionaries": [f.name for f in RESOURCES_DIR.glob("*.txt")] if RESOURCES_DIR.exists() else [],
        "models": [f.name for f in MODELS_DIR.glob("*.pth")] if MODELS_DIR.exists() else [],
        "data_dirs": list(discover_game_dirs().keys())
    })


@app.route('/api/dictionaries', methods=['GET'])
def list_dictionaries():
    """Return a list of available dictionary files in resources/."""
    try:
        dicts = []
        if RESOURCES_DIR.exists():
            for f in RESOURCES_DIR.glob("*.txt"):
                dicts.append(f.name)
        return jsonify({"dictionaries": sorted(dicts)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/models', methods=['GET'])
def list_models():
    """Return available neural network checkpoints in models/."""
    try:
        models = []
        if MODELS_DIR.exists():
            for p in sorted(MODELS_DIR.glob("*.pth")):
                stat = p.stat()
                models.append({
                    "name": p.name,
                    "path": str(p),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        return jsonify({
            "models": models,
            "default": get_default_model_name()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/games', methods=['GET'])
def list_games():
    """
    List all available game replay JSON files.
    Filters out summary JSON files (*summary.json) and non-replay data.
    """
    games = []
    all_dirs = discover_game_dirs()

    for category, directory in all_dirs.items():
        if not directory.exists():
            continue

        for json_file in directory.glob("*.json"):
            # Exclude run summary files and game summary files
            if json_file.name.endswith('_summary.json') or json_file.name == 'summary.json':
                continue

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Validate this is an actual game replay containing turns
                turns = data.get("turns")
                if not isinstance(turns, list):
                    continue

                player_names = data.get("player_names", ["Player 0", "Player 1"])
                final_score = data.get("final_score", [0, 0])
                p0_score = final_score[0] if len(final_score) > 0 else 0
                p1_score = final_score[1] if len(final_score) > 1 else 0

                winner = None
                if p0_score > p1_score:
                    winner = player_names[0]
                elif p1_score > p0_score:
                    winner = player_names[1]
                else:
                    winner = "Tie"

                # Count bingos (>= 7 letters)
                bingos = sum(1 for t in turns if t.get("action_type") == "PLAY" and len(t.get("word", "") or "") >= 7)

                try:
                    rel_path = str(json_file.relative_to(BASE_DIR))
                except ValueError:
                    rel_path = str(json_file)

                games.append({
                    "id": json_file.stem,
                    "filename": json_file.name,
                    "category": category,
                    "path": rel_path,
                    "timestamp": data.get("timestamp", ""),
                    "player_names": player_names,
                    "final_score": final_score,
                    "score_margin": abs(p0_score - p1_score),
                    "winner": winner,
                    "bingos": bingos,
                    "total_turns": len(turns),
                    "metadata": data.get("metadata", {})
                })
            except Exception as e:
                # Silently skip malformed/unrelated JSON files
                continue

    # Sort by timestamp (newest first)
    games.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)

    return jsonify({
        "games": games,
        "count": len(games)
    })


@app.route('/api/games/<category>/<filename>', methods=['GET'])
@app.route('/api/game/<category>/<filename>', methods=['GET'])
def get_game(category, filename):
    """Get a specific game's full JSON replay data."""
    all_dirs = discover_game_dirs()
    if category not in all_dirs:
        return jsonify({"error": f"Invalid category: {category}"}), 404

    safe_filename = Path(filename).name
    json_file = all_dirs[category] / safe_filename

    if not json_file.exists():
        return jsonify({"error": "Game not found"}), 404

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_overall_stats():
    """Get aggregate statistics across all available games."""
    all_dirs = discover_game_dirs()
    category_counts = {}
    total_games = 0
    for category, directory in all_dirs.items():
        if directory.exists():
            count = sum(1 for f in directory.glob("*.json") if not (f.name.endswith('_summary.json') or f.name == 'summary.json'))
            category_counts[category] = count
            total_games += count
    return jsonify({
        "total_games": total_games,
        "categories": category_counts
    })


@app.route('/api/stats/<category>/<filename>', methods=['GET'])
def get_game_stats(category, filename):
    """Get comprehensive statistics for a specific game replay."""
    all_dirs = discover_game_dirs()
    if category not in all_dirs:
        return jsonify({"error": "Invalid category"}), 404

    safe_filename = Path(filename).name
    json_file = all_dirs[category] / safe_filename

    if not json_file.exists():
        return jsonify({"error": "Game not found"}), 404

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        turns = data.get("turns", [])
        player_names = data.get("player_names", ["Player 0", "Player 1"])
        final_scores = data.get("final_score", [0, 0])

        stats = {
            "total_turns": len(turns),
            "player_stats": [{}, {}]
        }

        for player_id in [0, 1]:
            player_moves = [t for t in turns if t.get("player") == player_id]
            plays = [t for t in player_moves if t.get("action_type") == "PLAY"]
            passes = [t for t in player_moves if t.get("action_type") == "PASS"]
            exchanges = [t for t in player_moves if t.get("action_type") == "EXCHANGE"]

            # Bingos include any play of 7 or more letters
            bingos = [t for t in plays if t.get("word") and len(t["word"]) >= 7]
            total_score = sum(t.get("score", 0) for t in player_moves)
            avg_score = total_score / len(player_moves) if player_moves else 0

            stats["player_stats"][player_id] = {
                "name": player_names[player_id] if player_id < len(player_names) else f"Player {player_id}",
                "total_moves": len(player_moves),
                "plays": len(plays),
                "passes": len(passes),
                "exchanges": len(exchanges),
                "bingos": len(bingos),
                "bingo_words": [t["word"] for t in bingos],
                "total_score": total_score,
                "average_score_per_move": round(avg_score, 2),
                "highest_scoring_move": max((t.get("score", 0) for t in plays), default=0),
                "final_score": final_scores[player_id] if player_id < len(final_scores) else total_score
            }

        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/interactive/ai_move', methods=['POST'])
def interactive_ai_move():
    """
    Endpoint to evaluate board position and select the AI's next move.
    Supports alphable (with selectable model & value_weight), greedy, and random bots.
    """
    try:
        data = request.json or {}
        board = data.get('board')
        rack = data.get('rack')
        score_diff = int(data.get('score_diff', 0))
        bag_remaining = int(data.get('bag_remaining', 100))
        ai_type = data.get('ai_type', 'alphable')  # 'alphable', 'random', 'greedy'
        temperature = float(data.get('temperature', 0.0))
        top_k = int(data.get('top_k', 3))
        dictionary_name = data.get('dictionary', 'CSW24.txt')
        model_name = data.get('model', None)
        value_weight = float(data.get('value_weight', 60.0))

        if not board or not rack:
            return jsonify({"error": "Board and rack are required"}), 400

        eng = get_engine(
            model_name=model_name,
            dictionary_name=dictionary_name,
            value_weight=value_weight
        )

        # 1. Evaluate legal moves using the engine
        evals = get_move_evals(
            eng,
            board,
            rack,
            score_diff,
            bag_remaining,
            value_weight=value_weight
        )

        if not evals:
            return jsonify({
                "action": "PASS",
                "evaluated_moves": []
            })

        # Format evaluated moves for frontend inspection panel
        formatted_evals = []
        for e in evals:
            move = e['move']
            formatted_evals.append({
                "word": move['word'],
                "row": move['row'],
                "col": move['col'],
                "direction": move['dir'],
                "points": e['points'],
                "value": round(float(e['value']), 4),
                "equity": round(float(e.get('equity', e['points'] + value_weight * e['value'])), 2),
                "new_rack": e['new_rack']
            })

        # 2. Select move based on ai_type
        selected_move_eval = None

        if ai_type == 'random':
            selected_move_eval = random.choice(evals)
        elif ai_type == 'greedy':
            # Highest immediate points
            if temperature > 1e-4:
                # Softmax over top-K by score
                by_points = sorted(evals, key=lambda x: x['points'], reverse=True)[:top_k]
                scores = [x['points'] for x in by_points]
                max_s = max(scores)
                weights = [random.expovariate(1.0) * (s - max_s) for s in scores]  # Gumbel sample
                selected_move_eval = by_points[max(range(len(scores)), key=lambda i: scores[i] + temperature * weights[i])]
            else:
                selected_move_eval = max(evals, key=lambda x: x['points'])
        else:
            # Alphable with equity & temperature
            selected_move_eval = choose_move_with_temperature(
                evals,
                temperature=temperature,
                top_k=top_k
            )
            if selected_move_eval is None:
                selected_move_eval = evals[0]

        return jsonify({
            "action": "PLAY",
            "move": {
                "word": selected_move_eval['move']['word'],
                "row": selected_move_eval['move']['row'],
                "col": selected_move_eval['move']['col'],
                "direction": selected_move_eval['move']['dir']
            },
            "points": selected_move_eval['points'],
            "value": round(float(selected_move_eval['value']), 4),
            "equity": round(float(selected_move_eval.get('equity', selected_move_eval['points'] + value_weight * selected_move_eval['value'])), 2),
            "new_rack": selected_move_eval['new_rack'],
            "evaluated_moves": formatted_evals,
            "evals": formatted_evals
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/interactive/validate_user_move', methods=['POST'])
def validate_user_move():
    """
    Validates a human player's move against the board and dictionary.
    Returns legal points and remaining rack tiles if valid.
    """
    try:
        data = request.json or {}
        board = data.get('board')
        rack = data.get('rack')
        move_data = data.get('move')
        dictionary_name = data.get('dictionary', 'CSW24.txt')

        if not board or not rack or not move_data:
            return jsonify({"error": "Board, rack, and move are required"}), 400

        eng = get_engine(dictionary_name=dictionary_name)

        move = {
            'word': move_data['word'].upper(),
            'row': int(move_data['row']),
            'col': int(move_data['col']),
            'dir': move_data['direction'].capitalize()  # Across or Down
        }

        legal_moves = eng.move_gen.generate(board, rack)

        is_legal = False
        points = 0
        new_rack = []

        for m in legal_moves:
            if (m['word'].upper() == move['word'] and
                    m['row'] == move['row'] and
                    m['col'] == move['col'] and
                    m['dir'].capitalize() == move['dir']):
                is_legal = True
                _, points, new_rack = simulator.simulate_move(board, m, rack)
                break

        if is_legal:
            return jsonify({
                "valid": True,
                "points": points,
                "score": points,
                "new_rack": new_rack
            })
        else:
            return jsonify({
                "valid": False,
                "error": "Move is not legal for the current board and rack"
            })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ==========================================
# Frontend Static Asset Serving
# ==========================================

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """
    Serves the compiled React frontend directly when available.
    Enables single-process operation without requiring a running Node server.
    """
    if path.startswith('api/'):
        return jsonify({"error": f"API endpoint not found: /{path}"}), 404

    if FRONTEND_BUILD_DIR.exists():
        target = FRONTEND_BUILD_DIR / path
        if path and target.exists() and target.is_file():
            return send_from_directory(str(FRONTEND_BUILD_DIR), path)
        index_html = FRONTEND_BUILD_DIR / "index.html"
        if index_html.exists():
            return send_from_directory(str(FRONTEND_BUILD_DIR), "index.html")

    return jsonify({
        "service": "Alphable Visualizer Backend",
        "status": "online",
        "api_docs": "/api/health",
        "message": "Frontend build not found. Run 'npm run build' in visualizer/frontend or launch React dev server."
    })


if __name__ == '__main__':
    # Ensure standard data directories exist
    for d in DATA_DIRS.values():
        d.mkdir(parents=True, exist_ok=True)

    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'

    print(f"Starting Alphable Replay Visualizer Backend on http://{host}:{port} ...")
    app.run(debug=debug, host=host, port=port, use_reloader=debug)
