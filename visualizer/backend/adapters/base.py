"""
Base Engine Adapter Interface for Alphable Visualizer.
All engine implementations (V4, V3, Base MAGPIE, Greedy) conform to this contract.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseEngineAdapter(ABC):
    """Abstract contract for Scrabble game engine adapters."""

    @abstractmethod
    def get_id(self) -> str:
        """Returns the unique identifier for this engine, e.g. 'v4' or 'v3'."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Returns human-readable name, e.g. 'Alphable V4 (BAMS + MAGPIE)'."""
        pass

    @abstractmethod
    def list_available_models(self) -> List[Dict[str, Any]]:
        """
        Returns list of registered checkpoints/presets:
        [{'id': str, 'name': str, 'description': str, 'verified_wr': str, 'size_mb': float}]
        """
        pass

    @abstractmethod
    def select_move(
        self,
        board: List[List[Optional[str]]],
        rack: List[str],
        score_diff: int = 0,
        bag_remaining: int = 100,
        model_name: Optional[str] = None,
        lexicon: str = "CSW24",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Computes the best move for the given board and rack.
        Returns:
            {
                'action': 'PLAY' | 'PASS' | 'EXCHANGE',
                'move': {'word': str, 'row': int, 'col': int, 'direction': str},
                'points': int,
                'equity': float,
                'new_rack': List[str],
                'candidates': List[Dict[str, Any]],
                'bams_score': Optional[float]
            }
        """
        pass

    @abstractmethod
    def validate_move(
        self,
        board: List[List[Optional[str]]],
        rack: List[str],
        move: Dict[str, Any],
        lexicon: str = "CSW24"
    ) -> Dict[str, Any]:
        """
        Validates whether a move is legal given the current board and rack.
        Returns:
            {
                'valid': bool,
                'points': int,
                'new_rack': List[str],
                'error': Optional[str]
            }
        """
        pass


STANDARD_SCRABBLE_BAG = {
    'A': 9, 'B': 2, 'C': 2, 'D': 4, 'E': 12, 'F': 2, 'G': 3, 'H': 2, 'I': 9,
    'J': 1, 'K': 1, 'L': 4, 'M': 2, 'N': 6, 'O': 8, 'P': 2, 'Q': 1, 'R': 6,
    'S': 4, 'T': 6, 'U': 4, 'V': 2, 'W': 2, 'X': 1, 'Y': 2, 'Z': 1, '?': 2
}


def sanitize_rack_for_board(
    board: List[List[Optional[str]]],
    rack: List[str]
) -> List[str]:
    """
    Ensures that rack tiles do not exceed the remaining tiles in the 100-tile Scrabble bag.
    If a tile in rack has been exhausted by tiles on the board, substitutes it with
    an available blank ('?') or another available letter so that MAGPIE
    does not fail with (error 51) 'rack not available in the bag for player 1'.
    """
    import copy
    counts = copy.copy(STANDARD_SCRABBLE_BAG)

    # 1. Deduct all tiles currently on the board
    for r in range(15):
        for c in range(15):
            tile = board[r][c]
            if tile and tile != ".":
                if tile.islower():
                    # Lowercase indicates designated blank on board
                    counts["?"] = max(0, counts.get("?", 0) - 1)
                else:
                    up = tile.upper()
                    if up in counts:
                        counts[up] = max(0, counts[up] - 1)

    # 2. Reconcile rack against remaining available tiles
    sanitized: List[str] = []
    for t in rack:
        if not t:
            continue
        t_up = t.upper()
        if counts.get(t_up, 0) > 0:
            counts[t_up] -= 1
            sanitized.append(t_up)
        elif counts.get("?", 0) > 0:
            counts["?"] -= 1
            sanitized.append("?")
        else:
            avail = [k for k, v in counts.items() if v > 0 and k != "?"]
            if avail:
                rep = avail[0]
                counts[rep] -= 1
                sanitized.append(rep)
            else:
                sanitized.append(t_up)

    return sanitized

