"""
Baseline Adapter for Visualizer Studio: Base MAGPIE and Score Greedy Bots.
"""

import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

V4_DIR = Path(__file__).resolve().parent.parent.parent.parent / "Alphable_V4"
if str(V4_DIR) not in sys.path:
    sys.path.insert(0, str(V4_DIR))

try:
    from alphable_v4.engine.magpie_bindings import MagpieEngine
    from alphable_v4.engine.game_state import GameState
    MAGPIE_AVAILABLE = True
except Exception:
    MAGPIE_AVAILABLE = False

from visualizer.backend.adapters.base import BaseEngineAdapter, sanitize_rack_for_board


class BaselineAdapter(BaseEngineAdapter):
    """Adapter for Classical Base MAGPIE (KLV Static Equity) and Score Greedy bots."""

    def __init__(self):
        self._engines: Dict[str, Any] = {}

    def get_id(self) -> str:
        return "baseline"

    def get_name(self) -> str:
        return "Classical Baselines (Base MAGPIE & Score Greedy)"

    def _get_engine(self, lexicon: str = "CSW24"):
        if lexicon not in self._engines:
            if not MAGPIE_AVAILABLE:
                raise RuntimeError("MAGPIE engine is not available in environment.")
            self._engines[lexicon] = MagpieEngine(lexicon=lexicon)
        return self._engines[lexicon]

    def list_available_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "magpie",
                "name": "Base MAGPIE (KLV Static Equity)",
                "status": "Active",
                "description": "Classical C engine with KLV static equity tables.",
                "verified_wr": "Baseline (50.0%)",
                "size_mb": 0.0,
            },
            {
                "id": "greedy",
                "name": "Score Greedy Bot",
                "status": "Active",
                "description": "Selects the move with the highest immediate board score.",
                "verified_wr": "Novice (<5% vs V4)",
                "size_mb": 0.0,
            }
        ]

    def select_move(
        self,
        board: List[List[Optional[str]]],
        rack: List[str],
        score_diff: int = 0,
        bag_remaining: int = 100,
        model_name: Optional[str] = None,
        lexicon: str = "CSW24",
        mode: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        engine = self._get_engine(lexicon)
        clean_rack = sanitize_rack_for_board(board, [t.upper() for t in rack if t])

        if not clean_rack:
            return {
                "action": "PASS",
                "move": {"word": "", "row": 7, "col": 7, "direction": "Across", "coord": "PASS"},
                "points": 0,
                "equity": 0.0,
                "new_rack": [],
                "candidates": [],
                "metadata": {"game_over": True}
            }


        t0 = time.perf_counter()
        game_state = GameState(
            board=board,
            rack=clean_rack,
            score=0,
            opp_score=-score_diff,
            bag_count=bag_remaining,
            lexicon=lexicon,
        )

        try:
            legal_moves = engine.generate_moves(game_state=game_state, max_candidates=50)
        except Exception:
            legal_moves = []

        bot_mode = mode or model_name or "magpie"
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)

        if not legal_moves:
            return {
                "action": "PASS",
                "move": {"word": "", "row": 7, "col": 7, "direction": "Across", "coord": "PASS"},
                "points": 0,
                "equity": 0.0,
                "new_rack": clean_rack,
                "candidates": [],
                "metadata": {
                    "mode": bot_mode,
                    "method": "No Legal Moves (Pass)",
                    "latency_ms": latency_ms,
                    "num_candidates_evaluated": 0,
                    "stage": "Endgame" if bag_remaining == 0 else "Midgame"
                }
            }

        if bot_mode == "greedy":
            best_move = max(legal_moves, key=lambda m: m.score)
            method_desc = "Score Greedy Search"
        else:
            # Base MAGPIE sorts by static equity by default
            best_move = legal_moves[0]
            method_desc = "Classical KLV Static Equity"

        candidates = []
        for m in legal_moves[:15]:
            candidates.append({
                "word": m.word,
                "row": m.row,
                "col": m.col,
                "direction": m.direction,
                "coord": m.coord_str,
                "points": m.score,
                "leave": "".join(m.leave) if m.leave else "",
                "equity": round(float(m.equity if hasattr(m, "equity") and m.equity is not None else m.score), 2),
                "is_play": m.is_placement,
                "is_exchange": m.is_exchange,
                "is_pass": m.is_pass,
            })

        action = "PLAY" if best_move.is_placement else ("EXCHANGE" if best_move.is_exchange else "PASS")
        new_rack = list(best_move.leave) if best_move.leave is not None else list(clean_rack)

        return {
            "action": action,
            "move": {
                "word": best_move.word,
                "row": best_move.row,
                "col": best_move.col,
                "direction": best_move.direction,
                "coord": best_move.coord_str,
            },
            "points": best_move.score,
            "equity": round(float(best_move.equity if hasattr(best_move, "equity") and best_move.equity is not None else best_move.score), 2),
            "new_rack": new_rack,
            "candidates": candidates,
            "metadata": {
                "mode": bot_mode,
                "lexicon": lexicon,
                "method": method_desc,
                "latency_ms": latency_ms,
                "num_candidates_evaluated": len(legal_moves),
                "static_equity": round(float(best_move.equity if hasattr(best_move, "equity") and best_move.equity is not None else best_move.score), 2),
                "stage": "Opening / Midgame" if bag_remaining > 5 else ("Pre-Endgame Parity" if bag_remaining > 0 else "Endgame"),
            }
        }

    def validate_move(
        self,
        board: List[List[Optional[str]]],
        rack: List[str],
        move: Dict[str, Any],
        lexicon: str = "CSW24"
    ) -> Dict[str, Any]:
        engine = self._get_engine(lexicon)
        clean_rack = sanitize_rack_for_board(board, [t.upper() for t in rack if t])

        game_state = GameState(board=board, rack=clean_rack, lexicon=lexicon)
        try:
            legal_moves = engine.generate_moves(game_state=game_state, max_candidates=500)
        except Exception as e:
            return {
                "valid": False,
                "points": 0,
                "new_rack": clean_rack,
                "error": f"Validation error: {e}"
            }

        target_word = move.get("word", "").upper()
        target_row = int(move.get("row", 0))
        target_col = int(move.get("col", 0))
        target_dir = move.get("direction", "Across").capitalize()

        matched = None
        for m in legal_moves:
            if (m.word.upper() == target_word and
                m.row == target_row and
                m.col == target_col and
                m.direction.capitalize() == target_dir):
                matched = m
                break

        if matched:
            return {
                "valid": True,
                "points": matched.score,
                "word": matched.word,
                "new_rack": list(matched.leave) if matched.leave is not None else [],
                "error": None
            }
        else:
            return {
                "valid": False,
                "points": 0,
                "new_rack": clean_rack,
                "error": f"Move '{target_word}' is not valid."
            }

