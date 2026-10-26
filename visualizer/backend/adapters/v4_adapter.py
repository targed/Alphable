"""
Alphable V4 Engine Adapter for Visualizer Studio.
Wraps MAGPIE native C move generator and BAMS search network.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure Alphable_V4 is importable
V4_DIR = Path(__file__).resolve().parent.parent.parent.parent / "Alphable_V4"
if str(V4_DIR) not in sys.path:
    sys.path.insert(0, str(V4_DIR))

try:
    from alphable_v4.engine.magpie_bindings import MagpieEngine
    from alphable_v4.engine.game_state import GameState
    from alphable_v4.engine.move import Move
    from alphable_v4.search.bams import BAMSSearch, BAMSConfig
    from alphable_v4.cli import MODEL_REGISTRY, PRESET_ALIASES, CHECKPOINTS_DIR
    V4_AVAILABLE = True
except Exception as e:
    print(f"Warning: Alphable V4 import error: {e}")
    V4_AVAILABLE = False

from visualizer.backend.adapters.base import BaseEngineAdapter, sanitize_rack_for_board


class V4Adapter(BaseEngineAdapter):
    """Adapter for Alphable V4 (MAGPIE C engine + BAMS Search)."""

    def __init__(self):
        self._engines: Dict[str, Any] = {}
        self._bams_cache: Dict[str, Any] = {}

    def get_id(self) -> str:
        return "v4"

    def get_name(self) -> str:
        return "Alphable V4 (BAMS + Native C MAGPIE)"

    def _get_engine(self, lexicon: str = "CSW24"):
        if lexicon not in self._engines:
            if not V4_AVAILABLE:
                raise RuntimeError("Alphable V4 is not available in environment.")
            self._engines[lexicon] = MagpieEngine(lexicon=lexicon)
        return self._engines[lexicon]

    def list_available_models(self) -> List[Dict[str, Any]]:
        if not V4_AVAILABLE:
            return []

        models = []
        for key, info in MODEL_REGISTRY.items():
            ckpt = info.get("checkpoint_file")
            size_mb = 0.0
            if ckpt:
                full_path = os.path.join(CHECKPOINTS_DIR, ckpt)
                if os.path.exists(full_path):
                    size_mb = round(os.path.getsize(full_path) / (1024 * 1024), 1)

            models.append({
                "id": key,
                "name": info["name"],
                "status": info.get("status", "Active"),
                "description": info.get("description", ""),
                "verified_wr": info.get("verified_wr", "N/A"),
                "checkpoint": ckpt,
                "size_mb": size_mb,
            })
        return models

    def _get_bams(self, model_name: Optional[str], lexicon: str = "CSW24"):
        if not model_name:
            model_name = "latest"

        resolved = PRESET_ALIASES.get(model_name, model_name)
        preset_info = MODEL_REGISTRY.get(resolved, MODEL_REGISTRY["latest"])

        ckpt_file = preset_info.get("checkpoint_file", "v4_value_net_best.pt")
        ckpt_path = os.path.join(CHECKPOINTS_DIR, ckpt_file)

        raw_cfg = preset_info.get("config", {})
        config = BAMSConfig(**raw_cfg)

        cache_key = f"{resolved}_{lexicon}"
        if cache_key not in self._bams_cache:
            engine = self._get_engine(lexicon)
            bams = BAMSSearch.from_checkpoint(
                engine=engine,
                checkpoint_path=ckpt_path if os.path.exists(ckpt_path) else None,
                config=config
            )
            self._bams_cache[cache_key] = bams

        return self._bams_cache[cache_key]

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
        engine = self._get_engine(lexicon)
        # Sanitize rack against available tiles to prevent MAGPIE error 51
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


        game_state = GameState(
            board=board,
            rack=clean_rack,
            score=0,
            opp_score=-score_diff,
            bag_count=bag_remaining,
            lexicon=lexicon,
        )

        try:
            bams = self._get_bams(model_name, lexicon)
            best_move, meta = bams.select_move(game_state)
        except Exception as e:
            # Fallback to direct MAGPIE move generation
            try:
                raw_moves = engine.generate_moves(game_state=game_state, max_candidates=15)
                if raw_moves:
                    best_move = raw_moves[0]
                    meta = {"candidate_moves": raw_moves}
                else:
                    best_move = Move.make_pass()
                    meta = {}
            except Exception:
                best_move = Move.make_pass()
                meta = {}

        # Build candidate moves list
        candidates = []
        raw_candidates = meta.get("candidate_moves", [])
        if not raw_candidates:
            try:
                raw_candidates = engine.generate_moves(game_state=game_state, max_candidates=15)
            except Exception:
                raw_candidates = []

        for c in raw_candidates[:15]:
            c_dict = {
                "word": c.word,
                "row": c.row,
                "col": c.col,
                "direction": c.direction,
                "coord": c.coord_str,
                "points": c.score,
                "leave": "".join(c.leave) if c.leave else "",
                "equity": round(float(c.equity if hasattr(c, "equity") and c.equity is not None else c.score), 2),
                "is_play": c.is_placement,
                "is_exchange": c.is_exchange,
                "is_pass": c.is_pass,
            }
            candidates.append(c_dict)

        action = "PLAY" if best_move.is_placement else ("EXCHANGE" if best_move.is_exchange else "PASS")

        # Compute new rack
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
            "equity": round(float(meta.get("best_bams_score", best_move.score)), 2),
            "bams_score": round(float(meta.get("best_bams_score", best_move.score)), 2),
            "new_rack": new_rack,
            "candidates": candidates,
            "metadata": {
                "model": model_name or "latest",
                "lexicon": lexicon,
                "method": meta.get("method", "bams_mc_rollout_2ply"),
                "latency_ms": round(float(meta.get("latency_ms", 0.0)), 1),
                "num_candidates_evaluated": meta.get("num_candidates_evaluated", len(candidates)),
                "num_samples": meta.get("num_samples", 0),
                "best_bams_score": round(float(meta.get("best_bams_score", best_move.score)), 2),
                "static_equity": round(float(best_move.equity if hasattr(best_move, "equity") and best_move.equity is not None else best_move.score), 2),
                "volatility_used": meta.get("volatility_applied", False),
                "sampled_racks": meta.get("sampled_racks", []),
                "evaluations": meta.get("evaluations", []),
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

        game_state = GameState(
            board=board,
            rack=clean_rack,
            lexicon=lexicon,
        )

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
            new_rack = list(matched.leave) if matched.leave is not None else []
            return {
                "valid": True,
                "points": matched.score,
                "word": matched.word,
                "new_rack": new_rack,
                "error": None
            }
        else:
            return {
                "valid": False,
                "points": 0,
                "new_rack": clean_rack,
                "error": f"Move '{target_word}' at ({target_row},{target_col}) is not legal for rack {''.join(clean_rack)}."
            }

