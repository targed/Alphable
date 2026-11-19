"""
Enhanced BAMS vs Base MAGPIE Tournament Runner
"""
import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alphable.engine.magpie_bindings import MagpieEngine
from alphable.engine.move import Move
from alphable.engine.game_state import GameState
from alphable.search.bams import BAMSSearch, BAMSConfig
from alphable.platform.eval import GameSimulator

def run_tournament(n_games=30):
    engine = MagpieEngine(lexicon='CSW24')
    ckpt = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'alphable', 'models', 'checkpoints', 'v4_value_net_best.pt'))
    if not os.path.exists(ckpt):
        ckpt = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'models', 'checkpoints', 'v4_value_net_best.pt'))
    bams = BAMSSearch.from_checkpoint(
        engine,
        ckpt,
        config=BAMSConfig(
            num_samples=24,
            candidate_beam=16,
            candidate_beam_2ply=8,
            samples_2ply=14,
            max_static_deficit=3.5,
            opp_penalty_weight=0.12,
            value_weight=4.5,
            weight_2ply=0.18,
            use_volatility_control=True,
            volatility_weight=0.4,
            dynamic_beam=True,
            use_exact_endgame=True,
            use_pre_endgame=True,
            use_belief_tracker=True,
            nested_2ply=True,
        )
    )

    sim = GameSimulator(engine, lexicon='CSW24')
    bams_scores, magpie_scores = [], []
    bams_wins, magpie_wins, draws = 0, 0, 0
    stats = {'total_turns': 0, 'divergences': 0, 'endgame_solver_plays': 0}

    def bams_policy(s):
        cands = engine.generate_moves(game_state=s, max_candidates=5)
        top_m = cands[0] if cands else None
        bm, meta = bams.select_move(s)
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

    print(f"Starting {n_games}-game tournament: BAMS (Enhanced) vs Base MAGPIE (KLV)...", flush=True)
    for g in range(n_games):
        bams.opp_tracker.reset()
        seed = 2026 + g * 37
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
        print(f"Game {g+1:02d}/{n_games:02d} [{role}]: BAMS {bs} - {ms} MAGPIE | {w_str}", flush=True)

    wr = (bams_wins + 0.5 * draws) / n_games * 100
    mean_b = np.mean(bams_scores)
    mean_m = np.mean(magpie_scores)
    print("=" * 65, flush=True)
    print(f"TOURNAMENT SUMMARY ({n_games} Games)", flush=True)
    print(f"BAMS Record       : {bams_wins}W - {magpie_wins}L - {draws}D ({wr:.1f}% Win Rate)", flush=True)
    print(f"BAMS Mean Score   : {mean_b:.1f} pts", flush=True)
    print(f"MAGPIE Mean Score : {mean_m:.1f} pts", flush=True)
    print(f"Net Differential  : {mean_b - mean_m:+.1f} pts", flush=True)
    print(f"Divergence Rate   : {stats['divergences']}/{stats['total_turns']} turns ({stats['divergences']/stats['total_turns']*100:.1f}%)", flush=True)
    print(f"Endgame Solvers   : {stats['endgame_solver_plays']} plays", flush=True)
    print("=" * 65, flush=True)

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    run_tournament(n)
