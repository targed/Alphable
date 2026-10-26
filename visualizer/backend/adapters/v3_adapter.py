"""
Alphable V3 Engine Adapter for Visualizer Studio.
Integrates V3 GADDAG move generator and Macondo ResNet / Transformer ranker.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

V3_DIR = Path(__file__).resolve().parent.parent.parent.parent / "Alphable_V3"
V3_SRC = V3_DIR / "src"
RESOURCES_DIR = V3_DIR / "resources"
MODELS_DIR = V3_DIR / "models"

if V3_SRC.exists() and str(V3_SRC) not in sys.path:
    sys.path.insert(0, str(V3_SRC))

try:
    import torch
    from alphable.core import inference, simulator, structure
    from alphable.training.self_play import evaluate_moves as get_move_evals, choose_move_with_temperature
    V3_AVAILABLE = True
except Exception as e:
    print(f"Warning: Alphable V3 import error: {e}")
    V3_AVAILABLE = False

from visualizer.backend.adapters.base import BaseEngineAdapter


class V3Adapter(BaseEngineAdapter):
    """Adapter for Alphable V3 (GADDAG + Macondo ResNet)."""

    def __init__(self):
        self._engines: Dict[Any, Any] = {}

    def get_id(self) -> str:
        return "v3"

    def get_name(self) -> str:
        return "Alphable V3 (Macondo ResNet / Transformer)"

    def list_available_models(self) -> List[Dict[str, Any]]:
        if not V3_AVAILABLE or not MODELS_DIR.exists():
            return []

        models = []
        for p in sorted(MODELS_DIR.glob("*.pth")):
            size_mb = round(p.stat().st_size / (1024 * 1024), 1)
            models.append({
                "id": p.name,
                "name": p.stem.replace("_", " ").title(),
                "status": "Active",
                "description": f"V3 checkpoint {p.name}",
                "verified_wr": "V3 Baseline (65.5% vs V4)",
                "checkpoint": p.name,
                "size_mb": size_mb,
            })
        return models

    def _get_engine(self, model_name: Optional[str] = None, lexicon: str = "CSW24", value_weight: float = 60.0):
        if not V3_AVAILABLE:
            raise RuntimeError("Alphable V3 is not available in environment.")

        dict_file = f"{lexicon}.txt" if not lexicon.endswith(".txt") else lexicon
        dict_path = RESOURCES_DIR / dict_file
        if not dict_path.exists():
            dict_path = RESOURCES_DIR / "CSW24.txt"

        if not model_name:
            priority = ["alphable_v3_expert.pth", "alphable_v3_macondo_v2.pth", "alphable_best_val_model.pth"]
            for pr in priority:
                if (MODELS_DIR / pr).exists():
                    model_name = pr
                    break

        model_path = (MODELS_DIR / model_name) if model_name else None
        m_str = str(model_path) if (model_path and model_path.exists()) else None

        cache_key = (m_str, str(dict_path), float(value_weight))
        if cache_key not in self._engines:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            eng = inference.AlphableInference(
                model_path=m_str,
                device=device,
                dict_path=str(dict_path),
                value_weight=value_weight,
            )
            self._engines[cache_key] = eng

        return self._engines[cache_key]

    def _normalize_board_for_v3(self, board: List[List[Optional[str]]]) -> List[List[str]]:
        v3_board = []
        for r in range(15):
            row = []
            for c in range(15):
                val = board[r][c]
                row.append("." if (val is None or val == "") else str(val).upper())
            v3_board.append(row)
        return v3_board

    def select_move(
        self,
        board: List[List[Optional[str]]],
        rack: List[str],
        score_diff: int = 0,
        bag_remaining: int = 100,
        model_name: Optional[str] = None,
        lexicon: str = "CSW24",
        value_weight: float = 60.0,
        temperature: float = 0.0,
        **kwargs
    ) -> Dict[str, Any]:
        eng = self._get_engine(model_name=model_name, lexicon=lexicon, value_weight=value_weight)
        v3_board = self._normalize_board_for_v3(board)
        clean_rack = [t.upper() for t in rack if t]

        evals = get_move_evals(
            eng,
            v3_board,
            clean_rack,
            score_diff=score_diff,
            bag_remaining=bag_remaining,
            value_weight=value_weight,
        )

        if not evals:
            return {
                "action": "PASS",
                "move": {"word": "", "row": 0, "col": 0, "direction": "Across", "coord": ""},
                "points": 0,
                "equity": 0.0,
                "new_rack": clean_rack,
                "candidates": []
            }

        # Format candidates
        candidates = []
        for e in evals[:15]:
            m = e["move"]
            dir_str = "Across" if m["dir"].lower().startswith("a") else "Down"
            coord_str = f"{m['row']+1}{chr(ord('A') + m['col'])}"
            candidates.append({
                "word": m["word"],
                "row": m["row"],
                "col": m["col"],
                "direction": dir_str,
                "coord": coord_str,
                "points": e["points"],
                "equity": round(float(e.get("equity", e["points"] + value_weight * e.get("value", 0.0))), 2),
                "value": round(float(e.get("value", 0.0)), 4),
                "leave": "".join(e.get("new_rack", [])),
                "is_play": True,
                "is_exchange": False,
                "is_pass": False,
            })

        chosen = choose_move_with_temperature(evals, temperature=temperature, top_k=3) if temperature > 1e-4 else evals[0]
        if not chosen:
            chosen = evals[0]

        best_m = chosen["move"]
        best_dir = "Across" if best_m["dir"].lower().startswith("a") else "Down"
        best_coord = f"{best_m['row']+1}{chr(ord('A') + best_m['col'])}"

        return {
            "action": "PLAY",
            "move": {
                "word": best_m["word"],
                "row": best_m["row"],
                "col": best_m["col"],
                "direction": best_dir,
                "coord": best_coord,
            },
            "points": chosen["points"],
            "equity": round(float(chosen.get("equity", chosen["points"] + value_weight * chosen.get("value", 0.0))), 2),
            "new_rack": chosen.get("new_rack", []),
            "candidates": candidates,
            "metadata": {
                "engine": "v3",
                "model": model_name or "alphable_v3_expert.pth",
                "value_weight": value_weight
            }
        }

    def validate_move(
        self,
        board: List[List[Optional[str]]],
        rack: List[str],
        move: Dict[str, Any],
        lexicon: str = "CSW24"
    ) -> Dict[str, Any]:
        eng = self._get_engine(lexicon=lexicon)
        v3_board = self._normalize_board_for_v3(board)
        clean_rack = [t.upper() for t in rack if t]

        target_word = move.get("word", "").upper()
        target_row = int(move.get("row", 0))
        target_col = int(move.get("col", 0))
        target_dir = move.get("direction", "Across").capitalize()

        legal_moves = eng.move_gen.generate(v3_board, clean_rack)

        matched = None
        for m in legal_moves:
            if (m["word"].upper() == target_word and
                m["row"] == target_row and
                m["col"] == target_col and
                m["dir"].capitalize() == target_dir):
                matched = m
                break

        if matched:
            _, points, new_rack = simulator.simulate_move(v3_board, matched, clean_rack)
            return {
                "valid": True,
                "points": points,
                "new_rack": new_rack,
                "error": None
            }
        else:
            return {
                "valid": False,
                "points": 0,
                "new_rack": clean_rack,
                "error": f"Move '{target_word}' is not legal for rack {''.join(clean_rack)}."
            }
