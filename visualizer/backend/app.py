"""
Alphable Visualizer Studio - Flask Backend Server.
Provides engine-agnostic APIs for V4, V3, and baselines, plus game replay serving.
"""

import os
import sys
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from visualizer.backend.adapters.v4_adapter import V4Adapter
from visualizer.backend.adapters.v3_adapter import V3Adapter
from visualizer.backend.adapters.baseline_adapter import BaselineAdapter
from visualizer.backend.services.replay_service import ReplayService
from visualizer.backend.services.dictionary_service import dictionary_service

FRONTEND_BUILD_DIR = Path(__file__).resolve().parent.parent / "frontend" / "build"


def create_app() -> Flask:
    """App factory for visualizer backend server."""
    app = Flask(
        __name__,
        static_folder=str(FRONTEND_BUILD_DIR / "static") if (FRONTEND_BUILD_DIR / "static").exists() else None,
        static_url_path="/static"
    )
    CORS(app)

    # Initialize adapters and services
    v4 = V4Adapter()
    v3 = V3Adapter()
    baseline = BaselineAdapter()
    replay_service = ReplayService()

    adapters = {
        "v4": v4,
        "v3": v3,
        "baseline": baseline,
        "magpie": baseline,
        "greedy": baseline,
    }

    def _resolve_adapter(engine_key: str):
        key = (engine_key or "v4").lower()
        if key in ("magpie", "greedy"):
            return baseline
        return adapters.get(key, v4)

    # =========================================================================
    # API Routes
    # =========================================================================

    @app.route('/api/health', methods=['GET'])
    def health():
        return jsonify({
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "available_engines": list(adapters.keys()),
            "frontend_built": FRONTEND_BUILD_DIR.exists()
        })

    @app.route('/api/engines', methods=['GET'])
    def list_engines():
        engine_list = [
            {"id": "v4", "name": v4.get_name(), "description": "State-of-the-Art BAMS Search with C MAGPIE"},
            {"id": "v3", "name": v3.get_name(), "description": "Macondo Distilled ResNet & Transformer Ranker"},
            {"id": "magpie", "name": "Base MAGPIE", "description": "Classical C engine with KLV static equity"},
            {"id": "greedy", "name": "Score Greedy", "description": "Immediate points maximizer"}
        ]
        return jsonify({"engines": engine_list})

    @app.route('/api/models', methods=['GET'])
    def list_models():
        engine_id = request.args.get("engine", "v4").lower()
        adapter = _resolve_adapter(engine_id)
        models = adapter.list_available_models()
        return jsonify({
            "engine": engine_id,
            "models": models
        })

    @app.route('/api/games', methods=['GET'])
    def list_games():
        games = replay_service.list_all_games()
        return jsonify({
            "count": len(games),
            "games": games
        })

    @app.route('/api/games/<category>/<filename>', methods=['GET'])
    def get_game(category, filename):
        details = replay_service.get_game_details(category, filename)
        if details is None:
            return jsonify({"error": "Game not found"}), 404
        return jsonify(details)

    @app.route('/api/tournaments', methods=['GET'])
    def list_tournaments():
        tourneys = replay_service.list_v4_tournaments()
        return jsonify({
            "count": len(tourneys),
            "tournaments": tourneys
        })

    @app.route('/api/dictionary/lookup', methods=['GET'])
    def lookup_word():
        word = request.args.get("word", "").strip()
        lexicon = request.args.get("lexicon", "CSW24").strip()
        if not word:
            return jsonify({"error": "Word parameter is required."}), 400
        result = dictionary_service.lookup_word(word, lexicon)
        return jsonify(result)

    @app.route('/api/interactive/move', methods=['POST'])
    def compute_ai_move():
        try:
            data = request.json or {}
            board = data.get('board')
            rack = data.get('rack')
            engine_id = data.get('engine', 'v4')
            model_name = data.get('model', None)
            score_diff = int(data.get('score_diff', 0))
            bag_remaining = int(data.get('bag_remaining', 100))
            lexicon = data.get('lexicon', 'CSW24')

            if board is None or rack is None:
                return jsonify({"error": "Board and rack are required."}), 400

            adapter = _resolve_adapter(engine_id)
            kwargs = {}
            if engine_id in ("magpie", "greedy"):
                kwargs["mode"] = engine_id

            result = adapter.select_move(
                board=board,
                rack=rack,
                score_diff=score_diff,
                bag_remaining=bag_remaining,
                model_name=model_name,
                lexicon=lexicon,
                **kwargs
            )
            return jsonify(result)
        except Exception as e:
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    @app.route('/api/interactive/validate', methods=['POST'])
    def validate_move():
        try:
            data = request.json or {}
            board = data.get('board')
            rack = data.get('rack')
            move = data.get('move')
            engine_id = data.get('engine', 'v4')
            lexicon = data.get('lexicon', 'CSW24')

            if not board or not rack or not move:
                return jsonify({"error": "Board, rack, and move are required."}), 400

            adapter = _resolve_adapter(engine_id)
            result = adapter.validate_move(
                board=board,
                rack=rack,
                move=move,
                lexicon=lexicon
            )
            return jsonify(result)
        except Exception as e:
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    @app.route('/api/compare/position', methods=['POST'])
    def compare_position():
        """Runs side-by-side evaluations across requested engines for the same position."""
        try:
            data = request.json or {}
            board = data.get('board')
            rack = data.get('rack')
            engines = data.get('engines', ['v4', 'magpie'])
            score_diff = int(data.get('score_diff', 0))
            bag_remaining = int(data.get('bag_remaining', 100))
            lexicon = data.get('lexicon', 'CSW24')

            if not board or not rack:
                return jsonify({"error": "Board and rack are required."}), 400

            comparisons = {}
            for eng_id in engines:
                adapter = _resolve_adapter(eng_id)
                kwargs = {}
                if eng_id in ("magpie", "greedy"):
                    kwargs["mode"] = eng_id
                try:
                    res = adapter.select_move(
                        board=board,
                        rack=rack,
                        score_diff=score_diff,
                        bag_remaining=bag_remaining,
                        lexicon=lexicon,
                        **kwargs
                    )
                    comparisons[eng_id] = {
                        "name": adapter.get_name(),
                        "action": res.get("action"),
                        "move": res.get("move"),
                        "points": res.get("points"),
                        "equity": res.get("equity"),
                        "candidates_top3": res.get("candidates", [])[:3]
                    }
                except Exception as ex:
                    comparisons[eng_id] = {"error": str(ex)}

            return jsonify({
                "comparisons": comparisons,
                "lexicon": lexicon
            })
        except Exception as e:
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    # =========================================================================
    # Static Assets & Frontend Serving
    # =========================================================================

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        if path.startswith('api/'):
            return jsonify({"error": f"API route not found: /{path}"}), 404

        if FRONTEND_BUILD_DIR.exists():
            target = FRONTEND_BUILD_DIR / path
            if path and target.exists() and target.is_file():
                return send_from_directory(str(FRONTEND_BUILD_DIR), path)
            index_html = FRONTEND_BUILD_DIR / "index.html"
            if index_html.exists():
                return send_from_directory(str(FRONTEND_BUILD_DIR), "index.html")

        return jsonify({
            "service": "Alphable Visualizer Studio API",
            "status": "online",
            "api_health": "/api/health",
            "message": "Frontend build assets not found. Run 'npm run build' in visualizer/frontend."
        })

    return app


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'

    application = create_app()
    print(f"\nStarting Alphable Visualizer Studio on http://{host}:{port}")
    application.run(host=host, port=port, debug=debug)
