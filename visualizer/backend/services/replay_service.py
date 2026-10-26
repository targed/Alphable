"""
Replay & Tournament Discovery Service for Alphable Visualizer.
Discovers, indexes, and serves game logs and tournament series from V3 and V4.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
V3_DATA_DIR = REPO_ROOT / "Alphable_V3" / "data"
V4_DATA_DIR = REPO_ROOT / "Alphable_V4" / "data"
V4_TOURNAMENTS_DIR = V4_DATA_DIR / "tournaments"


class ReplayService:
    """Discovers and parses game replays and tournament results."""

    def __init__(self):
        self.v3_dirs = {
            "vs_greedy": V3_DATA_DIR / "vs_greedy",
            "vs_random": V3_DATA_DIR / "vs_random",
            "vs_nn": V3_DATA_DIR / "vs_nn",
            "results": V3_DATA_DIR / "results",
            "matches": V3_DATA_DIR / "matches",
        }

    def list_all_games(self) -> List[Dict[str, Any]]:
        """Lists all discovered replay games across V3 and V4."""
        games = []

        # 1. Discover V3 game replays
        for category, directory in self.v3_dirs.items():
            if not directory.exists():
                continue

            for json_file in directory.glob("*.json"):
                if json_file.name.endswith("_summary.json") or json_file.name == "summary.json":
                    continue

                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    turns = data.get("turns")
                    if not isinstance(turns, list):
                        continue

                    player_names = data.get("player_names", ["Player 0", "Player 1"])
                    final_score = data.get("final_score", [0, 0])
                    p0 = final_score[0] if len(final_score) > 0 else 0
                    p1 = final_score[1] if len(final_score) > 1 else 0

                    winner = player_names[0] if p0 > p1 else (player_names[1] if p1 > p0 else "Tie")
                    bingos = sum(1 for t in turns if t.get("action_type") == "PLAY" and len(t.get("word", "") or "") >= 7)

                    games.append({
                        "id": json_file.stem,
                        "filename": json_file.name,
                        "category": category,
                        "engine": "v3",
                        "timestamp": data.get("timestamp", ""),
                        "player_names": player_names,
                        "final_score": final_score,
                        "score_margin": abs(p0 - p1),
                        "winner": winner,
                        "bingos": bingos,
                        "total_turns": len(turns),
                        "metadata": data.get("metadata", {}),
                    })
                except Exception:
                    continue

        # Sort games newest first
        games.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
        return games

    def list_v4_tournaments(self) -> List[Dict[str, Any]]:
        """Lists all tournament runs from Alphable V4."""
        tourneys = []
        if not V4_TOURNAMENTS_DIR.exists():
            return tourneys

        for f in V4_TOURNAMENTS_DIR.glob("run_*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                data["filename"] = f.name
                tourneys.append(data)
            except Exception:
                continue

        tourneys.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
        return tourneys

    def get_game_details(self, category: str, filename: str) -> Optional[Dict[str, Any]]:
        """Fetches full game JSON data by category and filename."""
        safe_name = Path(filename).name

        if category in self.v3_dirs:
            target_file = self.v3_dirs[category] / safe_name
            if target_file.exists():
                try:
                    with open(target_file, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    return None

        if category == "tournaments":
            target_file = V4_TOURNAMENTS_DIR / safe_name
            if target_file.exists():
                try:
                    with open(target_file, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    return None

        return None
