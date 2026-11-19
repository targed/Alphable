"""
Phase 3 Benchmark Tournament Series: Alphable V4 (BAMS) vs Static Greedy.

Alternates first/second turn across games to ensure fair evaluation without first-turn bias.
Logs:
- Win rate
- Mean scores
- Bingos per game
- Invalid moves
"""

import os
import sys
import time

from alphable.engine.game_state import GameState
from alphable.engine.move import Move
from alphable.engine.magpie_bindings import MagpieEngine
from alphable.search.bams import BAMSSearch, BAMSConfig
from alphable.platform.eval import GameSimulator, MatchStats


def run_benchmark(num_games: int = 20):
    print(f"=== Alphable V4 Phase 3 Benchmark Series ({num_games} games) ===")
    engine = MagpieEngine(lexicon="CSW24")
    checkpoint_path = "alphable/models/checkpoints/v4_value_net_best.pt"
    if not os.path.exists(checkpoint_path):
        checkpoint_path = "models/checkpoints/v4_value_net_best.pt"

    bams = BAMSSearch.from_checkpoint(
        engine,
        checkpoint_path,
        config=BAMSConfig(num_samples=24, candidate_beam=10, value_weight=20.0),
    )

    def bams_policy(state: GameState):
        return bams.select_move(state)

    def greedy_policy(state: GameState):
        cands = engine.generate_moves(game_state=state, max_candidates=10)
        if cands:
            return cands[0], {"method": "static_top"}
        return Move.create_pass(), {"method": "pass"}

    sim = GameSimulator(engine, lexicon="CSW24")

    bams_wins = 0
    greedy_wins = 0
    draws = 0
    bams_scores = []
    greedy_scores = []
    bams_bingos = 0
    greedy_bingos = 0
    bams_invalids = 0

    t_start = time.time()
    for g in range(num_games):
        seed = 42 + g * 17
        # Alternate who goes first
        bams_is_p1 = (g % 2 == 0)

        p1_pol = bams_policy if bams_is_p1 else greedy_policy
        p2_pol = greedy_policy if bams_is_p1 else bams_policy

        res = sim.play_game(p1_pol, p2_pol, seed=seed)

        if bams_is_p1:
            b_score = res["p1_score"]
            g_score = res["p2_score"]
            b_bingo = res["p1_bingos"]
            g_bingo = res["p2_bingos"]
            b_inv = res["p1_invalid"]
            b_won = res["winner"] == 1
            g_won = res["winner"] == 2
        else:
            b_score = res["p2_score"]
            g_score = res["p1_score"]
            b_bingo = res["p2_bingos"]
            g_bingo = res["p1_bingos"]
            b_inv = res["p2_invalid"]
            b_won = res["winner"] == 2
            g_won = res["winner"] == 1

        bams_scores.append(b_score)
        greedy_scores.append(g_score)
        bams_bingos += b_bingo
        greedy_bingos += g_bingo
        bams_invalids += b_inv

        if b_won:
            bams_wins += 1
            outcome = "BAMS WON"
        elif g_won:
            greedy_wins += 1
            outcome = "Greedy WON"
        else:
            draws += 1
            outcome = "DRAW"

        print(
            f"Game {g+1:02d}/{num_games:02d} [BAMS {'P1' if bams_is_p1 else 'P2'}]: "
            f"BAMS {b_score} - {g_score} Greedy | {outcome} | Bingos: {b_bingo}-{g_bingo}"
        )

    dt = time.time() - t_start
    win_rate = (bams_wins + 0.5 * draws) / num_games * 100
    mean_bams = sum(bams_scores) / num_games
    mean_greedy = sum(greedy_scores) / num_games
    bingos_per_game = bams_bingos / num_games

    print("\n================== SUMMARY ==================")
    print(f"Total Games: {num_games} in {dt:.1f}s ({dt/num_games:.2f}s/game)")
    print(f"BAMS Record: {bams_wins}W - {greedy_wins}L - {draws}D")
    print(f"BAMS Win Rate: {win_rate:.1f}% (Target >= 65.0%)")
    print(f"BAMS Mean Score: {mean_bams:.1f} (Target >= 450.0)")
    print(f"Greedy Mean Score: {mean_greedy:.1f}")
    print(f"BAMS Bingos/Game: {bingos_per_game:.2f} (Target >= 2.5)")
    print(f"BAMS Invalid Moves: {bams_invalids} (Target 0)")
    print("=============================================")


if __name__ == "__main__":
    run_benchmark(20)
