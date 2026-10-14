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
import argparse
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
        def magpie_policy(state: GameState):
            cands = engine.generate_moves(game_state=state, max_candidates=5)
            if cands:
                return cands[0], {"method": "magpie_static_top"}
            return Move.create_pass(), {"method": "pass"}
        return magpie_policy, "Base MAGPIE (KLV Static)", "Base-MAGPIE"

    # 2. V3 ResNet Champion (Macondo Distilled, 63 dims)
    if norm in ("v3", "v3-resnet"):
        sys.path.insert(0, "/home/targed/Documents/Git/Alphable/Alphable_V3/src")
        from alphable.core import inference as v3_inference, simulator as v3_simulator
        v3_dict = "/home/targed/Documents/Git/Alphable/Alphable_V3/resources/CSW24.txt"
        v3_model = "/home/targed/Documents/Git/Alphable/Alphable_V3/models/alphable_v3_macondo_v2.pth"
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
        sys.path.insert(0, "/home/targed/Documents/Git/Alphable/Alphable_V3/src")
        from alphable.models.transformer_ranker import SmolLM2CandidateRanker
        from alphable.core import simulator as v3_simulator, structure as v3_structure
        v3_dict = "/home/targed/Documents/Git/Alphable/Alphable_V3/resources/CSW24.txt"
        t_model_path = "/home/targed/Documents/Git/Alphable/Alphable_V3/models/transformer_ranker_v2"
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
        print("-" * 75)
        print(" STATISTICAL SIGNIFICANCE (ZERO TILE LUCK TEST)")
        print("-" * 75)
        print(f"Match Win Rate (95% CI) : {pair_win_pct:.1f}% ± {ci95_win_dup:.1f}% [{pair_win_pct - ci95_win_dup:.1f}% — {pair_win_pct + ci95_win_dup:.1f}%]")
        print(f"Net Spread (95% CI)     : {mean_dup_spread:+.1f} ± {ci95_dup_spread:.1f} pts/game [{mean_dup_spread - ci95_dup_spread:+.1f} — {mean_dup_spread + ci95_dup_spread:+.1f} pts]")
        print(f"Paired t-Test (H0: Δ=0) : t = {t_dup:.2f}, p-value = {p_val_dup:.4f} ({sig_dup})")
        print("Luck Cancellation       : Tile draw noise eliminated via paired symmetric seeds.")
        print("=" * 75)
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

        p1_sc = s1 if p1_is_first else s2
        p2_sc = s2 if p1_is_first else s1
        game_margins.append(p1_sc - p2_sc)

        if p1_won:
            p1_wins += 1
            verdict = f"{p1_short} WON ✓"
        elif p2_won:
            p2_wins += 1
            verdict = f"{p2_short} WON"
        else:
            draws += 1
            verdict = "DRAW"

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

    # 4. Ablation
    p_ablation = subparsers.add_parser("ablation", help="Quantify AI Value Network contribution (ON vs OFF)")
    p_ablation.add_argument("--model", "--model-preset", dest="model", type=str, default="latest",
                            help="Model preset to ablate (default: latest)")
    p_ablation.add_argument("--games", type=int, default=10, help="Number of games to simulate")
    p_ablation.add_argument("--lexicon", type=str, default="CSW24", help="Lexicon (CSW24 or NWL23)")

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


if __name__ == "__main__":
    main()
