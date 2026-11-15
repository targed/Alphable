"""
Evaluation Harness and Match Simulation Engine for Alphable V4.

Simulates complete, tournament-rule Scrabble games between Alphable V4 (BAMS)
and baseline engines (Static Greedy, HastyBot, or self-play).
Tracks:
- Win rate
- Mean scores
- Bingos per game
- Invalid move violations (must be 0)
- End-game tile penalties according to official WESPA/NASPA rules
"""

from __future__ import annotations
import concurrent.futures
import os
from pathlib import Path
import random
import time
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any, Callable

import numpy as np
import scipy.stats as st

from alphable_v4.engine.move import Move
from alphable_v4.engine.game_state import GameState, STANDARD_TILE_COUNTS, TILE_VALUES
from alphable_v4.engine.magpie_bindings import MagpieEngine
from alphable_v4.search.bams import BAMSSearch, BAMSConfig
from alphable_v4.platform.checkpoint import TournamentCheckpointManager
from alphable_v4.platform.policies import build_policy


@dataclass
class MatchStats:
    """Aggregated match series metrics."""
    games_played: int = 0
    p1_wins: int = 0
    p2_wins: int = 0
    draws: int = 0
    p1_total_score: int = 0
    p2_total_score: int = 0
    p1_total_bingos: int = 0
    p2_total_bingos: int = 0
    p1_invalid_moves: int = 0
    p2_invalid_moves: int = 0
    game_results: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def p1_win_rate(self) -> float:
        return (self.p1_wins + 0.5 * self.draws) / max(1, self.games_played)

    @property
    def p1_mean_score(self) -> float:
        return self.p1_total_score / max(1, self.games_played)

    @property
    def p2_mean_score(self) -> float:
        return self.p2_total_score / max(1, self.games_played)

    @property
    def p1_bingos_per_game(self) -> float:
        return self.p1_total_bingos / max(1, self.games_played)

    @property
    def p2_bingos_per_game(self) -> float:
        return self.p2_total_bingos / max(1, self.games_played)


class ScrabbleBag:
    """Simulates the physical Scrabble tile bag."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.tiles: List[str] = []
        for tile, count in STANDARD_TILE_COUNTS.items():
            self.tiles.extend([tile] * count)
        self.rng.shuffle(self.tiles)

    def draw(self, n: int) -> List[str]:
        drawn = []
        for _ in range(min(n, len(self.tiles))):
            drawn.append(self.tiles.pop())
        return drawn

    def exchange(self, rack_tiles: List[str]) -> List[str]:
        drawn = self.draw(len(rack_tiles))
        self.tiles.extend(rack_tiles)
        self.rng.shuffle(self.tiles)
        return drawn

    @property
    def count(self) -> int:
        return len(self.tiles)


def get_game_phase(turn_num: int, bag_count: int) -> str:
    """
    Classifies the game state into one of four distinct phases:
    - OPENING: turns 1 to 5
    - MIDGAME: turn > 5 and bag > 14
    - PRE_ENDGAME: bag in 1..14
    - ENDGAME: bag == 0
    """
    if bag_count == 0:
        return "endgame"
    elif 1 <= bag_count <= 14:
        return "pre_endgame"
    elif turn_num <= 5:
        return "opening"
    else:
        return "midgame"


class GameSimulator:
    """Runs full 2-player Scrabble matches."""

    def __init__(self, engine: MagpieEngine, lexicon: str = "CSW24"):
        self.engine = engine
        self.lexicon = lexicon

    def play_game(
        self,
        p1_policy: Callable[[GameState], Tuple[Move, Dict[str, Any]]],
        p2_policy: Callable[[GameState], Tuple[Move, Dict[str, Any]]],
        seed: Optional[int] = None,
        max_turns: int = 60,
    ) -> Dict[str, Any]:
        """
        Plays a single game to completion.

        Returns:
            Dict containing scores, winner, turn history, and bingo statistics.
        """
        bag = ScrabbleBag(seed=seed)
        board = [[None for _ in range(15)] for _ in range(15)]
        p1_rack = bag.draw(7)
        p2_rack = bag.draw(7)
        p1_score = 0
        p2_score = 0
        p1_bingos = 0
        p2_bingos = 0
        p1_invalid = 0
        p2_invalid = 0

        scoreless_turns = 0
        turn_history = []
        phase_scores: Dict[str, Dict[str, int]] = {
            "opening": {"p1": 0, "p2": 0},
            "midgame": {"p1": 0, "p2": 0},
            "pre_endgame": {"p1": 0, "p2": 0},
            "endgame": {"p1": 0, "p2": 0},
        }
        phase_counts: Dict[str, Dict[str, int]] = {
            "opening": {"p1": 0, "p2": 0},
            "midgame": {"p1": 0, "p2": 0},
            "pre_endgame": {"p1": 0, "p2": 0},
            "endgame": {"p1": 0, "p2": 0},
        }

        turn_num = 0
        while turn_num < max_turns:
            # Player 1's Turn
            turn_num += 1
            phase_p1 = get_game_phase(turn_num, bag.count)
            phase_counts[phase_p1]["p1"] += 1
            state_p1 = GameState(
                board=board,
                rack=p1_rack,
                opp_rack=p2_rack,
                score=p1_score,
                opp_score=p2_score,
                scoreless_turns=scoreless_turns,
                bag_count=bag.count,
                lexicon=self.lexicon,
            )

            try:
                move_p1, meta_p1 = p1_policy(state_p1)
            except Exception:
                move_p1 = Move.create_pass()
                meta_p1 = {"error": "policy_exception"}

            if move_p1.is_placement:
                try:
                    board = state_p1.apply_move(move_p1).board
                except Exception:
                    p1_invalid += 1

                p1_score += move_p1.score
                phase_scores[phase_p1]["p1"] += move_p1.score
                if move_p1.leave is not None and len(move_p1.leave) <= len(p1_rack):
                    tiles_played = len(p1_rack) - len(move_p1.leave)
                    p1_rack = list(move_p1.leave)
                else:
                    tiles_played = min(len(p1_rack), len(move_p1.word))
                    for t in move_p1.word:
                        if t in p1_rack:
                            p1_rack.remove(t)
                        elif '?' in p1_rack:
                            p1_rack.remove('?')

                if tiles_played == 7:
                    p1_bingos += 1

                # Draw new tiles
                p1_rack.extend(bag.draw(7 - len(p1_rack)))
                scoreless_turns = 0
            elif move_p1.is_exchange:
                # Exchange tiles with the bag
                if move_p1.leave is not None and len(move_p1.leave) < len(p1_rack):
                    exch_tiles = list(p1_rack)
                    for t in move_p1.leave:
                        if t in exch_tiles:
                            exch_tiles.remove(t)
                else:
                    exch_tiles = [t.upper() for t in move_p1.word if t.upper() in p1_rack]

                if bag.count >= len(exch_tiles) and len(exch_tiles) > 0:
                    for t in exch_tiles:
                        p1_rack.remove(t)
                    drawn = bag.exchange(exch_tiles)
                    p1_rack.extend(drawn)
                scoreless_turns += 1
            else:
                scoreless_turns += 1

            turn_history.append({
                "player": 1,
                "turn": turn_num,
                "phase": phase_p1,
                "move": str(move_p1),
                "score": move_p1.score,
                "total": p1_score,
            })

            # Check Player 1 out of tiles and bag empty
            if len(p1_rack) == 0 and bag.count == 0:
                penalty = sum(TILE_VALUES.get(t.upper(), 0) for t in p2_rack)
                p1_score += 2 * penalty
                phase_scores["endgame"]["p1"] += 2 * penalty
                break

            if scoreless_turns >= 6:
                break

            # Player 2's Turn
            turn_num += 1
            phase_p2 = get_game_phase(turn_num, bag.count)
            phase_counts[phase_p2]["p2"] += 1
            state_p2 = GameState(
                board=board,
                rack=p2_rack,
                opp_rack=p1_rack,
                score=p2_score,
                opp_score=p1_score,
                scoreless_turns=scoreless_turns,
                bag_count=bag.count,
                lexicon=self.lexicon,
            )

            try:
                move_p2, meta_p2 = p2_policy(state_p2)
            except Exception:
                move_p2 = Move.create_pass()
                meta_p2 = {"error": "policy_exception"}

            if move_p2.is_placement:
                try:
                    board = state_p2.apply_move(move_p2).board
                except Exception:
                    p2_invalid += 1

                p2_score += move_p2.score
                phase_scores[phase_p2]["p2"] += move_p2.score
                if move_p2.leave is not None and len(move_p2.leave) <= len(p2_rack):
                    tiles_played = len(p2_rack) - len(move_p2.leave)
                    p2_rack = list(move_p2.leave)
                else:
                    tiles_played = min(len(p2_rack), len(move_p2.word))
                    for t in move_p2.word:
                        if t in p2_rack:
                            p2_rack.remove(t)
                        elif '?' in p2_rack:
                            p2_rack.remove('?')

                if tiles_played == 7:
                    p2_bingos += 1

                p2_rack.extend(bag.draw(7 - len(p2_rack)))
                scoreless_turns = 0
            elif move_p2.is_exchange:
                # Exchange tiles with the bag
                if move_p2.leave is not None and len(move_p2.leave) < len(p2_rack):
                    exch_tiles = list(p2_rack)
                    for t in move_p2.leave:
                        if t in exch_tiles:
                            exch_tiles.remove(t)
                else:
                    exch_tiles = [t.upper() for t in move_p2.word if t.upper() in p2_rack]

                if bag.count >= len(exch_tiles) and len(exch_tiles) > 0:
                    for t in exch_tiles:
                        p2_rack.remove(t)
                    drawn = bag.exchange(exch_tiles)
                    p2_rack.extend(drawn)
                scoreless_turns += 1
            else:
                scoreless_turns += 1

            turn_history.append({
                "player": 2,
                "turn": turn_num,
                "phase": phase_p2,
                "move": str(move_p2),
                "score": move_p2.score,
                "total": p2_score,
            })

            if len(p2_rack) == 0 and bag.count == 0:
                penalty = sum(TILE_VALUES.get(t.upper(), 0) for t in p1_rack)
                p2_score += 2 * penalty
                phase_scores["endgame"]["p2"] += 2 * penalty
                break

            if scoreless_turns >= 6:
                break

        # If game ended with passes, deduct remaining rack points from each player
        if bag.count > 0 or (len(p1_rack) > 0 and len(p2_rack) > 0):
            p1_rem = sum(TILE_VALUES.get(t.upper(), 0) for t in p1_rack)
            p2_rem = sum(TILE_VALUES.get(t.upper(), 0) for t in p2_rack)
            p1_score -= p1_rem
            p2_score -= p2_rem
            phase_scores["endgame"]["p1"] -= p1_rem
            phase_scores["endgame"]["p2"] -= p2_rem

        winner = 1 if p1_score > p2_score else (2 if p2_score > p1_score else 0)
        return {
            "winner": winner,
            "p1_score": p1_score,
            "p2_score": p2_score,
            "p1_bingos": p1_bingos,
            "p2_bingos": p2_bingos,
            "p1_invalid": p1_invalid,
            "p2_invalid": p2_invalid,
            "total_turns": turn_num,
            "turn_history": turn_history,
            "phase_scores": phase_scores,
            "phase_counts": phase_counts,
        }

    def run_match_series(
        self,
        p1_policy: Callable[[GameState], Tuple[Move, Dict[str, Any]]],
        p2_policy: Callable[[GameState], Tuple[Move, Dict[str, Any]]],
        num_games: int = 10,
        start_seed: int = 1000,
        verbose: bool = True,
    ) -> MatchStats:
        """Executes a multi-game tournament series."""
        stats = MatchStats()

        for g_idx in range(num_games):
            seed = start_seed + g_idx
            res = self.play_game(p1_policy, p2_policy, seed=seed)

            stats.games_played += 1
            stats.p1_total_score += res["p1_score"]
            stats.p2_total_score += res["p2_score"]
            stats.p1_total_bingos += res["p1_bingos"]
            stats.p2_total_bingos += res["p2_bingos"]
            stats.p1_invalid_moves += res["p1_invalid"]
            stats.p2_invalid_moves += res["p2_invalid"]
            stats.game_results.append(res)

            if res["winner"] == 1:
                stats.p1_wins += 1
            elif res["winner"] == 2:
                stats.p2_wins += 1
            else:
                stats.draws += 1

            if verbose:
                print(
                    f"Game {g_idx+1:03d}/{num_games:03d}: P1 {res['p1_score']} - {res['p2_score']} P2 "
                    f"| Winner: {'P1' if res['winner']==1 else ('P2' if res['winner']==2 else 'Tie')} "
                    f"| Bingos: {res['p1_bingos']}-{res['p2_bingos']}"
                )

        return stats


_WORKER_CACHE: Dict[Tuple[Any, ...], Dict[str, Any]] = {}


def _init_worker_env():
    """Pin thread counts and memory limits inside worker process."""
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
    os.environ["NUMEXPR_NUM_THREADS"] = "1"
    os.environ["MAGPIE_THREADS"] = "1"
    if "MAGPIE_MAX_MEMORY_MB" not in os.environ:
        os.environ["MAGPIE_MAX_MEMORY_MB"] = "256"
    try:
        import torch
        torch.set_num_threads(1)
    except Exception:
        pass


def _run_duplicate_pair_worker(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Worker function executed in an isolated OS process.
    Reuses persistent MagpieEngine and policy models across pairs in the same process
    to eliminate redundant model loading, heap fragmentation, and thread over-subscription.
    """
    _init_worker_env()

    lexicon = task.get("lexicon", "CSW24")
    device = task.get("device", "cpu")
    p1_kwargs = task.get("p1_kwargs") or {}
    p2_kwargs = task.get("p2_kwargs") or {}
    cache_key = (
        task["p1_spec"],
        task["p2_spec"],
        lexicon,
        device,
        task.get("p1_model_path"),
        task.get("p2_model_path"),
        tuple(sorted(p1_kwargs.items())),
        tuple(sorted(p2_kwargs.items())),
    )

    if cache_key not in _WORKER_CACHE:
        engine_p1 = MagpieEngine(lexicon=lexicon)
        engine_p2 = MagpieEngine(lexicon=lexicon)
        p1_policy, p1_name, p1_short = build_policy(
            engine_p1,
            spec=task["p1_spec"],
            model_path=task.get("p1_model_path"),
            overrides=p1_kwargs,
            lexicon=lexicon,
            device=device,
        )
        p2_policy, p2_name, p2_short = build_policy(
            engine_p2,
            spec=task["p2_spec"],
            model_path=task.get("p2_model_path"),
            overrides=p2_kwargs,
            lexicon=lexicon,
            device=device,
        )
        sim = GameSimulator(engine_p1, lexicon=lexicon)
        _WORKER_CACHE[cache_key] = {
            "engine_p1": engine_p1,
            "engine_p2": engine_p2,
            "p1_policy": p1_policy,
            "p2_policy": p2_policy,
            "p1_name": p1_name,
            "p1_short": p1_short,
            "p2_name": p2_name,
            "p2_short": p2_short,
            "sim": sim,
        }

    cached = _WORKER_CACHE[cache_key]
    sim = cached["sim"]
    p1_policy = cached["p1_policy"]
    p2_policy = cached["p2_policy"]
    p1_name = cached["p1_name"]
    p1_short = cached["p1_short"]
    p2_name = cached["p2_name"]
    p2_short = cached["p2_short"]
    seed = task["seed"]

    # Game A: P1 as Player 1, P2 as Player 2
    res_a = sim.play_game(p1_policy, p2_policy, seed=seed)
    # Game B: P2 as Player 1, P1 as Player 2 with IDENTICAL SEED
    res_b = sim.play_game(p2_policy, p1_policy, seed=seed)

    score_p1_pair = res_a["p1_score"] + res_b["p2_score"]
    score_p2_pair = res_a["p2_score"] + res_b["p1_score"]
    bingos_p1_pair = res_a["p1_bingos"] + res_b["p2_bingos"]
    bingos_p2_pair = res_a["p2_bingos"] + res_b["p1_bingos"]

    pair_diff = score_p1_pair - score_p2_pair
    if pair_diff > 0:
        verdict = f"{p1_short} WON MATCH"
    elif pair_diff < 0:
        verdict = f"{p2_short} WON MATCH"
    else:
        verdict = "MATCH TIED"

    phases = ["opening", "midgame", "pre_endgame", "endgame"]
    pair_phase_spreads = {}
    for ph in phases:
        p1_ph = res_a.get("phase_scores", {}).get(ph, {}).get("p1", 0) + res_b.get("phase_scores", {}).get(ph, {}).get("p2", 0)
        p2_ph = res_a.get("phase_scores", {}).get(ph, {}).get("p2", 0) + res_b.get("phase_scores", {}).get(ph, {}).get("p1", 0)
        pair_phase_spreads[ph] = (p1_ph - p2_ph) / 2.0

    return {
        "pair": task["pair_idx"] + 1,
        "seed": seed,
        "p1_name": p1_name,
        "p1_short": p1_short,
        "p2_name": p2_name,
        "p2_short": p2_short,
        "p1_gameA_score": res_a["p1_score"],
        "p1_gameB_score": res_b["p2_score"],
        "p1_pair_total": score_p1_pair,
        "p2_gameA_score": res_a["p2_score"],
        "p2_gameB_score": res_b["p1_score"],
        "p2_pair_total": score_p2_pair,
        "p1_bingos": bingos_p1_pair,
        "p2_bingos": bingos_p2_pair,
        "net_spread": pair_diff,
        "phase_spreads": pair_phase_spreads,
        "verdict": verdict,
    }


def run_parallel_duplicate_tournament(
    p1_spec: str = "hybrid-pimc",
    p2_spec: str = "magpie-tuned",
    num_pairs: int = 10,
    workers: int = 4,
    lexicon: str = "CSW24",
    device: str = "cpu",
    start_seed: int = 1000,
    seed_stride: int = 31,
    p1_kwargs: Optional[Dict[str, Any]] = None,
    p2_kwargs: Optional[Dict[str, Any]] = None,
    p1_model_path: Optional[str] = None,
    p2_model_path: Optional[str] = None,
    checkpoint_path: Optional[str] = None,
    resume: bool = False,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Executes a parallel paired duplicate tournament across multiple CPU processes.
    Supports atomic incremental checkpointing and recovery.
    """
    total_games = num_pairs * 2
    t_start = time.time()

    # Setup checkpoint manager
    ckpt_mgr: Optional[TournamentCheckpointManager] = None
    completed_seeds = set()
    pair_records: List[Dict[str, Any]] = []

    if checkpoint_path:
        meta = {
            "p1_spec": p1_spec,
            "p2_spec": p2_spec,
            "total_pairs": num_pairs,
            "lexicon": lexicon,
            "start_seed": start_seed,
            "seed_stride": seed_stride,
        }
        ckpt_mgr = TournamentCheckpointManager(checkpoint_path, metadata=meta)
        if resume:
            completed_seeds, existing_records = ckpt_mgr.load_completed_pairs()
            pair_records.extend(existing_records)
            if verbose and existing_records:
                print(f"[Checkpoint] Resumed {len(existing_records)}/{num_pairs} pairs from {checkpoint_path}")

    # Prepare task list
    tasks = []
    for p in range(num_pairs):
        seed = start_seed + p * seed_stride
        if seed in completed_seeds:
            continue
        tasks.append({
            "pair_idx": p,
            "seed": seed,
            "p1_spec": p1_spec,
            "p2_spec": p2_spec,
            "lexicon": lexicon,
            "device": device,
            "p1_kwargs": p1_kwargs or {},
            "p2_kwargs": p2_kwargs or {},
            "p1_model_path": p1_model_path,
            "p2_model_path": p2_model_path,
        })

    if verbose:
        print(f"Running {len(tasks)} remaining pairs across {workers} parallel worker processes...")

    if tasks:
        # Run worker tasks in parallel
        max_workers = min(workers, len(tasks))
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {executor.submit(_run_duplicate_pair_worker, t): t for t in tasks}
            for future in concurrent.futures.as_completed(future_to_task):
                task_info = future_to_task[future]
                try:
                    rec = future.result()
                    pair_records.append(rec)
                    if ckpt_mgr is not None:
                        ckpt_mgr.record_pair(rec)

                    if verbose:
                        print(
                            f"Pair {rec['pair']:02d}/{num_pairs:02d} [Seed {rec['seed']}]: "
                            f"{rec['p1_short']} {rec['p1_gameA_score']}+{rec['p1_gameB_score']}={rec['p1_pair_total']} pts vs "
                            f"{rec['p2_short']} {rec['p2_gameA_score']}+{rec['p2_gameB_score']}={rec['p2_pair_total']} pts | "
                            f"Net: {rec['net_spread']:+d} pts | {rec['verdict']}"
                        )
                except Exception as exc:
                    print(f"Worker generated an exception for Pair {task_info['pair_idx']+1} (Seed {task_info['seed']}): {exc}")
                    raise exc

    # Sort records by pair index
    pair_records.sort(key=lambda r: r["pair"])
    dt = time.time() - t_start

    # Compute aggregate statistics
    actual_pairs = len(pair_records)
    p1_pair_wins = sum(1 for r in pair_records if r["net_spread"] > 0)
    p2_pair_wins = sum(1 for r in pair_records if r["net_spread"] < 0)
    pair_draws = sum(1 for r in pair_records if r["net_spread"] == 0)

    pair_win_pct = (p1_pair_wins + 0.5 * pair_draws) / max(1, actual_pairs) * 100.0

    pair_diffs_per_game = np.array([r["net_spread"] for r in pair_records]) / 2.0 if actual_pairs > 0 else np.array([0.0])
    mean_dup_spread = float(np.mean(pair_diffs_per_game)) if actual_pairs > 0 else 0.0
    std_dup_spread = float(np.std(pair_diffs_per_game, ddof=1)) if actual_pairs > 1 else 0.0
    se_dup_spread = std_dup_spread / np.sqrt(actual_pairs) if actual_pairs > 0 else 0.0
    ci95_dup_spread = 1.96 * se_dup_spread
    t_dup = mean_dup_spread / se_dup_spread if se_dup_spread > 0 else 0.0
    p_val_dup = float(st.t.sf(abs(t_dup), df=max(1, actual_pairs - 1)) * 2.0) if actual_pairs > 1 else 1.0

    p_win_dup = (p1_pair_wins + 0.5 * pair_draws) / max(1, actual_pairs) if actual_pairs > 0 else 0.0
    se_win_dup = np.sqrt(p_win_dup * (1.0 - p_win_dup) / actual_pairs) if actual_pairs > 0 else 0.0
    ci95_win_dup = 1.96 * se_win_dup * 100.0

    phases = ["opening", "midgame", "pre_endgame", "endgame"]
    phase_means = {
        ph: float(np.mean([r.get("phase_spreads", {}).get(ph, 0.0) for r in pair_records]))
        if actual_pairs > 0 else 0.0
        for ph in phases
    }

    p1_name = pair_records[0]["p1_name"] if pair_records else p1_spec
    p1_short = pair_records[0]["p1_short"] if pair_records else p1_spec
    p2_name = pair_records[0]["p2_name"] if pair_records else p2_spec
    p2_short = pair_records[0]["p2_short"] if pair_records else p2_spec

    p1_total_scores = [r["p1_pair_total"] / 2.0 for r in pair_records]
    p2_total_scores = [r["p2_pair_total"] / 2.0 for r in pair_records]
    p1_all_bingos = sum(r.get("p1_bingos", 0) for r in pair_records)
    p2_all_bingos = sum(r.get("p2_bingos", 0) for r in pair_records)

    return {
        "mode": "duplicate",
        "total_games": actual_pairs * 2,
        "duplicate_pairs": actual_pairs,
        "duration_seconds": dt,
        "seconds_per_game": dt / max(1, actual_pairs * 2),
        "workers": workers,
        "p1_name": p1_name,
        "p1_short": p1_short,
        "p2_name": p2_name,
        "p2_short": p2_short,
        "p1_pair_wins": p1_pair_wins,
        "p2_pair_wins": p2_pair_wins,
        "pair_draws": pair_draws,
        "pair_win_pct": pair_win_pct,
        "ci95_win_pct": ci95_win_dup,
        "p1_mean_score": float(np.mean(p1_total_scores)) if p1_total_scores else 0.0,
        "p2_mean_score": float(np.mean(p2_total_scores)) if p2_total_scores else 0.0,
        "p1_bingos_per_game": p1_all_bingos / max(1, actual_pairs * 2),
        "p2_bingos_per_game": p2_all_bingos / max(1, actual_pairs * 2),
        "net_spread_mean": mean_dup_spread,
        "net_spread_ci95": ci95_dup_spread,
        "t_statistic": t_dup,
        "p_value": p_val_dup,
        "phase_means": phase_means,
        "pair_records": pair_records,
    }
