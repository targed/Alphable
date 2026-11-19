"""
Policy Registry and Builders for Alphable V4 Evaluation and Tournaments.

Defines model presets, aliases, and policy construction for:
1. Alphable V4 BAMS and Hybrid PIMC neural search engines.
2. Classical Base MAGPIE (Static, PAT, and Maximally Tuned PIMC + Endgame).
3. Legacy Alphable V3 (Macondo ResNet and SmolLM2 Transformer).
4. Score-greedy and random baseline players.
"""

from __future__ import annotations
import os
import sys
from typing import Dict, Any, Tuple, Optional, Callable, List

import torch

from alphable_v4.engine.move import Move
from alphable_v4.engine.game_state import GameState
from alphable_v4.engine.magpie_bindings import MagpieEngine
from alphable_v4.search.bams import BAMSSearch, BAMSConfig


CHECKPOINTS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "models", "checkpoints")
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
    "hybrid-pimc": {
        "name": "Alphable V4 Hybrid PIMC (Native Simulation + Neural Re-Ranking)",
        "short_name": "Hybrid-PIMC",
        "checkpoint_file": "v4_value_net_best.pt",
        "description": "Native C PIMC rollouts (~98k nps) + ResNet-18 Cross-Attention value network re-ranking",
        "verified_wr": "Grandmaster Benchmark vs Tuned MAGPIE",
        "status": "🚀 SOTA HYBRID ENGINE",
        "config": {
            "hybrid_pimc": True,
            "sim_iterations": 35,
            "use_pat": True,
            "pimc_weight": 1.0,
            "win_prob_weight": 8.0,
            "value_weight": 3.0,
            "use_volatility_control": True,
            "volatility_weight": 0.4,
            "use_exact_endgame": True,
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
    "pimc": "hybrid-pimc",
    "hybrid": "hybrid-pimc",
    "v4-hybrid": "hybrid-pimc",
    "sota": "hybrid-pimc",
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
    1. A V4 model preset ('latest', '5-frontiers', 'rl-gen1', 'scaled', 'v4-baseline', 'hybrid-pimc')
    2. A custom model checkpoint path (--model-path)
    3. Classical Base MAGPIE ('magpie', 'magpie-pat', 'magpie-tuned')
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
                out_sim = engine.simulate(iterations=sim_iters)
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
        repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
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
        repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
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
    if canonical_key in ("v4-pat", "hybrid-pimc") or norm in ("v4-pat", "champion-pat", "latest-pat", "hybrid-pimc", "hybrid", "pimc"):
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
