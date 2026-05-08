"""
Alphable V2 Game Logger - JSON replay files for the visualizer.
Schema intentionally matches V1 logger shape for compatibility.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class MoveEntry:
    """Represents a single move/turn in the game."""
    turn_index: int
    player: int
    action_type: str
    action_id: int
    word: Optional[str] = None
    position: Optional[tuple] = None
    direction: Optional[str] = None
    score: float = 0.0
    rack_before: Optional[List[str]] = None
    rack_after: Optional[List[str]] = None
    board_state: Optional[str] = None
    tiles_in_bag: int = 0
    consecutive_passes: int = 0
    additional_info: Optional[Dict[str, Any]] = None


class GameLogger:
    def __init__(self, player0_name: str = "Player 0", player1_name: str = "Player 1"):
        self.game_id = str(uuid.uuid4())
        self.timestamp = datetime.now().isoformat()
        self.player_names = [player0_name, player1_name]
        self.turns: List[Dict[str, Any]] = []
        self.final_score: Optional[List[float]] = None
        self.game_metadata: Dict[str, Any] = {}

    def log_move(self, move: MoveEntry):
        move_data = {
            "turn_index": move.turn_index,
            "player": move.player,
            "action_type": move.action_type,
            "action_id": move.action_id,
            "score": move.score,
            "tiles_in_bag": move.tiles_in_bag,
            "consecutive_passes": move.consecutive_passes,
        }

        if move.word:
            move_data["word"] = move.word
        if move.position:
            move_data["position"] = list(move.position)
        if move.direction:
            move_data["direction"] = move.direction
        if move.rack_before is not None:
            move_data["rack_before"] = move.rack_before
        if move.rack_after is not None:
            move_data["rack_after"] = move.rack_after
        if move.board_state:
            move_data["board_state"] = move.board_state
        if move.additional_info:
            move_data.update(move.additional_info)

        self.turns.append(move_data)

    def set_final_score(self, scores: List[float]):
        self.final_score = scores

    def set_metadata(self, **kwargs):
        self.game_metadata.update(kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "timestamp": self.timestamp,
            "player_names": self.player_names,
            "final_score": self.final_score,
            "metadata": self.game_metadata,
            "turns": self.turns,
        }

    def save_json(self, filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    def get_statistics(self) -> Dict[str, Any]:
        stats = {
            "total_turns": len(self.turns),
            "player_stats": [{}, {}],
        }

        for player_id in [0, 1]:
            player_moves = [t for t in self.turns if t["player"] == player_id]
            plays = [t for t in player_moves if t["action_type"] == "PLAY"]
            passes = [t for t in player_moves if t["action_type"] == "PASS"]
            exchanges = [
                t for t in player_moves if t["action_type"] == "EXCHANGE"]
            bingos = [t for t in plays if len(t.get("word", "")) == 7]

            total_score = sum(t["score"] for t in player_moves)
            avg_score = total_score / len(player_moves) if player_moves else 0

            stats["player_stats"][player_id] = {
                "total_moves": len(player_moves),
                "plays": len(plays),
                "passes": len(passes),
                "exchanges": len(exchanges),
                "bingos": len(bingos),
                "total_score": total_score,
                "average_score_per_move": round(avg_score, 2),
                "highest_scoring_move": max((t["score"] for t in plays), default=0),
            }

        return stats
