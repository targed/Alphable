#!/usr/bin/env python3
"""
Alphable V4 Command Center & Benchmarking Platform.

Provides interactive commands, model management, and tournament runners:
1. models: Catalog and inspect all neural checkpoints, search presets, and benchmark ratings.
2. tournament: Head-to-head match series comparing any model/preset against any opponent or baseline.
   Supports standard alternating seat tournaments and duplicate pair-swapped zero-luck tournaments.
3. analyze: Inspect any Scrabble board position; compare Base MAGPIE vs BAMS AI side-by-side.
4. play: Play an interactive match against Alphable V4 in the terminal.
5. ablation: Quantify exactly what the AI Value Network adds over Base MAGPIE.
"""

from __future__ import annotations
import os
import sys
import time
import json
import argparse
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any, Callable

import numpy as np
import scipy.stats as st
import torch

from alphable_v4.engine.move import Move
from alphable_v4.engine.game_state import GameState, STANDARD_TILE_COUNTS
from alphable_v4.engine.magpie_bindings import MagpieEngine
from alphable_v4.models.value_net import V4ValueNetwork
from alphable_v4.models.belief_net import BayesianRackInference
from alphable_v4.search.bams import BAMSSearch, BAMSConfig
from alphable_v4.platform.eval import GameSimulator, MatchStats, ScrabbleBag


CHECKPOINTS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "models", "checkpoints")
)
DATA_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data")
)
TOURNAMENTS_DIR = os.path.normpath(
    os.path.join(DATA_DIR, "tournaments")
)

# ==============================================================================
# MODEL REGISTRY & CONFIGURATION PRESETS
# ==============================================================================

MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "latest": {
        "name": "Alphable V4 Scaled 2-Ply + Volatility (Champion)",
        "short_name": "V4-Champion",
        "checkpoint_file": "v4_value_net_best.pt",
        "description": "Calibrated 2-Ply Search (K=8, N=14) + Volatility Control (w=0.4) + Supervised Value Net",
        "verified_wr": "56.7% vs Base MAGPIE (+13.1 pts net spread)",
        "status": "⭐ CURRENT PRODUCTION CHAMPION",
        "config": {
            "candidate_beam": 15,
            "num_samples": 24,
            "max_static_deficit": 4.5,
            "opp_penalty_weight": 0.12,
            "value_weight": 4.5,
            "nested_2ply": True,
            "candidate_beam_2ply": 8,
            "samples_2ply": 14,
            "weight_2ply": 0.18,
            "use_volatility_control": True,
            "volatility_weight": 0.4,
            "dynamic_beam": True,
            "use_exact_endgame": True,
            "use_pre_endgame": True,
        },
    },
    "5-frontiers": {
        "name": "Alphable V4 5-Frontiers (1,000-Game Official Champion)",
        "short_name": "5-Frontiers",
        "checkpoint_file": "v4_value_net_best.pt",
        "description": "Official 1,000-Game Tournament Model (540W - 456L - 4D, +9.8 pts spread)",
        "verified_wr": "54.2% vs Base MAGPIE (+9.8 pts spread in 1,000 games)",
        "status": "🏆 VERIFIED 1,000-GAME BENCHMARK CHAMPION",
        "config": {
            "candidate_beam": 15,
            "num_samples": 24,
            "max_static_deficit": 3.5,
            "opp_penalty_weight": 0.12,
            "value_weight": 4.5,
            "nested_2ply": True,
            "candidate_beam_2ply": 6,
            "samples_2ply": 12,
            "weight_2ply": 0.18,
            "use_volatility_control": False,
            "volatility_weight": 0.0,
            "dynamic_beam": True,
            "use_exact_endgame": True,
            "use_pre_endgame": True,
        },
    },
    "rl-gen1": {
        "name": "Alphable V4 RL Gen-1 (Anchored Self-Play Fine-Tuned)",
        "short_name": "RL-Gen1",
        "checkpoint_file": "v4_value_net_rl_gen1.pt",
        "description": "Anchored Self-Play RL Policy Checkpoint + Calibrated Volatility Control",
        "verified_wr": "Self-Play RL Fine-Tuned Policy",
        "status": "🔬 REINFORCEMENT LEARNING POLICY CHECKPOINT",
        "config": {
            "candidate_beam": 15,
            "num_samples": 24,
            "max_static_deficit": 4.5,
            "opp_penalty_weight": 0.12,
            "value_weight": 4.5,
            "nested_2ply": True,
            "candidate_beam_2ply": 8,
            "samples_2ply": 14,
            "weight_2ply": 0.18,
            "use_volatility_control": True,
            "volatility_weight": 0.4,
            "dynamic_beam": True,
            "use_exact_endgame": True,
            "use_pre_endgame": True,
        },
    },
    "scaled": {
        "name": "Alphable V4 Deep Scaled 2-Ply (K=12, N=20)",
        "short_name": "Deep-Scaled",
        "checkpoint_file": "v4_value_net_best.pt",
        "description": "Deep 2-Ply Monte Carlo Lookahead for grandmaster analytical depth",
        "verified_wr": "57.0%+ (Deep Inference Profile)",
        "status": "⚡ HIGH-PRECISION DEEP SEARCH",
        "config": {
            "candidate_beam": 20,
            "num_samples": 32,
            "max_static_deficit": 5.0,
            "opp_penalty_weight": 0.12,
            "value_weight": 4.5,
            "nested_2ply": True,
            "candidate_beam_2ply": 12,
            "samples_2ply": 20,
            "weight_2ply": 0.18,
            "use_volatility_control": True,
            "volatility_weight": 0.4,
            "dynamic_beam": True,
            "use_exact_endgame": True,
            "use_pre_endgame": True,
        },
    },
    "v4-baseline": {
        "name": "Alphable V4 Baseline (1-Ply Search)",
        "short_name": "V4-Baseline",
        "checkpoint_file": "v4_value_net_best.pt",
        "description": "Original V4 1-Ply BAMS Model without 2-ply nesting or volatility control",
        "verified_wr": "52.2% vs Base MAGPIE (+4.3 pts spread in 1,000 games)",
        "status": "📦 V4 BASELINE REFERENCE",
        "config": {
            "candidate_beam": 10,
            "num_samples": 16,
            "max_static_deficit": 4.0,
            "opp_penalty_weight": 0.10,
            "value_weight": 4.0,
            "nested_2ply": False,
            "candidate_beam_2ply": 0,
            "samples_2ply": 0,
            "use_volatility_control": False,
            "volatility_weight": 0.0,
            "dynamic_beam": False,
            "use_exact_endgame": True,
            "use_pre_endgame": False,
        },
    },
    "static-magpie": {
        "name": "Base MAGPIE (KLV Static Equity Top Move)",
        "short_name": "Base-MAGPIE",
        "checkpoint_file": None,
        "description": "Classical C-based Base MAGPIE (Zero Neural Network, static KLV leave tables)",
        "verified_wr": "50.0% (0.0 pts baseline reference)",
        "status": "⚙️ CLASSICAL C SOLVER BASELINE",
        "config": {},
    },
    "magpie-pat": {
        "name": "Base MAGPIE + PAT (Positional Adjustment Term)",
        "short_name": "MAGPIE-PAT",
        "checkpoint_file": None,
        "description": "MAGPIE with native Positional Adjustment Term (-pat CSW24) evaluating opening defense and openness",
        "verified_wr": "52.0%+ vs Base MAGPIE (+2.5 pts spread)",
        "status": "⚙️ POSITIONAL ADJUSTED C SOLVER",
        "config": {},
    },
    "magpie-tuned": {
        "name": "Maximally Tuned Base MAGPIE (PAT + PIMC Simulation + Exact Endgame)",
        "short_name": "MAGPIE-Tuned",
        "checkpoint_file": None,
        "description": "Maximally tuned MAGPIE combining -pat CSW24, PIMC multi-ply simulation lookahead, and exact alpha-beta endgame solving",
        "verified_wr": "58.0%+ vs 1-Ply Static MAGPIE (+15-20 pts ceiling)",
        "status": "⚡ MAXIMALLY TUNED C BENCHMARK ENGINE",
        "config": {},
    },
    "v4-pat": {
        "name": "Alphable V4 Scaled 2-Ply + PAT-Enhanced Candidate Generator",
        "short_name": "V4-Champion-PAT",
        "checkpoint_file": "v4_value_net_best.pt",
        "description": "V4 Champion 2-Ply search powered by MAGPIE -pat candidate generation and threat modeling",
        "verified_wr": "Enhanced 2-Ply Search with PAT Candidate Generator",
        "status": "🌟 GENERATOR-ENHANCED CHAMPION",
        "config": {
            "candidate_beam": 15,
            "num_samples": 24,
            "max_static_deficit": 4.5,
            "opp_penalty_weight": 0.12,
            "value_weight": 4.5,
            "nested_2ply": True,
            "candidate_beam_2ply": 8,
            "samples_2ply": 14,
            "weight_2ply": 0.18,
            "use_volatility_control": True,
            "volatility_weight": 0.4,
            "dynamic_beam": True,
            "use_exact_endgame": True,
            "use_pre_endgame": True,
        },
    },
}

PRESET_ALIASES: Dict[str, str] = {
    "champion": "latest",
    "calibrated": "latest",
    "oracle": "latest",
    "frontiers": "5-frontiers",
    "v5-frontier-v4": "5-frontiers",
    "frontier-v4": "5-frontiers",
    "frontier": "5-frontiers",
    "rl": "rl-gen1",
    "self-play": "rl-gen1",
    "deep-scaled": "scaled",
    "deep": "scaled",
    "baseline": "v4-baseline",
    "magpie": "static-magpie",
    "pat-magpie": "magpie-pat",
    "tuned-magpie": "magpie-tuned",
    "magpie-max": "magpie-tuned",
    "magpie-sim": "magpie-tuned",
    "champion-pat": "v4-pat",
    "latest-pat": "v4-pat",
}


def resolve_preset(name: str) -> Tuple[str, Dict[str, Any]]:
    """Resolves a preset name or alias to its canonical registry entry."""
    norm = name.strip().lower()
    canonical = PRESET_ALIASES.get(norm, norm)
    if canonical in MODEL_REGISTRY:
        return canonical, MODEL_REGISTRY[canonical]
    valid_keys = list(MODEL_REGISTRY.keys()) + list(PRESET_ALIASES.keys())
    raise ValueError(
        f"Unknown model preset or baseline: '{name}'.\n"
        f"Available presets: {list(MODEL_REGISTRY.keys())}\n"
        f"Available aliases: {list(PRESET_ALIASES.keys())}"
    )


def get_shared_engine(lexicon: str = "CSW24") -> MagpieEngine:
    return MagpieEngine(lexicon=lexicon)


def format_board(board: List[List[Optional[str]]]) -> str:
    """Renders a readable 15x15 Scrabble grid with row/col labels."""
    header = "    " + " ".join(f"{chr(ord('A')+c)}" for c in range(15))
    lines = [header, "   +" + "-" * 31 + "+"]
    for r in range(15):
        row_str = f"{r+1:2d} | "
        for c in range(15):
            tile = board[r][c]
            row_str += (tile if tile and tile != "." else ".") + " "
        row_str += "|"
        lines.append(row_str)
    lines.append("   +" + "-" * 31 + "+")
    return "\n".join(lines)


# ==============================================================================
# POLICY BUILDER (Supports Presets, Custom Checkpoints, MAGPIE, & V3)
# ==============================================================================

def build_policy(
    engine: MagpieEngine,
    spec: str = "latest",
    model_path: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None,
    lexicon: str = "CSW24",
    device: Optional[str] = None,
) -> Tuple[Callable[[GameState], Tuple[Move, Dict[str, Any]]], str, str]:
    """
    Builds a move-selection policy callable, a full display name, and a short identifier from either:
    1. A V4 model preset ('latest', '5-frontiers', 'rl-gen1', 'scaled', 'v4-baseline')
    2. A custom model checkpoint path (--model-path)
    3. Classical Base MAGPIE ('magpie' or 'static-magpie')
    4. Alphable V3 Champions ('v3', 'v3-resnet', 'v3-transformer')
    5. Pure score-greedy baseline ('greedy')
    """
    norm = spec.strip().lower()

    # 1. Base MAGPIE
    if norm in ("magpie", "static-magpie"):
        engine.set_pat(None)
        def magpie_policy(state: GameState):
            cands = engine.generate_moves(game_state=state, max_candidates=5)
            if cands:
                return cands[0], {"method": "magpie_static_top"}
            return Move.create_pass(), {"method": "pass"}
        return magpie_policy, "Base MAGPIE (KLV Static)", "Base-MAGPIE"

    # 1b. Base MAGPIE + PAT (Positional Adjustment Term)
    if norm in ("magpie-pat", "pat-magpie"):
        engine.set_pat(lexicon)
        def magpie_pat_policy(state: GameState):
            cands = engine.generate_moves(game_state=state, max_candidates=5)
            if cands:
                return cands[0], {"method": "magpie_pat_top"}
            return Move.create_pass(), {"method": "pass"}
        return magpie_pat_policy, f"Base MAGPIE + PAT ({lexicon})", "MAGPIE-PAT"

    # 1c. Maximally Tuned Base MAGPIE (PAT + PIMC Simulation + Exact Endgame)
    if norm in ("magpie-tuned", "tuned-magpie", "magpie-max", "magpie-sim"):
        engine.set_pat(lexicon)
        sim_iters = 30
        def magpie_tuned_policy(state: GameState):
            # Exact alpha-beta minimax endgame solving when bag is empty
            if state.bag_count == 0 and len(state.opp_rack) > 0:
                cands = engine.generate_moves(game_state=state, max_candidates=20)
                if cands:
                    try:
                        engine.set_cgp(state.to_cgp())
                        raw_eg = engine.solve_endgame()
                        for line in raw_eg.splitlines():
                            line = line.strip()
                            if line and not line.startswith("Endgame") and not line.startswith("Play"):
                                parts = line.split()
                                if len(parts) >= 3:
                                    coord_str = parts[0].upper()
                                    clean_word = parts[1].replace("(", "").replace(")", "").upper()
                                    for c in cands:
                                        if c.coord_str.upper() == coord_str and c.word.upper() == clean_word:
                                            return c, {"method": "magpie_endgame_solve"}
                    except Exception:
                        pass

            # Midgame / Pre-endgame: generate PAT-ranked candidates and simulate
            cands = engine.generate_moves(game_state=state, max_candidates=6)
            if not cands:
                return Move.create_pass(), {"method": "pass"}
            if len(cands) == 1:
                return cands[0], {"method": "magpie_single_candidate"}

            try:
                out_sim = engine.run_command(f"simulate -iterations {sim_iters}")
                for line in out_sim.splitlines():
                    line = line.strip()
                    if not line or ":" not in line:
                        continue
                    idx_part, rest = line.split(":", 1)
                    if not idx_part.strip().isdigit():
                        continue
                    parts = rest.strip().split()
                    if len(parts) >= 4:
                        coord = parts[0]
                        word = parts[1].replace("(", "").replace(")", "")
                        for c in cands:
                            if c.coord_str.upper() == coord.upper() and c.word.upper() == word.upper():
                                return c, {"method": "magpie_sim_top", "sim_line": line}
            except Exception:
                pass

            return cands[0], {"method": "magpie_pat_top"}
        return magpie_tuned_policy, "Maximally Tuned Base MAGPIE (PAT + PIMC + Endgame)", "MAGPIE-Tuned"

    # 2. V3 ResNet Champion (Macondo Distilled, 63 dims)
    if norm in ("v3", "v3-resnet"):
        repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
        v3_src = os.path.join(repo_root, "Alphable_V3", "src")
        sys.path.insert(0, v3_src)
        from alphable.core import inference as v3_inference, simulator as v3_simulator
        v3_dict = os.path.join(repo_root, "Alphable_V3", "resources", "CSW24.txt")
        v3_model = os.path.join(repo_root, "Alphable_V3", "models", "alphable_v3_macondo_v2.pth")
        dev = device or ("cuda" if torch.cuda.is_available() else "cpu")
        v3_eng = v3_inference.AlphableInference(
            model_path=v3_model, dict_path=v3_dict, device=dev, state_vector_size=63
        )

        def v3_policy(state: GameState):
            v3_board = [[(t if t and t != "." else ".") for t in r] for r in state.board]
            score_diff = state.score - state.opp_score
            best_m, val = v3_eng.find_best_move(v3_board, state.rack, score_diff, state.bag_count)
            if not best_m:
                return Move.create_pass(), {"method": "v3_pass"}
            new_board, points, new_rack = v3_simulator.simulate_move(v3_board, best_m, state.rack)
            direction = best_m.get("dir") or best_m.get("direction") or "Across"
            r, c = best_m["row"], best_m["col"]
            word_with_blanks = "".join(
                new_board[r + (i if direction == "Down" else 0)][c + (i if direction == "Across" else 0)]
                for i in range(len(best_m["word"]))
            )
            parsed = Move(row=r, col=c, direction=direction, word=word_with_blanks, score=points, leave="".join(new_rack))
            return parsed, {"method": "v3_macondo_resnet", "val": val}

        return v3_policy, "Alphable V3 (Macondo ResNet Champion)", "V3-ResNet"

    # 3. V3 SmolLM2 Transformer Ranker
    if norm == "v3-transformer":
        repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
        v3_src = os.path.join(repo_root, "Alphable_V3", "src")
        sys.path.insert(0, v3_src)
        from alphable.models.transformer_ranker import SmolLM2CandidateRanker
        from alphable.core import simulator as v3_simulator, structure as v3_structure
        v3_dict = os.path.join(repo_root, "Alphable_V3", "resources", "CSW24.txt")
        t_model_path = os.path.join(repo_root, "Alphable_V3", "models", "transformer_ranker_v2")
        dev = device or ("cuda" if torch.cuda.is_available() else "cpu")
        ranker = SmolLM2CandidateRanker(model_name_or_path=t_model_path, device=dev)
        g = v3_structure.Gaddag.load(v3_dict)
        v3_gen = v3_structure.MoveGenerator(g)

        def v3_trans_policy(state: GameState):
            v3_board = [[(t if t and t != "." else ".") for t in r] for r in state.board]
            v3_moves = v3_gen.generate(v3_board, state.rack)
            if not v3_moves:
                return Move.create_pass(), {"method": "v3_pass"}
            scored = []
            for m in v3_moves[:30]:
                _, pts, nr = v3_simulator.simulate_move(v3_board, m, state.rack)
                scored.append((m, pts, nr))
            scored.sort(key=lambda x: x[1], reverse=True)
            top_cands = [x[0] for x in scored[:8]]
            score_diff = state.score - state.opp_score
            ranked = ranker.rank_candidates(v3_board, state.rack, score_diff, state.bag_count, top_cands)
            best_m = ranked[0][0] if ranked else top_cands[0]
            new_board, points, new_rack = v3_simulator.simulate_move(v3_board, best_m, state.rack)
            direction = best_m.get("dir") or best_m.get("direction") or "Across"
            r, c = best_m["row"], best_m["col"]
            word_with_blanks = "".join(
                new_board[r + (i if direction == "Down" else 0)][c + (i if direction == "Across" else 0)]
                for i in range(len(best_m["word"]))
            )
            parsed = Move(row=r, col=c, direction=direction, word=word_with_blanks, score=points, leave="".join(new_rack))
            return parsed, {"method": "v3_transformer_ranker"}

        return v3_trans_policy, "Alphable V3 (SmolLM2 Transformer)", "V3-Trans"

    # 4. Score-Greedy Baseline
    if norm == "greedy":
        def greedy_policy(state: GameState):
            cands = engine.generate_moves(game_state=state, max_candidates=10)
            if cands:
                best = max(cands, key=lambda c: c.score)
                return best, {"method": "score_greedy"}
            return Move.create_pass(), {"method": "pass"}
        return greedy_policy, "ScoreGreedy Baseline", "Score-Greedy"

    # 5. Alphable V4 BAMS Model (Preset or Custom Checkpoint)
    canonical_key, info = resolve_preset(norm)
    if canonical_key == "v4-pat" or norm in ("v4-pat", "champion-pat", "latest-pat"):
        engine.set_pat(lexicon)
    else:
        engine.set_pat(None)
    cfg_kwargs = dict(info.get("config", {}))

    # Apply command-line overrides
    if overrides:
        for k, v in overrides.items():
            if v is not None:
                cfg_kwargs[k] = v

    if device:
        cfg_kwargs["device"] = device

    conf = BAMSConfig(**cfg_kwargs)

    # Determine checkpoint path
    ckpt_path = model_path
    if not ckpt_path:
        ckpt_file = info.get("checkpoint_file")
        if ckpt_file:
            ckpt_path = os.path.join(CHECKPOINTS_DIR, ckpt_file)

    if not ckpt_path or not os.path.exists(ckpt_path):
        raise FileNotFoundError(f"Checkpoint file not found: {ckpt_path}")

    bams = BAMSSearch.from_checkpoint(engine, ckpt_path, config=conf)
    display_name = f"{info['name']} ({os.path.basename(ckpt_path)})" if model_path else info["name"]
    short_name = info.get("short_name", canonical_key)
    if model_path:
        short_name = os.path.splitext(os.path.basename(model_path))[0]
    return bams.select_move, display_name, short_name


# ==============================================================================
# COMMAND 0: MODELS CATALOG (List all checkpoints, presets, and benchmarks)
# ==============================================================================
def cmd_models(args):
    """Prints a detailed catalog of available models, presets, and benchmarks."""
    print("=" * 95)
    print("                   ALPHABLE V4: NEURAL CHECKPOINTS & SEARCH PRESETS CATALOG")
    print("=" * 95)
    print(f"Checkpoints Directory: {CHECKPOINTS_DIR}\n")

    for key, info in MODEL_REGISTRY.items():
        ckpt_file = info.get("checkpoint_file")
        if ckpt_file:
            full_path = os.path.join(CHECKPOINTS_DIR, ckpt_file)
            size_mb = f"{os.path.getsize(full_path) / (1024*1024):.1f} MB" if os.path.exists(full_path) else "MISSING"
        else:
            full_path = "N/A (C solver)"
            size_mb = "N/A"

        cfg = info.get("config", {})
        samples = cfg.get("num_samples", "N/A")
        beam = cfg.get("candidate_beam", "N/A")
        ply2 = f"Yes (K={cfg.get('candidate_beam_2ply',0)}, N={cfg.get('samples_2ply',0)})" if cfg.get("nested_2ply") else "No (1-Ply)"
        vol = f"w={cfg.get('volatility_weight', 0.0)}" if cfg.get("use_volatility_control") else "Disabled"

        print(f"• PRESET: '{key}'")
        print(f"  Name           : {info['name']}")
        print(f"  Status         : {info['status']}")
        print(f"  Checkpoint     : {ckpt_file} ({size_mb})")
        print(f"  Search Params  : Beam K={beam}, Samples N={samples} | 2-Ply: {ply2} | Volatility: {vol}")
        print(f"  Verified Perf  : {info['verified_wr']}")
        print(f"  Description    : {info['description']}")
        print("-" * 95)

    print("\nALIASES ACCEPTED BY --model OR --opponent:")
    for alias, target in PRESET_ALIASES.items():
        print(f"  --model {alias:<14} -> maps to preset '{target}'")

    print("\nADDITIONAL OPPONENTS SUPPORTED BY --opponent:")
    print("  • magpie        : Base MAGPIE (Classical C KLV static equity top move)")
    print("  • v3-resnet     : Alphable V3 Champion ResNet Model (Macondo Distilled, 63 dims)")
    print("  • v3-transformer: Alphable V3 SmolLM2-135M Autoregressive Transformer Ranker")
    print("  • greedy        : ScoreGreedy Baseline (Max immediate points)")

    print("\nEXAMPLE COMMANDS:")
    print("  # Run the latest champion vs Base MAGPIE for 1,000 games:")
    print("  python cli.py tournament --opponent magpie --games 1000\n")
    print("  # Run the 5-frontiers 1,000-game baseline model:")
    print("  python cli.py tournament --model 5-frontiers --opponent magpie --games 1000\n")
    print("  # Compare the latest model against V4 baseline directly:")
    print("  python cli.py tournament --model latest --opponent v4-baseline --games 50\n")
    print("  # Run a zero-tile-luck duplicate tournament between latest and RL Gen-1:")
    print("  python cli.py tournament --model latest --opponent rl-gen1 --games 30 --duplicate\n")
    print("=" * 95)


# ==============================================================================
# COMMAND 1: ANALYZE (Compare MAGPIE Static vs BAMS AI Side-by-Side)
# ==============================================================================
def cmd_analyze(args):
    """Analyzes a position, showing MAGPIE's choice vs BAMS AI's choice."""
    print("=" * 80)
    print("  ALPHABLE V4 POSITION ANALYZER: BASE MAGPIE vs BAMS AI")
    print("=" * 80)

    engine = get_shared_engine(args.lexicon)

    overrides = {
        "num_samples": args.samples,
        "candidate_beam": args.beam,
        "max_static_deficit": args.max_deficit,
        "volatility_weight": args.volatility_weight,
        "seed": args.seed,
    }
    bams_policy, model_name, _ = build_policy(
        engine,
        spec=args.model,
        model_path=args.model_path,
        overrides=overrides,
        lexicon=args.lexicon,
    )

    # Setup board
    board = [[None for _ in range(15)] for _ in range(15)]
    if args.board_word and args.board_coord:
        row, col, direction = Move.parse_coordinate(args.board_coord)
        word = args.board_word.upper()
        for idx, ch in enumerate(word):
            r = row if direction == "Across" else row + idx
            c = col + idx if direction == "Across" else col
            if 0 <= r < 15 and 0 <= c < 15:
                board[r][c] = ch

    rack = [ch.upper() for ch in args.rack]
    state = GameState(board=board, rack=rack, lexicon=args.lexicon)

    print(f"\nACTIVE MODEL: {model_name}")
    print("\nCURRENT BOARD:")
    print(format_board(board))
    print(f"\nPLAYER RACK: {' '.join(rack)} (Lexicon: {args.lexicon})")

    # 1. Base MAGPIE evaluation (Pure Static KLV)
    t0 = time.perf_counter()
    magpie_cands = engine.generate_moves(game_state=state, max_candidates=args.beam or 10)
    dt_magpie = (time.perf_counter() - t0) * 1000

    if not magpie_cands:
        print("\nNo legal moves found.")
        return

    base_magpie_move = magpie_cands[0]

    # 2. BAMS AI evaluation
    t0 = time.perf_counter()
    bams_move, bams_meta = bams_policy(state)
    dt_bams = (time.perf_counter() - t0) * 1000

    print("\n" + "-" * 80)
    print(f" CANDIDATE EVALUATION BREAKDOWN (MAGPIE KLV vs {model_name})")
    print("-" * 80)
    print(f"{'#':<3} {'Move':<14} {'Pts':<5} {'Leave':<7} {'Static Eq':<11} {'Opp Threat':<12} {'Neural Val':<12} {'BAMS Score':<10}")
    print("-" * 80)

    eval_dict = {f"{e['word']}@{e['row']},{e['col']}": e for e in bams_meta.get("evaluations", [])}

    for idx, c in enumerate(magpie_cands[: args.beam or 10], 1):
        key = f"{c.word}@{c.row},{c.col}"
        meta_e = eval_dict.get(key, {})
        opp_threat = f"{meta_e.get('opp_reply_mean', 0.0):.1f} pts" if meta_e else "pruned"
        val_pred = f"{meta_e.get('value_net_mean', 0.0):+.4f}" if meta_e else "pruned"
        bams_sc = f"{meta_e.get('bams_score', 0.0):.2f}" if meta_e else "pruned"

        move_label = f"{c.coord_str} {c.word}"
        is_magpie_pick = (c == base_magpie_move)
        is_bams_pick = (c.word == bams_move.word and c.row == bams_move.row and c.col == bams_move.col)

        flag = ""
        if is_magpie_pick and is_bams_pick:
            flag = " [AGREED #1]"
        elif is_magpie_pick:
            flag = " [BASE MAGPIE #1]"
        elif is_bams_pick:
            flag = " [AI CHOSEN #1 ★]"

        print(
            f"{idx:<3} {move_label:<14} {c.score:<5} {c.leave:<7} {c.equity:<11.2f} "
            f"{opp_threat:<12} {val_pred:<12} {bams_sc:<10}{flag}"
        )

    print("-" * 80)
    print(f"Base MAGPIE Latency: {dt_magpie:.2f} ms | AI Policy Latency: {dt_bams:.2f} ms")

    # Divergence Analysis
    is_divergent = not (base_magpie_move.word == bams_move.word and base_magpie_move.coord_str == bams_move.coord_str)
    print("\nDECISION SUMMARY:")
    print(f"  • Base MAGPIE Choice : {base_magpie_move.coord_str} {base_magpie_move.word} (Score: {base_magpie_move.score}, Static Equity: {base_magpie_move.equity:.2f})")
    print(f"  • AI Policy Choice   : {bams_move.coord_str} {bams_move.word} (Score: {bams_move.score}, BAMS Score: {bams_meta.get('best_bams_score', 0.0):.2f})")

    if is_divergent:
        print("\n  >>> [AI DIVERGENCE DETECTED] <<<")
        print("  The AI actively overrode Base MAGPIE's #1 move!")
        print(f"  Reason: The AI evaluated Monte Carlo opponent replies, board topology volatility,")
        print("  and neural board control, determining that the alternative move provides superior")
        print("  defensive security or long-term winning probability.")
    else:
        print("\n  >>> [AI & MAGPIE CONSENSUS] <<<")
        print("  Both Base MAGPIE and the AI agree on the optimal play for this rack.")


# ==============================================================================
# COMMAND 2: PLAY (Interactive Match Human vs Alphable V4)
# ==============================================================================
def cmd_play(args):
    """Interactive Scrabble match in terminal."""
    print("=" * 65)
    print("   WELCOME TO ALPHABLE V4 INTERACTIVE SCRABBLE MATCH")
    print("=" * 65)
    print("Rules: Play words using standard notation (e.g., '8H CATS' or 'H8 CATS').")
    print("Commands: 'pass' to pass, 'hint' for AI analysis, 'quit' to exit.\n")

    engine = get_shared_engine(args.lexicon)
    ai_policy, model_name, _ = build_policy(
        engine,
        spec=args.model,
        model_path=args.model_path,
        lexicon=args.lexicon,
    )

    print(f"Opponent AI Engine: {model_name}\n")

    bag = ScrabbleBag(seed=args.seed)
    board = [[None for _ in range(15)] for _ in range(15)]
    human_rack = bag.draw(7)
    ai_rack = bag.draw(7)
    human_score = 0
    ai_score = 0

    turn = 1
    while True:
        print("\n" + "=" * 65)
        print(f"TURN {turn} | SCORE: Human {human_score} - {ai_score} AI | Bag: {bag.count} tiles")
        print("=" * 65)
        print(format_board(board))
        print(f"\nYOUR RACK: {' '.join(human_rack)}")

        # Human Turn
        while True:
            cmd = input("\nEnter your move (e.g. '8H CATS' or 'hint' or 'pass'): ").strip()
            if cmd.lower() in ("quit", "exit"):
                print("Game exited.")
                return

            if cmd.lower() == "hint":
                h_state = GameState(board=board, rack=human_rack, lexicon=args.lexicon)
                top_m, _ = ai_policy(h_state)
                print(f"★ AI Hint: Consider '{top_m.coord_str} {top_m.word}' for {top_m.score} pts (Leave: {top_m.leave})")
                continue

            if cmd.lower() == "pass":
                print("You passed.")
                break

            try:
                parts = cmd.split()
                if len(parts) != 2:
                    print("Invalid format. Use '<COORD> <WORD>', e.g., '8H TRAIN'.")
                    continue
                coord, word = parts[0], parts[1].upper()
                row, col, direction = Move.parse_coordinate(coord)

                # Validate against legal moves
                h_state = GameState(board=board, rack=human_rack, lexicon=args.lexicon)
                legal_moves = engine.generate_moves(game_state=h_state, max_candidates=500)
                matched_move = None
                for lm in legal_moves:
                    if lm.word == word and lm.row == row and lm.col == col:
                        matched_move = lm
                        break

                if not matched_move:
                    print(f"Illegal move: '{cmd}' is not in legal move list for your rack / lexicon {args.lexicon}.")
                    continue

                # Apply human move
                board = h_state.apply_move(matched_move).board
                human_score += matched_move.score
                print(f"✓ Played '{matched_move.word}' for {matched_move.score} points!")

                # Deduct from rack
                if matched_move.leave is not None:
                    human_rack = list(matched_move.leave)
                human_rack.extend(bag.draw(7 - len(human_rack)))
                break
            except Exception as e:
                print(f"Error parsing move: {e}")

        # AI Turn
        print(f"\n{model_name} is thinking...")
        ai_state = GameState(board=board, rack=ai_rack, score=ai_score, opp_score=human_score, lexicon=args.lexicon)
        t0 = time.perf_counter()
        ai_move, ai_meta = ai_policy(ai_state)
        dt = (time.perf_counter() - t0) * 1000

        if ai_move.is_placement:
            board = ai_state.apply_move(ai_move).board
            ai_score += ai_move.score
            print(f"► AI played '{ai_move.coord_str} {ai_move.word}' for {ai_move.score} pts [{dt:.1f}ms]")
            if ai_move.leave is not None:
                ai_rack = list(ai_move.leave)
            ai_rack.extend(bag.draw(7 - len(ai_rack)))
        else:
            print(f"► AI passed. [{dt:.1f}ms]")

        turn += 1
        if bag.count == 0 and (len(human_rack) == 0 or len(ai_rack) == 0):
            print("\n*** GAME OVER: Tile Bag Empty & Rack Cleared ***")
            print(f"FINAL SCORE: Human {human_score} - {ai_score} AI")
            break


# ==============================================================================
# COMMAND 3: TOURNAMENT (Flexible Model vs Baseline or Model vs Model)
# ==============================================================================
def cmd_tournament(args):
    """Runs a multi-game tournament series comparing any model/preset against an opponent."""
    engine = get_shared_engine(args.lexicon)

    # 1. Build Player 1 Policy
    overrides_p1 = {
        "num_samples": args.samples,
        "candidate_beam": args.beam,
        "volatility_weight": args.volatility_weight,
    }
    p1_policy, p1_name, p1_short = build_policy(
        engine,
        spec=args.model,
        model_path=args.model_path,
        overrides=overrides_p1,
        lexicon=args.lexicon,
        device=args.device,
    )

    # 2. Build Player 2 (Opponent) Policy
    p2_policy, p2_name, p2_short = build_policy(
        engine,
        spec=args.opponent,
        model_path=args.opponent_model_path,
        overrides=None,
        lexicon=args.lexicon,
        device=args.device,
    )

    print("=" * 75)
    print(f"   ALPHABLE V4 TOURNAMENT: {p1_name}")
    print(f"                      vs   {p2_name}")
    print(f"   Total Games: {args.games} | Duplicate Mode: {'YES (Pair-Swapped)' if args.duplicate else 'NO (Alternating Seats)'}")
    print("=" * 75)

    sim = GameSimulator(engine, lexicon=args.lexicon)

    # DUPLICATE MATCH MODE
    if args.duplicate:
        num_pairs = max(1, args.games // 2)
        total_games = num_pairs * 2
        p1_pair_wins = 0
        p2_pair_wins = 0
        pair_draws = 0
        p1_total_scores = []
        p2_total_scores = []
        p1_all_bingos = 0
        p2_all_bingos = 0
        pair_diffs = []
        pair_records = []

        t_start = time.time()
        print(f"\nRunning {num_pairs} duplicate match pairs ({total_games} total games)...\n")

        for p in range(num_pairs):
            seed = 1000 + p * 31

            # Game A: P1 as Player 1, P2 as Player 2
            res_a = sim.play_game(p1_policy, p2_policy, seed=seed)
            # Game B: P2 as Player 1, P1 as Player 2 with IDENTICAL SEED
            res_b = sim.play_game(p2_policy, p1_policy, seed=seed)

            score_p1_pair = res_a["p1_score"] + res_b["p2_score"]
            score_p2_pair = res_a["p2_score"] + res_b["p1_score"]

            bingos_p1_pair = res_a["p1_bingos"] + res_b["p2_bingos"]
            bingos_p2_pair = res_a["p2_bingos"] + res_b["p1_bingos"]

            p1_total_scores.append(score_p1_pair / 2.0)
            p2_total_scores.append(score_p2_pair / 2.0)
            p1_all_bingos += bingos_p1_pair
            p2_all_bingos += bingos_p2_pair

            pair_diff = score_p1_pair - score_p2_pair
            pair_diffs.append(pair_diff)

            if pair_diff > 0:
                p1_pair_wins += 1
                verdict = f"{p1_short} WON MATCH"
            elif pair_diff < 0:
                p2_pair_wins += 1
                verdict = f"{p2_short} WON MATCH"
            else:
                pair_draws += 1
                verdict = "MATCH TIED"

            # Calculate per-phase spread for this duplicate pair
            phases = ["opening", "midgame", "pre_endgame", "endgame"]
            pair_phase_spreads = {}
            for ph in phases:
                p1_ph = res_a.get("phase_scores", {}).get(ph, {}).get("p1", 0) + res_b.get("phase_scores", {}).get(ph, {}).get("p2", 0)
                p2_ph = res_a.get("phase_scores", {}).get(ph, {}).get("p2", 0) + res_b.get("phase_scores", {}).get(ph, {}).get("p1", 0)
                pair_phase_spreads[ph] = (p1_ph - p2_ph) / 2.0

            pair_records.append({
                "pair": p + 1,
                "seed": seed,
                "p1_gameA_score": res_a["p1_score"],
                "p1_gameB_score": res_b["p2_score"],
                "p1_pair_total": score_p1_pair,
                "p2_gameA_score": res_a["p2_score"],
                "p2_gameB_score": res_b["p1_score"],
                "p2_pair_total": score_p2_pair,
                "net_spread": pair_diff,
                "phase_spreads": pair_phase_spreads,
                "verdict": verdict,
            })

            print(
                f"Pair {p+1:02d}/{num_pairs:02d} [Seed {seed}]: "
                f"{p1_short} {res_a['p1_score']}+{res_b['p2_score']}={score_p1_pair} pts vs "
                f"{p2_short} {res_a['p2_score']}+{res_b['p1_score']}={score_p2_pair} pts | "
                f"Net: {pair_diff:+d} pts | {verdict}"
            )

        dt = time.time() - t_start
        pair_win_pct = (p1_pair_wins + 0.5 * pair_draws) / num_pairs * 100

        pair_diffs_per_game = np.array(pair_diffs) / 2.0
        mean_dup_spread = float(np.mean(pair_diffs_per_game))
        std_dup_spread = float(np.std(pair_diffs_per_game, ddof=1)) if len(pair_diffs_per_game) > 1 else 0.0
        se_dup_spread = std_dup_spread / np.sqrt(num_pairs) if num_pairs > 0 else 0.0
        ci95_dup_spread = 1.96 * se_dup_spread
        t_dup = mean_dup_spread / se_dup_spread if se_dup_spread > 0 else 0.0
        p_val_dup = float(st.t.sf(abs(t_dup), df=max(1, num_pairs - 1)) * 2.0)

        p_win_dup = (p1_pair_wins + 0.5 * pair_draws) / num_pairs
        se_win_dup = np.sqrt(p_win_dup * (1.0 - p_win_dup) / num_pairs) if num_pairs > 0 else 0.0
        ci95_win_dup = 1.96 * se_win_dup * 100.0

        if p_val_dup < 0.01:
            sig_dup = "Statistically Significant (p < 0.01, Strong Edge)"
        elif p_val_dup < 0.05:
            sig_dup = "Statistically Significant (p < 0.05, Confirmed Edge)"
        else:
            sig_dup = "Not Yet Statistically Significant (p >= 0.05)"

        print("\n" + "=" * 75)
        print(" DUPLICATE TOURNAMENT RESULTS SUMMARY (ZERO TILE LUCK)")
        print("=" * 75)
        print(f"Matchup: {p1_name} vs {p2_name}")
        print(f"Total Games Played: {total_games} ({num_pairs} duplicate pairs) in {dt:.1f}s ({dt/total_games:.2f}s/game)")
        print(f"Match Pair Record : {p1_pair_wins}W - {p2_pair_wins}L - {pair_draws}D ({pair_win_pct:.1f}% Match Win Rate for {p1_short})")
        print(f"{p1_short} Mean Score: {np.mean(p1_total_scores):.1f} pts (Bingos/Game: {p1_all_bingos/total_games:.2f})")
        print(f"{p2_short} Mean Score: {np.mean(p2_total_scores):.1f} pts (Bingos/Game: {p2_all_bingos/total_games:.2f})")
        print(f"Net Score Spread  : {mean_dup_spread:+.1f} pts per game in favor of {p1_short}")
        phases = ["opening", "midgame", "pre_endgame", "endgame"]
        phase_means = {
            ph: float(np.mean([r.get("phase_spreads", {}).get(ph, 0.0) for r in pair_records]))
            for ph in phases
        }
        print(f"Phase Net Spreads : Opening {phase_means['opening']:+.1f} | Midgame {phase_means['midgame']:+.1f} | Pre-End {phase_means['pre_endgame']:+.1f} | End {phase_means['endgame']:+.1f} pts/game")
        print("-" * 75)
        print(" STATISTICAL SIGNIFICANCE (ZERO TILE LUCK TEST)")
        print("-" * 75)
        print(f"Match Win Rate (95% CI) : {pair_win_pct:.1f}% ± {ci95_win_dup:.1f}% [{pair_win_pct - ci95_win_dup:.1f}% — {pair_win_pct + ci95_win_dup:.1f}%]")
        print(f"Net Spread (95% CI)     : {mean_dup_spread:+.1f} ± {ci95_dup_spread:.1f} pts/game [{mean_dup_spread - ci95_dup_spread:+.1f} — {mean_dup_spread + ci95_dup_spread:+.1f} pts]")
        print(f"Paired t-Test (H0: Δ=0) : t = {t_dup:.2f}, p-value = {p_val_dup:.4f} ({sig_dup})")
        print("Luck Cancellation       : Tile draw noise eliminated via paired symmetric seeds.")
        print("=" * 75)

        if not getattr(args, "no_save", False):
            p1_ckpt = getattr(args, "model_path", None) or MODEL_REGISTRY.get(args.model, {}).get("checkpoint_file")
            p2_ckpt = getattr(args, "opponent_model_path", None) or MODEL_REGISTRY.get(args.opponent, {}).get("checkpoint_file")
            save_tournament_telemetry(
                mode="duplicate",
                total_games=total_games,
                duplicate_pairs=num_pairs,
                duration_seconds=dt,
                p1_name=p1_name,
                p1_short=p1_short,
                p1_spec=args.model,
                p1_ckpt=p1_ckpt,
                p1_mean=float(np.mean(p1_total_scores)),
                p1_bingos_per_game=p1_all_bingos / total_games,
                p1_wins=p1_pair_wins,
                p2_name=p2_name,
                p2_short=p2_short,
                p2_spec=args.opponent,
                p2_ckpt=p2_ckpt,
                p2_mean=float(np.mean(p2_total_scores)),
                p2_bingos_per_game=p2_all_bingos / total_games,
                p2_wins=p2_pair_wins,
                draws=pair_draws,
                win_pct=pair_win_pct,
                ci95_win=ci95_win_dup,
                mean_spread=mean_dup_spread,
                ci95_spread=ci95_dup_spread,
                t_stat=t_dup,
                p_val=p_val_dup,
                sig_verdict=sig_dup,
                lexicon=args.lexicon,
                tag=args.tag,
                records=pair_records,
            )
        return

    # STANDARD ALTERNATING SEATS MODE
    p1_wins = 0
    p2_wins = 0
    draws = 0
    p1_scores = []
    p2_scores = []
    p1_bingos = 0
    p2_bingos = 0
    game_margins = []
    game_records = []

    t_start = time.time()
    for g in range(args.games):
        seed = 1000 + g * 31
        p1_is_first = (g % 2 == 0)

        first_pol = p1_policy if p1_is_first else p2_policy
        second_pol = p2_policy if p1_is_first else p1_policy

        res = sim.play_game(first_pol, second_pol, seed=seed)

        if p1_is_first:
            s1, s2 = res["p1_score"], res["p2_score"]
            b1, b2 = res["p1_bingos"], res["p2_bingos"]
            p1_won = (res["winner"] == 1)
            p2_won = (res["winner"] == 2)
        else:
            s1, s2 = res["p2_score"], res["p1_score"]
            b1, b2 = res["p2_bingos"], res["p1_bingos"]
            p1_won = (res["winner"] == 2)
            p2_won = (res["winner"] == 1)

        p1_scores.append(s1)
        p2_scores.append(s2)
        p1_bingos += b1
        p2_bingos += b2

        margin = s1 - s2
        game_margins.append(margin)

        if p1_won:
            p1_wins += 1
            verdict = f"{p1_short} WON ✓"
            winner_label = p1_short
        elif p2_won:
            p2_wins += 1
            verdict = f"{p2_short} WON"
            winner_label = p2_short
        else:
            draws += 1
            verdict = "DRAW"
            winner_label = "DRAW"

        # Phase scores mapped to Model 1 / Model 2
        phase_scores_m1_m2 = {}
        for ph in ["opening", "midgame", "pre_endgame", "endgame"]:
            if "phase_scores" in res:
                m1_ph = res["phase_scores"][ph]["p1"] if p1_is_first else res["phase_scores"][ph]["p2"]
                m2_ph = res["phase_scores"][ph]["p2"] if p1_is_first else res["phase_scores"][ph]["p1"]
                phase_scores_m1_m2[ph] = {"p1": m1_ph, "p2": m2_ph, "margin": m1_ph - m2_ph}

        game_records.append({
            "game": g + 1,
            "seed": seed,
            "p1_seat": "P1" if p1_is_first else "P2",
            "p1_score": s1,
            "p2_score": s2,
            "p1_bingos": b1,
            "p2_bingos": b2,
            "margin": margin,
            "phase_scores": phase_scores_m1_m2,
            "winner": winner_label,
        })

        print(
            f"Game {g+1:02d}/{args.games:02d} [{p1_short} {'P1' if p1_is_first else 'P2'}]: "
            f"{p1_short} {s1} - {s2} {p2_short} | {verdict} | Bingos: {b1}-{b2}"
        )

    dt = time.time() - t_start
    win_pct = (p1_wins + 0.5 * draws) / args.games * 100

    margins = np.array(game_margins)
    mean_margin = float(np.mean(margins))
    std_margin = float(np.std(margins, ddof=1)) if len(margins) > 1 else 0.0
    se_margin = std_margin / np.sqrt(len(margins)) if len(margins) > 0 else 0.0
    ci95_margin = 1.96 * se_margin

    p_val_game = (p1_wins + 0.5 * draws) / args.games
    se_p = np.sqrt(p_val_game * (1.0 - p_val_game) / args.games) if args.games > 0 else 0.0
    ci95_p = 1.96 * se_p * 100.0

    t_stat = mean_margin / se_margin if se_margin > 0 else 0.0
    p_val = float(st.t.sf(abs(t_stat), df=max(1, len(margins) - 1)) * 2.0)

    if p_val < 0.01:
        sig_std = "Statistically Significant (p < 0.01, Strong Edge)"
    elif p_val < 0.05:
        sig_std = "Statistically Significant (p < 0.05, Confirmed Edge)"
    else:
        sig_std = "Not Yet Statistically Significant (p >= 0.05)"

    print("\n" + "=" * 75)
    print(" TOURNAMENT RESULTS SUMMARY")
    print("=" * 75)
    print(f"Matchup: {p1_name} vs {p2_name}")
    print(f"Total Games Played: {args.games} in {dt:.1f}s ({dt/args.games:.2f}s/game)")
    print(f"Record            : {p1_wins}W - {p2_wins}L - {draws}D ({win_pct:.1f}% Win Rate for {p1_short})")
    print(f"{p1_short} Mean Score: {np.mean(p1_scores):.1f} pts (Bingos/Game: {p1_bingos/args.games:.2f})")
    print(f"{p2_short} Mean Score: {np.mean(p2_scores):.1f} pts (Bingos/Game: {p2_bingos/args.games:.2f})")
    print(f"Score Differential: {mean_margin:+.1f} pts in favor of {p1_short}")
    print("-" * 75)
    print(" STATISTICAL SIGNIFICANCE & ERROR BARS")
    print("-" * 75)
    print(f"Win Rate (95% CI)       : {win_pct:.1f}% ± {ci95_p:.1f}% [{win_pct - ci95_p:.1f}% — {win_pct + ci95_p:.1f}%]")
    print(f"Net Spread (95% CI)     : {mean_margin:+.1f} ± {ci95_margin:.1f} pts/game [{mean_margin - ci95_margin:+.1f} — {mean_margin + ci95_margin:+.1f} pts]")
    print(f"Paired t-Test (H0: Δ=0) : t = {t_stat:.2f}, p-value = {p_val:.4f} ({sig_std})")
    print(f"Bernoulli Tile Noise    : 1 SD of 1,000-game tile noise is ±{se_p*100:.2f}%. Run-to-run")
    print(f"                          variations within ±{ci95_p:.1f}% are normal statistical noise.")
    print("=" * 75)

    if not getattr(args, "no_save", False):
        p1_ckpt = getattr(args, "model_path", None) or MODEL_REGISTRY.get(args.model, {}).get("checkpoint_file")
        p2_ckpt = getattr(args, "opponent_model_path", None) or MODEL_REGISTRY.get(args.opponent, {}).get("checkpoint_file")
        save_tournament_telemetry(
            mode="standard",
            total_games=args.games,
            duplicate_pairs=None,
            duration_seconds=dt,
            p1_name=p1_name,
            p1_short=p1_short,
            p1_spec=args.model,
            p1_ckpt=p1_ckpt,
            p1_mean=float(np.mean(p1_scores)),
            p1_bingos_per_game=p1_bingos / args.games,
            p1_wins=p1_wins,
            p2_name=p2_name,
            p2_short=p2_short,
            p2_spec=args.opponent,
            p2_ckpt=p2_ckpt,
            p2_mean=float(np.mean(p2_scores)),
            p2_bingos_per_game=p2_bingos / args.games,
            p2_wins=p2_wins,
            draws=draws,
            win_pct=win_pct,
            ci95_win=ci95_p,
            mean_spread=mean_margin,
            ci95_spread=ci95_margin,
            t_stat=t_stat,
            p_val=p_val,
            sig_verdict=sig_std,
            lexicon=args.lexicon,
            tag=args.tag,
            records=game_records,
        )


# ==============================================================================
# COMMAND 4: ABLATION (Neural Value Network ON vs OFF)
# ==============================================================================
def cmd_ablation(args):
    """
    Quantifies the exact impact of the AI Value Network by comparing:
    - Condition A: BAMS Search WITH Neural Value Network
    - Condition B: BAMS Search WITHOUT Neural Value Network (Static heuristic only)
    """
    print("=" * 75)
    print(f"   ALPHABLE V4 ABLATION EXPERIMENT: NEURAL NETWORK ON vs OFF")
    print("=" * 75)
    print("This experiment proves whether the AI Neural Value Network makes an")
    print("empirical difference over identical seeds compared to static search alone.\n")

    engine = get_shared_engine(args.lexicon)

    # Condition A: Neural Active
    bams_neural, neural_name, _ = build_policy(engine, spec=args.model, lexicon=args.lexicon)

    # Condition B: Ablated (No Neural Net)
    bams_ablated = BAMSSearch(
        engine,
        value_net=None,
        config=BAMSConfig(num_samples=16, candidate_beam=10, max_static_deficit=4.0),
    )

    sim = GameSimulator(engine, lexicon=args.lexicon)

    neural_wins = 0
    ablated_wins = 0
    draws = 0
    neural_scores = []
    ablated_scores = []

    for g in range(args.games):
        seed = 777 + g * 13
        neural_is_p1 = (g % 2 == 0)

        p1_pol = bams_neural if neural_is_p1 else (lambda s: bams_ablated.select_move(s))
        p2_pol = (lambda s: bams_ablated.select_move(s)) if neural_is_p1 else bams_neural

        res = sim.play_game(p1_pol, p2_pol, seed=seed)

        n_sc = res["p1_score"] if neural_is_p1 else res["p2_score"]
        a_sc = res["p2_score"] if neural_is_p1 else res["p1_score"]
        neural_scores.append(n_sc)
        ablated_scores.append(a_sc)

        n_won = (res["winner"] == 1 and neural_is_p1) or (res["winner"] == 2 and not neural_is_p1)
        a_won = (res["winner"] == 2 and neural_is_p1) or (res["winner"] == 1 and not neural_is_p1)

        if n_won:
            neural_wins += 1
            res_str = "NEURAL (AI) WON"
        elif a_won:
            ablated_wins += 1
            res_str = "Ablated (No AI) Won"
        else:
            draws += 1
            res_str = "Draw"

        print(f"Game {g+1:02d}/{args.games:02d}: Neural {n_sc} - {a_sc} No-Neural | {res_str}")

    win_rate = (neural_wins + 0.5 * draws) / args.games * 100
    print("\n" + "=" * 75)
    print(" ABLATION FINDINGS")
    print("=" * 75)
    print(f"Neural (AI) Win Rate : {win_rate:.1f}% ({neural_wins}W - {ablated_wins}L - {draws}D)")
    print(f"Neural Mean Score    : {np.mean(neural_scores):.1f} pts")
    print(f"No-Neural Mean Score : {np.mean(ablated_scores):.1f} pts")
    print(f"Net AI Impact        : {np.mean(neural_scores) - np.mean(ablated_scores):+.1f} points per game")
    print("=" * 75)


# ==============================================================================
# TELEMETRY PERSISTENCE & HISTORY MANAGEMENT
# ==============================================================================
def save_tournament_telemetry(
    mode: str,
    total_games: int,
    duplicate_pairs: Optional[int],
    duration_seconds: float,
    p1_name: str,
    p1_short: str,
    p1_spec: str,
    p1_ckpt: Optional[str],
    p1_mean: float,
    p1_bingos_per_game: float,
    p1_wins: int,
    p2_name: str,
    p2_short: str,
    p2_spec: str,
    p2_ckpt: Optional[str],
    p2_mean: float,
    p2_bingos_per_game: float,
    p2_wins: int,
    draws: int,
    win_pct: float,
    ci95_win: float,
    mean_spread: float,
    ci95_spread: float,
    t_stat: float,
    p_val: float,
    sig_verdict: str,
    lexicon: str,
    tag: Optional[str] = None,
    records: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Saves complete tournament telemetry JSON and appends an entry to the history ledger."""
    os.makedirs(TOURNAMENTS_DIR, exist_ok=True)
    timestamp_dt = datetime.now()
    timestamp_str = timestamp_dt.strftime("%Y%m%d_%H%M%S")
    iso_ts = timestamp_dt.isoformat(timespec="seconds")
    run_id = f"run_{timestamp_str}"

    mode_tag = "dup" if mode == "duplicate" else "std"
    clean_p1 = p1_short.replace(" ", "-").replace("/", "-")
    clean_p2 = p2_short.replace(" ", "-").replace("/", "-")
    tag_clean = f"_{tag.replace(' ', '_')}" if tag else ""
    filename = f"{run_id}_{clean_p1}_vs_{clean_p2}_{total_games}g_{mode_tag}{tag_clean}.json"
    full_path = os.path.join(TOURNAMENTS_DIR, filename)

    run_data = {
        "run_id": run_id,
        "timestamp": iso_ts,
        "mode": mode,
        "tag": tag or f"{total_games}g-{mode_tag}",
        "lexicon": lexicon,
        "total_games": total_games,
        "duplicate_pairs": duplicate_pairs,
        "duration_seconds": round(duration_seconds, 1),
        "seconds_per_game": round(duration_seconds / total_games, 2) if total_games > 0 else 0.0,
        "player1": {
            "name": p1_name,
            "short_name": p1_short,
            "spec": p1_spec,
            "checkpoint_file": p1_ckpt,
            "mean_score": round(p1_mean, 1),
            "bingos_per_game": round(p1_bingos_per_game, 2),
            "wins": p1_wins,
        },
        "player2": {
            "name": p2_name,
            "short_name": p2_short,
            "spec": p2_spec,
            "checkpoint_file": p2_ckpt,
            "mean_score": round(p2_mean, 1),
            "bingos_per_game": round(p2_bingos_per_game, 2),
            "wins": p2_wins,
        },
        "draws": draws,
        "win_rate": {
            "percentage": round(win_pct, 1),
            "ci95": round(ci95_win, 1),
            "ci_lower": round(win_pct - ci95_win, 1),
            "ci_upper": round(win_pct + ci95_win, 1),
        },
        "net_spread": {
            "mean": round(mean_spread, 1),
            "ci95": round(ci95_spread, 1),
            "ci_lower": round(mean_spread - ci95_spread, 1),
            "ci_upper": round(mean_spread + ci95_spread, 1),
        },
        "significance": {
            "t_statistic": round(t_stat, 2),
            "p_value": round(p_val, 4),
            "verdict": sig_verdict,
            "hypothesis": "H0: Δ=0 vs H1: Δ!=0",
        },
        "details": records or [],
    }

    if records and any("phase_spreads" in r for r in records):
        phases = ["opening", "midgame", "pre_endgame", "endgame"]
        phase_summary = {}
        for ph in phases:
            vals = [r["phase_spreads"][ph] for r in records if "phase_spreads" in r and ph in r["phase_spreads"]]
            if vals:
                mean_val = float(np.mean(vals))
                se_val = float(np.std(vals, ddof=1) / np.sqrt(len(vals))) if len(vals) > 1 else 0.0
                phase_summary[ph] = {
                    "mean_spread": round(mean_val, 2),
                    "se": round(se_val, 2),
                    "ci95": round(1.96 * se_val, 2),
                }
        run_data["phase_summary"] = phase_summary

    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(run_data, f, indent=2)

    # Append to master tournament history ledger
    ledger_path = os.path.join(TOURNAMENTS_DIR, "tournament_history.jsonl")
    ledger_entry = {
        "run_id": run_id,
        "timestamp": iso_ts,
        "mode": mode,
        "tag": tag or f"{total_games}g-{mode_tag}",
        "lexicon": lexicon,
        "total_games": total_games,
        "duplicate_pairs": duplicate_pairs,
        "duration_seconds": round(duration_seconds, 1),
        "player1": {
            "name": p1_name,
            "short_name": p1_short,
            "spec": p1_spec,
            "mean_score": round(p1_mean, 1),
            "bingos_per_game": round(p1_bingos_per_game, 2),
            "wins": p1_wins,
        },
        "player2": {
            "name": p2_name,
            "short_name": p2_short,
            "spec": p2_spec,
            "mean_score": round(p2_mean, 1),
            "bingos_per_game": round(p2_bingos_per_game, 2),
            "wins": p2_wins,
        },
        "draws": draws,
        "win_rate": {"percentage": round(win_pct, 1), "ci95": round(ci95_win, 1)},
        "net_spread": {"mean": round(mean_spread, 1), "ci95": round(ci95_spread, 1)},
        "significance": {
            "t_statistic": round(t_stat, 2),
            "p_value": round(p_val, 4),
            "verdict": sig_verdict,
        },
        "file": filename,
    }
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(ledger_entry) + "\n")

    print("\n" + "-" * 75)
    print(" PERSISTED TELEMETRY & LEDGER RECORD")
    print("-" * 75)
    print(f" ✓ Run ID        : {run_id}")
    print(f" ✓ Telemetry File: data/tournaments/{filename}")
    print(f" ✓ History Ledger: data/tournaments/tournament_history.jsonl")
    print(f" Tip: View past runs with 'python cli.py history'")
    print(f"      Compare runs with   'python cli.py history --compare <run1> <run2>'")
    print("=" * 75)
    return full_path


def find_run_file(run_id_or_path: str) -> Optional[str]:
    """Finds a run JSON file by path, exact filename, run_id, or prefix."""
    if os.path.isfile(run_id_or_path):
        return run_id_or_path

    direct_in_dir = os.path.join(TOURNAMENTS_DIR, run_id_or_path)
    if os.path.isfile(direct_in_dir):
        return direct_in_dir
    if not run_id_or_path.endswith(".json") and os.path.isfile(direct_in_dir + ".json"):
        return direct_in_dir + ".json"

    if os.path.isdir(TOURNAMENTS_DIR):
        candidates = []
        for f in os.listdir(TOURNAMENTS_DIR):
            if f.endswith(".json") and f != "tournament_history.json":
                if run_id_or_path in f:
                    candidates.append(os.path.join(TOURNAMENTS_DIR, f))
        if len(candidates) == 1:
            return candidates[0]
        elif len(candidates) > 1:
            for c in candidates:
                if os.path.basename(c).startswith(run_id_or_path):
                    return c
            return candidates[0]
    return None


def render_run_detail(r: Dict[str, Any]):
    """Renders comprehensive details of a single benchmark run."""
    p1 = r.get("player1", {})
    p2 = r.get("player2", {})
    wr = r.get("win_rate", {})
    sp = r.get("net_spread", {})
    sig = r.get("significance", {})
    mode_str = "Duplicate (Pair-Swapped, Zero Luck)" if r.get("mode") == "duplicate" else "Standard (Alternating Seats)"

    print("=" * 80)
    print(f" TOURNAMENT RUN DETAILS: {r.get('run_id')}")
    print("=" * 80)
    print(f"Timestamp       : {r.get('timestamp')}")
    print(f"Tag             : {r.get('tag')}")
    print(f"Mode            : {mode_str}")
    print(f"Lexicon         : {r.get('lexicon')}")
    dup_info = f" ({r.get('duplicate_pairs')} pairs)" if r.get("duplicate_pairs") else ""
    print(f"Total Games     : {r.get('total_games')}{dup_info}")
    print(f"Duration        : {r.get('duration_seconds')}s ({r.get('seconds_per_game')}s/game)")
    print("-" * 80)
    print(f"Player 1        : {p1.get('name')}")
    print(f"  Short / Spec  : {p1.get('short_name')} (preset: {p1.get('spec')})")
    print(f"  Checkpoint    : {p1.get('checkpoint_file')}")
    print(f"  Wins / Record : {p1.get('wins')}W - {p2.get('wins')}L - {r.get('draws')}D")
    print(f"  Mean Score    : {p1.get('mean_score')} pts (Bingos/Game: {p1.get('bingos_per_game')})")
    print("-" * 80)
    print(f"Player 2        : {p2.get('name')}")
    print(f"  Short / Spec  : {p2.get('short_name')} (preset: {p2.get('spec')})")
    print(f"  Checkpoint    : {p2.get('checkpoint_file')}")
    print(f"  Mean Score    : {p2.get('mean_score')} pts (Bingos/Game: {p2.get('bingos_per_game')})")
    print("-" * 80)
    print(f"Win Rate (95% CI)   : {wr.get('percentage')}% ± {wr.get('ci95')}% [{wr.get('ci_lower')}% — {wr.get('ci_upper')}%]")
    print(f"Net Spread (95% CI) : {sp.get('mean'):+.1f} ± {sp.get('ci95')} pts/game [{sp.get('ci_lower'):+.1f} — {sp.get('ci_upper'):+.1f} pts]")
    print(f"Paired t-Test       : t = {sig.get('t_statistic')}, p = {sig.get('p_value')} ({sig.get('verdict')})")
    if r.get("notes"):
        print(f"Notes           : {r.get('notes')}")
    details = r.get("details", [])
    if details:
        print(f"Game Records    : {len(details)} recorded game data points saved in JSON.")
    print("=" * 80)


def render_run_comparison(r1: Dict[str, Any], r2: Dict[str, Any]):
    """Renders a side-by-side comparative analysis between two tournament runs."""
    p1_a = r1.get("player1", {})
    p2_a = r1.get("player2", {})
    wr_a = r1.get("win_rate", {})
    sp_a = r1.get("net_spread", {})
    sig_a = r1.get("significance", {})

    p1_b = r2.get("player1", {})
    p2_b = r2.get("player2", {})
    wr_b = r2.get("win_rate", {})
    sp_b = r2.get("net_spread", {})
    sig_b = r2.get("significance", {})

    d_wr = wr_b.get("percentage", 0.0) - wr_a.get("percentage", 0.0)
    d_sp = sp_b.get("mean", 0.0) - sp_a.get("mean", 0.0)
    d_p1_sc = (p1_b.get("mean_score", 0.0) or 0.0) - (p1_a.get("mean_score", 0.0) or 0.0)
    d_p1_bg = (p1_b.get("bingos_per_game", 0.0) or 0.0) - (p1_a.get("bingos_per_game", 0.0) or 0.0)
    d_speed = (r2.get("seconds_per_game", 0.0) or 0.0) - (r1.get("seconds_per_game", 0.0) or 0.0)

    print("=" * 115)
    print("                             HEAD-TO-HEAD BENCHMARK RUN COMPARISON")
    print("=" * 115)
    h_a = f"Run A ({r1.get('run_id','A')})"
    h_b = f"Run B ({r2.get('run_id','B')})"
    print(f"{'Metric':<25} {h_a:<40} {h_b:<40} {'Delta (B - A)'}")
    print("-" * 115)
    print(f"{'Tag':<25} {r1.get('tag','N/A'):<40} {r2.get('tag','N/A'):<40} —")
    print(f"{'Date':<25} {r1.get('timestamp','')[:16]:<40} {r2.get('timestamp','')[:16]:<40} —")
    print(f"{'Mode':<25} {r1.get('mode',''):<40} {r2.get('mode',''):<40} —")
    games_delta = r2.get('total_games', 0) - r1.get('total_games', 0)
    print(f"{'Total Games':<25} {str(r1.get('total_games','')):<40} {str(r2.get('total_games','')):<40} {games_delta:+d} games")
    print(f"{'Player 1':<25} {p1_a.get('short_name','P1'):<40} {p1_b.get('short_name','P1'):<40} —")
    print(f"{'Player 2':<25} {p2_a.get('short_name','P2'):<40} {p2_b.get('short_name','P2'):<40} —")
    print("-" * 115)
    wr_str_a = f"{wr_a.get('percentage', 0.0):.1f}% ± {wr_a.get('ci95', 0.0):.1f}%"
    wr_str_b = f"{wr_b.get('percentage', 0.0):.1f}% ± {wr_b.get('ci95', 0.0):.1f}%"
    print(f"{'Win Rate':<25} {wr_str_a:<40} {wr_str_b:<40} {d_wr:+.1f}%")
    ci_w_a = f"[{wr_a.get('ci_lower', 0.0):.1f}% — {wr_a.get('ci_upper', 0.0):.1f}%]"
    ci_w_b = f"[{wr_b.get('ci_lower', 0.0):.1f}% — {wr_b.get('ci_upper', 0.0):.1f}%]"
    print(f"{'Win Rate 95% CI':<25} {ci_w_a:<40} {ci_w_b:<40} —")
    sp_str_a = f"{sp_a.get('mean', 0.0):+.1f} ± {sp_a.get('ci95', 0.0):.1f} pts/g"
    sp_str_b = f"{sp_b.get('mean', 0.0):+.1f} ± {sp_b.get('ci95', 0.0):.1f} pts/g"
    print(f"{'Net Spread':<25} {sp_str_a:<40} {sp_str_b:<40} {d_sp:+.1f} pts/g")
    ci_s_a = f"[{sp_a.get('ci_lower', 0.0):+.1f} — {sp_a.get('ci_upper', 0.0):+.1f} pts]"
    ci_s_b = f"[{sp_b.get('ci_lower', 0.0):+.1f} — {sp_b.get('ci_upper', 0.0):+.1f} pts]"
    print(f"{'Net Spread 95% CI':<25} {ci_s_a:<40} {ci_s_b:<40} —")
    t_str_a = f"t = {sig_a.get('t_statistic', 0.0):.2f} (p = {sig_a.get('p_value', 0.0):.4f})"
    t_str_b = f"t = {sig_b.get('t_statistic', 0.0):.2f} (p = {sig_b.get('p_value', 0.0):.4f})"
    print(f"{'Paired t-Statistic':<25} {t_str_a:<40} {t_str_b:<40} —")
    print(f"{'Statistical Verdict':<25} {sig_a.get('verdict',''):<40} {sig_b.get('verdict',''):<40} —")
    sc1_a = f"{p1_a.get('mean_score', 0.0):.1f} pts ({p1_a.get('bingos_per_game', 0.0):.2f} bg)"
    sc1_b = f"{p1_b.get('mean_score', 0.0):.1f} pts ({p1_b.get('bingos_per_game', 0.0):.2f} bg)"
    print(f"{'P1 Mean Score':<25} {sc1_a:<40} {sc1_b:<40} {d_p1_sc:+.1f} pts ({d_p1_bg:+.2f} bg)")
    sc2_a = f"{p2_a.get('mean_score', 0.0):.1f} pts ({p2_a.get('bingos_per_game', 0.0):.2f} bg)"
    sc2_b = f"{p2_b.get('mean_score', 0.0):.1f} pts ({p2_b.get('bingos_per_game', 0.0):.2f} bg)"
    d_p2_sc = (p2_b.get('mean_score', 0.0) or 0.0) - (p2_a.get('mean_score', 0.0) or 0.0)
    print(f"{'P2 Mean Score':<25} {sc2_a:<40} {sc2_b:<40} {d_p2_sc:+.1f} pts")
    spd_a = f"{r1.get('seconds_per_game', 0.0):.2f} s/game"
    spd_b = f"{r2.get('seconds_per_game', 0.0):.2f} s/game"
    print(f"{'Speed':<25} {spd_a:<40} {spd_b:<40} {d_speed:+.2f} s/game")
    print("=" * 115)


def cmd_history(args):
    """View, search, and compare historical tournament benchmarks."""
    ledger_path = os.path.join(TOURNAMENTS_DIR, "tournament_history.jsonl")

    # Mode 1: Compare two runs
    if args.compare:
        id1, id2 = args.compare[0], args.compare[1]
        f1 = find_run_file(id1)
        f2 = find_run_file(id2)

        if not f1:
            print(f"Error: Could not locate tournament run for '{id1}'.")
            return
        if not f2:
            print(f"Error: Could not locate tournament run for '{id2}'.")
            return

        with open(f1, "r", encoding="utf-8") as f:
            r1 = json.load(f)
        with open(f2, "r", encoding="utf-8") as f:
            r2 = json.load(f)

        render_run_comparison(r1, r2)
        return

    # Mode 2: Show specific run in full detail
    if args.show:
        target_file = find_run_file(args.show)
        if not target_file:
            print(f"Error: Could not locate tournament run for '{args.show}'.")
            return
        with open(target_file, "r", encoding="utf-8") as f:
            run_data = json.load(f)
        render_run_detail(run_data)
        return

    # Mode 3: Display ledger table
    runs = []
    if os.path.isfile(ledger_path):
        with open(ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        runs.append(json.loads(line))
                    except Exception:
                        pass
    elif os.path.isdir(TOURNAMENTS_DIR):
        for f in sorted(os.listdir(TOURNAMENTS_DIR)):
            if f.endswith(".json") and f != "tournament_history.json":
                try:
                    with open(os.path.join(TOURNAMENTS_DIR, f), "r", encoding="utf-8") as jf:
                        runs.append(json.load(jf))
                except Exception:
                    pass

    if not runs:
        print("\nNo tournament runs found in data/tournaments/.")
        print("Run a tournament to generate history records:")
        print("  python cli.py tournament --opponent magpie --games 10\n")
        return

    # Filtering
    if args.tag:
        runs = [r for r in runs if args.tag.lower() in r.get("tag", "").lower()]
    if args.model:
        runs = [
            r for r in runs
            if args.model.lower() in r.get("player1", {}).get("name", "").lower()
            or args.model.lower() in r.get("player1", {}).get("short_name", "").lower()
            or args.model.lower() in r.get("player1", {}).get("spec", "").lower()
        ]

    runs = runs[-args.limit:]

    print("=" * 135)
    print("                                      ALPHABLE V4 TOURNAMENT BENCHMARK HISTORY LEDGER")
    print("=" * 135)
    print(
        f"{'Run ID':<21} {'Date/Time':<16} {'Mode':<5} {'Matchup':<27} {'Games':<6} "
        f"{'Win Rate (95% CI)':<20} {'Net Spread (95% CI)':<22} {'Sig (t, p)':<15} {'Tag'}"
    )
    print("-" * 135)

    for r in runs:
        run_id = r.get("run_id", "N/A")
        ts = r.get("timestamp", "").replace("T", " ")[:16]
        mode = "Dup" if r.get("mode") == "duplicate" else "Std"
        p1 = r.get("player1", {}).get("short_name", "P1")
        p2 = r.get("player2", {}).get("short_name", "P2")
        matchup = f"{p1} vs {p2}"
        if len(matchup) > 27:
            matchup = matchup[:26] + "…"

        games = str(r.get("total_games", 0))
        wr = r.get("win_rate", {})
        wr_str = f"{wr.get('percentage', 0.0):.1f}% ± {wr.get('ci95', 0.0):.1f}%"
        sp = r.get("net_spread", {})
        sp_str = f"{sp.get('mean', 0.0):+.1f} ± {sp.get('ci95', 0.0):.1f} pts"
        sig = r.get("significance", {})
        sig_str = f"t={sig.get('t_statistic', 0.0):.2f} p={sig.get('p_value', 0.0):.2f}"
        tag = r.get("tag", "")

        print(
            f"{run_id:<21} {ts:<16} {mode:<5} {matchup:<27} {games:<6} "
            f"{wr_str:<20} {sp_str:<22} {sig_str:<15} {tag}"
        )

    print("-" * 135)
    print(f"Total Runs Displayed: {len(runs)} | Storage: data/tournaments/")
    print("Commands:")
    print("  • View details : python cli.py history --show <run_id>")
    print("  • Compare runs : python cli.py history --compare <run1_id> <run2_id>")
    print("=" * 135)


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Alphable V4 Command Center: Interactive play, analysis, tournaments, model registry, and AI ablation."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 0. Models
    p_models = subparsers.add_parser("models", help="List all neural checkpoints, search presets, and benchmark ratings")

    # 1. Analyze
    p_analyze = subparsers.add_parser("analyze", help="Compare Base MAGPIE vs BAMS AI on any position")
    p_analyze.add_argument("--model", "--model-preset", dest="model", type=str, default="latest",
                           help="Model preset ('latest', '5-frontiers', 'rl-gen1', 'scaled', 'v4-baseline')")
    p_analyze.add_argument("--model-path", type=str, default=None, help="Custom checkpoint path override (.pt)")
    p_analyze.add_argument("--rack", type=str, default="AQRTUYZ", help="Player rack tiles (default: AQRTUYZ)")
    p_analyze.add_argument("--board-word", type=str, default="", help="Optional word on board (e.g. TRAIN)")
    p_analyze.add_argument("--board-coord", type=str, default="8D", help="Optional coordinate of board word (e.g. 8D)")
    p_analyze.add_argument("--samples", type=int, default=None, help="Override number of opponent rack samples (N)")
    p_analyze.add_argument("--beam", type=int, default=None, help="Override top candidate beam size (K)")
    p_analyze.add_argument("--max-deficit", type=float, default=None, help="Override max static equity deficit allowed")
    p_analyze.add_argument("--volatility-weight", type=float, default=None, help="Override board volatility control weight")
    p_analyze.add_argument("--lexicon", type=str, default="CSW24", help="Lexicon (CSW24 or NWL23)")
    p_analyze.add_argument("--seed", type=int, default=42, help="Random seed for CRN")

    # 2. Play
    p_play = subparsers.add_parser("play", help="Play an interactive game against Alphable V4 in terminal")
    p_play.add_argument("--model", "--model-preset", dest="model", type=str, default="latest",
                        help="Model preset ('latest', '5-frontiers', 'rl-gen1', 'scaled', 'v4-baseline')")
    p_play.add_argument("--model-path", type=str, default=None, help="Custom checkpoint path override (.pt)")
    p_play.add_argument("--lexicon", type=str, default="CSW24", help="Lexicon (CSW24 or NWL23)")
    p_play.add_argument("--seed", type=int, default=None, help="Optional game seed")

    # 3. Tournament
    p_tournament = subparsers.add_parser("tournament", help="Run head-to-head match series vs baseline or another model")
    p_tournament.add_argument("--model", "--model-preset", dest="model", type=str, default="latest",
                              help="Player 1 model preset: 'latest', '5-frontiers', 'rl-gen1', 'scaled', 'v4-baseline' (default: latest)")
    p_tournament.add_argument("--model-path", type=str, default=None, help="Custom checkpoint path for Player 1 (.pt)")
    p_tournament.add_argument("--opponent", type=str, default="magpie",
                              help="Opponent preset or baseline: 'magpie', 'v3-resnet', 'v3-transformer', 'greedy', 'v4-baseline', '5-frontiers', 'rl-gen1', 'scaled', 'latest' (default: magpie)")
    p_tournament.add_argument("--opponent-model-path", type=str, default=None, help="Custom checkpoint path for opponent (.pt)")
    p_tournament.add_argument("--games", type=int, default=10, help="Number of games to simulate (default: 10)")
    p_tournament.add_argument("--duplicate", action="store_true", help="Run duplicate pair-swapped matches to neutralize tile draw luck")
    p_tournament.add_argument("--lexicon", type=str, default="CSW24", help="Lexicon (CSW24 or NWL23)")
    p_tournament.add_argument("--samples", type=int, default=None, help="Override opponent rack samples (N)")
    p_tournament.add_argument("--beam", type=int, default=None, help="Override candidate beam (K)")
    p_tournament.add_argument("--volatility-weight", type=float, default=None, help="Override volatility weight")
    p_tournament.add_argument("--device", type=str, default=None, help="Device ('cuda' or 'cpu')")
    p_tournament.add_argument("--tag", type=str, default=None, help="Custom tag or label for this tournament run (e.g. 'rl-tune-exp1')")
    p_tournament.add_argument("--no-save", action="store_true", help="Do not save run telemetry or append to history ledger")

    # 4. Ablation
    p_ablation = subparsers.add_parser("ablation", help="Quantify AI Value Network contribution (ON vs OFF)")
    p_ablation.add_argument("--model", "--model-preset", dest="model", type=str, default="latest",
                            help="Model preset to ablate (default: latest)")
    p_ablation.add_argument("--games", type=int, default=10, help="Number of games to simulate")
    p_ablation.add_argument("--lexicon", type=str, default="CSW24", help="Lexicon (CSW24 or NWL23)")

    # 5. History
    p_history = subparsers.add_parser("history", help="Inspect and compare past tournament benchmarks")
    p_history.add_argument("--show", type=str, default=None, help="Inspect detailed telemetry of a specific run (by ID or prefix)")
    p_history.add_argument("--compare", nargs=2, metavar=("RUN1", "RUN2"), default=None, help="Compare two tournament runs side-by-side with delta analysis")
    p_history.add_argument("--tag", type=str, default=None, help="Filter runs by tag substring")
    p_history.add_argument("--model", type=str, default=None, help="Filter runs by model name substring")
    p_history.add_argument("--limit", type=int, default=25, help="Maximum number of historical runs to display (default: 25)")

    args = parser.parse_args()

    if args.command == "models":
        cmd_models(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "play":
        cmd_play(args)
    elif args.command == "tournament":
        cmd_tournament(args)
    elif args.command == "ablation":
        cmd_ablation(args)
    elif args.command == "history":
        cmd_history(args)


if __name__ == "__main__":
    main()
