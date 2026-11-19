"""
Search Scaling Benchmark: Evaluating Deep 2-Ply Beam (K=12, N=20) vs Base MAGPIE.
"""
import sys
import os
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alphable.engine.magpie_bindings import MagpieEngine
from alphable.engine.move import Move
from alphable.engine.game_state import GameState
from alphable.search.bams import BAMSSearch, BAMSConfig
from alphable.platform.eval import GameSimulator

def run_scaling_benchmark(n_games=50):
    engine = MagpieEngine(lexicon='CSW24')
    ckpt = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'alphable', 'models', 'checkpoints', 'v4_value_net_best.pt'))
    if not os.path.exists(ckpt):
        ckpt = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'models', 'checkpoints', 'v4_value_net_best.pt'))
    
    # Deep Scaled 2-Ply BAMS Configuration
    scaled_config = BAMSConfig(
        num_samples=24,
        candidate_beam=20,
        candidate_beam_2ply=12,    # Expanded from 6 to 12
        samples_2ply=20,           # Expanded from 12 to 20
        max_static_deficit=4.0,
        opp_penalty_weight=0.12,
        value_weight=4.5,
        weight_2ply=0.18,
        dynamic_beam=True,
        use_exact_endgame=True,
        use_pre_endgame=True,
        use_belief_tracker=True,
        nested_2ply=True,
    )
    bams = BAMSSearch.from_checkpoint(engine, ckpt, config=scaled_config)
    sim = GameSimulator(engine, lexicon='CSW24')

    bams_scores, magpie_scores = [], []
    bams_wins, magpie_wins, draws = 0, 0, 0
    latencies = []
    stats = {'total_turns': 0, 'divergences': 0, 'endgame_solver_plays': 0}

    def bams_policy(s):
        cands = engine.generate_moves(game_state=s, max_candidates=5)
        top_m = cands[0] if cands else None
        t0 = time.perf_counter()
        bm, meta = bams.select_move(s)
        lat = (time.perf_counter() - t0) * 1000.0
        latencies.append(lat)
        stats['total_turns'] += 1
        if top_m and (bm.coord_str != top_m.coord_str or bm.word != top_m.word):
            stats['divergences'] += 1
        if meta.get('method') == 'exact_alphabeta_endgame':
            stats['endgame_solver_plays'] += 1
        return bm, meta

    def magpie_policy(s):
        c = engine.generate_moves(game_state=s, max_candidates=5)
        m = c[0] if c else Move.create_pass()
        bams.record_opponent_move(m, state_before=s)
        return m, {}

    print(f"======================================================================", flush=True)
    print(f" STARTING SCALED SEARCH BENCHMARK: BAMS (K=12, N=20) vs Base MAGPIE", flush=True)
    print(f" Total Games: {n_games} | Alternate Seats | CSW24 Lexicon", flush=True)
    print(f"======================================================================\n", flush=True)

    start_total = time.perf_counter()
    for g in range(n_games):
        bams.opp_tracker.reset()
        seed = 4000 + g * 43
        p1 = bams_policy if g % 2 == 0 else magpie_policy
        p2 = magpie_policy if g % 2 == 0 else bams_policy
        r = sim.play_game(p1, p2, seed=seed)
        bs = r['p1_score'] if g % 2 == 0 else r['p2_score']
        ms = r['p2_score'] if g % 2 == 0 else r['p1_score']
        bams_scores.append(bs)
        magpie_scores.append(ms)
        role = 'P1' if g % 2 == 0 else 'P2'
        if bs > ms:
            bams_wins += 1
            w_str = 'BAMS WON ✓'
        elif ms > bs:
            magpie_wins += 1
            w_str = 'MAGPIE WON'
        else:
            draws += 1
            w_str = 'DRAW'
        print(f"Game {g+1:02d}/{n_games:02d} [{role}]: BAMS {bs} - {ms} MAGPIE | {w_str} (Diff: {bs - ms:+d})", flush=True)

    total_time = time.perf_counter() - start_total
    wr = (bams_wins + 0.5 * draws) / n_games * 100
    mean_b = np.mean(bams_scores)
    mean_m = np.mean(magpie_scores)
    mean_lat = np.mean(latencies) if latencies else 0.0

    print("\n" + "=" * 65, flush=True)
    print(f"SCALED SEARCH BENCHMARK SUMMARY ({n_games} Games in {total_time:.1f}s)", flush=True)
    print("=" * 65, flush=True)
    print(f"BAMS Record       : {bams_wins}W - {magpie_wins}L - {draws}D ({wr:.1f}% Win Rate)", flush=True)
    print(f"BAMS Mean Score   : {mean_b:.1f} pts", flush=True)
    print(f"MAGPIE Mean Score : {mean_m:.1f} pts", flush=True)
    print(f"Net Differential  : {mean_b - mean_m:+.1f} pts in favor of BAMS", flush=True)
    print(f"Mean Turn Latency : {mean_lat:.1f} ms/turn ({total_time/n_games:.2f} s/game)", flush=True)
    print(f"Divergence Rate   : {stats['divergences']}/{stats['total_turns']} turns ({stats['divergences']/stats['total_turns']*100:.1f}%)", flush=True)
    print(f"Endgame Solvers   : {stats['endgame_solver_plays']} plays", flush=True)
    print("=" * 65, flush=True)

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    run_scaling_benchmark(n)
