import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alphable_v4.engine.magpie_bindings import MagpieEngine
from alphable_v4.engine.game_state import GameState
from alphable_v4.search.bams import BAMSSearch, BAMSConfig

engine = MagpieEngine(lexicon='CSW24')
ckpt = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'models', 'checkpoints', 'v4_value_net_best.pt'))
bams = BAMSSearch.from_checkpoint(
    engine,
    ckpt,
    config=BAMSConfig(num_samples=24, candidate_beam=10, max_static_deficit=4.0)
)

test_racks = ['AEINRST', 'BCOOTUY', 'AADENRZ', 'EFGHIJK', 'DEILNOR', 'AAEEPSS']
for r in test_racks:
    s = GameState(board=[[None]*15 for _ in range(15)], rack=list(r), lexicon='CSW24')
    cands = engine.generate_moves(game_state=s, max_candidates=10)
    top_magpie = cands[0]
    bams_m, meta = bams.select_move(s)
    diverged = (bams_m.coord_str != top_magpie.coord_str or bams_m.word != top_magpie.word)
    print(f"Rack {r}: Magpie={top_magpie.coord_str} {top_magpie.word} ({top_magpie.score}p, eq={top_magpie.equity:.2f}) | BAMS={bams_m.coord_str} {bams_m.word} ({bams_m.score}p, eq={bams_m.equity:.2f}) | Diverged={diverged}")
