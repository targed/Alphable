"""
Frontier 5: Automated Hyperparameter Calibration Engine for Alphable V4 BAMS.

Performs systematic optimization of BAMS search hyperparameters:
- weight_2ply (2-ply nested rollout influence)
- opp_penalty_weight (leakage penalty multiplier)
- max_static_deficit (candidate pruning threshold)
- value_weight (positional network equity scaling)

Uses duplicate match series (seed-swapped) to eliminate tile luck variance.
"""

import sys
import os
import json
import argparse
import itertools
from typing import Dict, Any, List, Tuple
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alphable_v4.engine.magpie_bindings import MagpieEngine
from alphable_v4.engine.move import Move
from alphable_v4.engine.game_state import GameState
from alphable_v4.search.bams import BAMSSearch, BAMSConfig
from alphable_v4.platform.eval import GameSimulator


def evaluate_hyperparams(
    engine: MagpieEngine,
    checkpoint_path: str,
    params: Dict[str, Any],
    num_matches: int = 5,
    base_seed: int = 42,
    lexicon: str = "CSW24",
) -> Dict[str, Any]:
    """
    Evaluates a parameter set over duplicate matches against Base MAGPIE.
    Each match consists of 2 games with identical tile bags and swapped seats.
    """
    config = BAMSConfig(
        num_samples=16,
        candidate_beam=12,
        max_static_deficit=params.get("max_static_deficit", 3.5),
        opp_penalty_weight=params.get("opp_penalty_weight", 0.12),
        value_weight=params.get("value_weight", 4.5),
        nested_2ply=True,
        candidate_beam_2ply=4,
        samples_2ply=8,
        weight_2ply=params.get("weight_2ply", 0.18),
        use_pre_endgame=True,
        use_belief_tracker=True,
        dynamic_beam=True,
        use_exact_endgame=True,
    )
    bams = BAMSSearch.from_checkpoint(engine, checkpoint_path, config=config)
    sim = GameSimulator(engine, lexicon=lexicon)

    def bams_policy(s: GameState) -> Tuple[Move, Dict[str, Any]]:
        return bams.select_move(s)

    def magpie_policy(s: GameState) -> Tuple[Move, Dict[str, Any]]:
        cands = engine.generate_moves(game_state=s, max_candidates=5)
        return (cands[0], {}) if cands else (Move.create_pass(), {})

    bams_scores: List[int] = []
    magpie_scores: List[int] = []
    bams_wins = 0
    magpie_wins = 0
    draws = 0

    for m in range(num_matches):
        seed = base_seed + m * 101
        bams.opp_tracker.reset()

        # Leg 1: BAMS is Player 1
        r1 = sim.play_game(bams_policy, magpie_policy, seed=seed)
        bams_scores.append(r1["p1_score"])
        magpie_scores.append(r1["p2_score"])

        # Leg 2: BAMS is Player 2 (identical tile seed)
        bams.opp_tracker.reset()
        r2 = sim.play_game(magpie_policy, bams_policy, seed=seed)
        bams_scores.append(r2["p2_score"])
        magpie_scores.append(r2["p1_score"])

        # Net duplicate spread for match
        net_m = (r1["p1_score"] - r1["p2_score"]) + (r2["p2_score"] - r2["p1_score"])
        if net_m > 0:
            bams_wins += 1
        elif net_m < 0:
            magpie_wins += 1
        else:
            draws += 1

    total_games = len(bams_scores)
    mean_bams = float(np.mean(bams_scores))
    mean_magpie = float(np.mean(magpie_scores))
    net_spread = mean_bams - mean_magpie
    win_rate = (bams_wins + 0.5 * draws) / max(1, num_matches) * 100.0

    return {
        "params": params,
        "matches_played": num_matches,
        "total_games": total_games,
        "match_record": f"{bams_wins}W - {magpie_wins}L - {draws}D",
        "win_rate": win_rate,
        "mean_bams_score": mean_bams,
        "mean_magpie_score": mean_magpie,
        "net_spread": net_spread,
    }


def run_hyperparameter_optimization(
    checkpoint_path: str,
    output_path: str = "Alphable_V4/data/optimal_hyperparams.json",
    num_matches: int = 3,
    lexicon: str = "CSW24",
) -> Dict[str, Any]:
    """Runs systematic sweep over parameter grid and identifies optimum."""
    engine = MagpieEngine(lexicon=lexicon)

    # Grid search space centered around calibrated theoretical values
    param_grid = [
        {"weight_2ply": 0.15, "opp_penalty_weight": 0.10, "max_static_deficit": 3.5, "value_weight": 4.5},
        {"weight_2ply": 0.18, "opp_penalty_weight": 0.12, "max_static_deficit": 3.5, "value_weight": 4.5},
        {"weight_2ply": 0.22, "opp_penalty_weight": 0.12, "max_static_deficit": 4.0, "value_weight": 5.0},
        {"weight_2ply": 0.18, "opp_penalty_weight": 0.15, "max_static_deficit": 3.0, "value_weight": 4.0},
    ]

    results: List[Dict[str, Any]] = []
    print(f"Starting Hyperparameter Optimization across {len(param_grid)} configurations...")
    print(f"Evaluation: {num_matches} duplicate matches ({num_matches * 2} games) per trial.\n")

    for i, p in enumerate(param_grid):
        print(f"Trial {i+1}/{len(param_grid)}: {p}")
        res = evaluate_hyperparams(
            engine,
            checkpoint_path,
            p,
            num_matches=num_matches,
            base_seed=1000 + i * 50,
            lexicon=lexicon,
        )
        print(f"  Result: WR: {res['win_rate']:.1f}% | Net Spread: {res['net_spread']:+.1f} pts | BAMS {res['mean_bams_score']:.1f} vs MAGPIE {res['mean_magpie_score']:.1f}\n")
        results.append(res)

    best_result = max(results, key=lambda x: (x["win_rate"], x["net_spread"]))

    print("=" * 65)
    print("OPTIMAL HYPERPARAMETER CONFIGURATION FOUND")
    print("=" * 65)
    print(f"Parameters: {best_result['params']}")
    print(f"Win Rate  : {best_result['win_rate']:.1f}%")
    print(f"Net Spread: {best_result['net_spread']:+.1f} pts/game")
    print("=" * 65)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({
            "optimal_params": best_result["params"],
            "best_win_rate": best_result["win_rate"],
            "best_net_spread": best_result["net_spread"],
            "all_trials": results,
        }, f, indent=2)
    print(f"Saved optimal hyperparameters to {output_path}")

    return best_result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", default="/home/targed/Documents/Git/Alphable/Alphable_V4/models/checkpoints/v4_value_net_best.pt")
    parser.add_argument("--output", default="/home/targed/Documents/Git/Alphable/Alphable_V4/data/optimal_hyperparams.json")
    parser.add_argument("--matches", type=int, default=3)
    args = parser.parse_args()

    run_hyperparameter_optimization(args.checkpoint, args.output, num_matches=args.matches)
