"""
Alphable Game Logger - Generates JSON replay files for the Visualizer
Captures complete game state, moves, racks, scores for replay analysis
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional


class GameLogger:
    """Logs Scrabble game moves and states for replay visualization."""
    
    def __init__(self, player0_name: str = "Player 0", player1_name: str = "Player 1"):
        """Initialize a new game log.
        
        Args:
            player0_name: Display name for player 0
            player1_name: Display name for player 1
        """
        self.game_id = str(uuid.uuid4())
        self.timestamp = datetime.now().isoformat()
        self.player_names = [player0_name, player1_name]
        self.turns: List[Dict[str, Any]] = []
        self.final_score: Optional[List[float]] = None
        self.game_metadata: Dict[str, Any] = {}
        
    def log_move(self, 
                 turn_index: int,
                 player: int,
                 action_type: str,
                 action_id: int,
                 word: Optional[str] = None,
                 position: Optional[tuple] = None,
                 direction: Optional[str] = None,
                 score: float = 0.0,
                 rack_before: Optional[List[str]] = None,
                 rack_after: Optional[List[str]] = None,
                 board_state: Optional[str] = None,
                 tiles_in_bag: int = 0,
                 consecutive_passes: int = 0,
                 additional_info: Optional[Dict[str, Any]] = None):
        """Log a single move/turn.
        
        Args:
            turn_index: Sequential turn number (0-indexed)
            player: Player ID (0 or 1)
            action_type: One of "PLAY", "PASS", "EXCHANGE"
            action_id: The numeric action ID from the engine
            word: The word played (if action_type == "PLAY")
            position: (row, col) where word starts (if PLAY)
            direction: "Across" or "Down" (if PLAY)
            score: Points scored this turn
            rack_before: Tiles in hand before the move
            rack_after: Tiles in hand after the move
            board_state: String representation of board (15x15 grid)
            tiles_in_bag: Number of tiles remaining in the bag
            consecutive_passes: Running count of consecutive passes
            additional_info: Any extra metadata (e.g., AI evaluation)
        """
        move_data = {
            "turn_index": turn_index,
            "player": player,
            "action_type": action_type,
            "action_id": action_id,
            "score": score,
            "tiles_in_bag": tiles_in_bag,
            "consecutive_passes": consecutive_passes
        }
        
        if word:
            move_data["word"] = word
        if position:
            move_data["position"] = list(position)  # [row, col]
        if direction:
            move_data["direction"] = direction
        if rack_before:
            move_data["rack_before"] = rack_before
        if rack_after:
            move_data["rack_after"] = rack_after
        if board_state:
            move_data["board_state"] = board_state
        if additional_info:
            move_data.update(additional_info)
            
        self.turns.append(move_data)
    
    def set_final_score(self, scores: List[float]):
        """Set the final game scores.
        
        Args:
            scores: [player0_score, player1_score]
        """
        self.final_score = scores
    
    def set_metadata(self, **kwargs):
        """Add metadata to the game log (e.g., checkpoint number, bot version)."""
        self.game_metadata.update(kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the game log to a dictionary.
        
        Returns:
            Dictionary representation of the full game
        """
        return {
            "game_id": self.game_id,
            "timestamp": self.timestamp,
            "player_names": self.player_names,
            "final_score": self.final_score,
            "metadata": self.game_metadata,
            "turns": self.turns
        }
    
    def save_json(self, filepath: str):
        """Save the game log to a JSON file.
        
        Args:
            filepath: Path where to save the JSON file
        """
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        print(f"Game log saved to: {filepath}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Calculate game statistics.
        
        Returns:
            Dictionary with game statistics
        """
        stats = {
            "total_turns": len(self.turns),
            "player_stats": [{}, {}]
        }
        
        for player_id in [0, 1]:
            player_moves = [t for t in self.turns if t["player"] == player_id]
            plays = [t for t in player_moves if t["action_type"] == "PLAY"]
            passes = [t for t in player_moves if t["action_type"] == "PASS"]
            exchanges = [t for t in player_moves if t["action_type"] == "EXCHANGE"]
            
            # Find bingos (7-letter words = 50 point bonus, so score usually >= 50)
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
                "highest_scoring_move": max((t["score"] for t in plays), default=0)
            }
        
        return stats
