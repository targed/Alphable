#!/usr/bin/env python3
"""
scratch/diagnose_divergence.py
Diagnoses move choices of Hybrid PIMC vs Tuned MAGPIE on identical board states.
"""

from alphable.engine.magpie_bindings import MagpieEngine
from alphable.cli import build_policy
from alphable.platform.eval import GameSimulator, ScrabbleBag, get_game_phase
from alphable.engine.game_state import GameState

def diagnose():
    eng_sim = MagpieEngine(lexicon="CSW24")
    eng_tuned = MagpieEngine(lexicon="CSW24")
    eng_hybrid = MagpieEngine(lexicon="CSW24")

    tuned_policy, _, _ = build_policy(eng_tuned, spec="magpie-tuned")
    hybrid_policy, _, _ = build_policy(eng_hybrid, spec="hybrid-pimc")

    bag = ScrabbleBag(seed=1000)
    board = [[None for _ in range(15)] for _ in range(15)]
    p1_rack = bag.draw(7)
    p2_rack = bag.draw(7)
    p1_score, p2_score = 0, 0
    scoreless = 0

    divergences = []

    for turn_num in range(1, 35):
        # State for P1
        state_p1 = GameState(
            board=board, rack=p1_rack, opp_rack=p2_rack,
            score=p1_score, opp_score=p2_score,
            scoreless_turns=scoreless, bag_count=bag.count, lexicon="CSW24"
        )
        
        # Test both policies on state_p1
        m_tuned, meta_tuned = tuned_policy(state_p1)
        m_hybrid, meta_hybrid = hybrid_policy(state_p1)

        diff = (m_tuned.coord_str != m_hybrid.coord_str or m_tuned.word != m_hybrid.word)
        if diff:
            divergences.append({
                "turn": turn_num,
                "player": 1,
                "bag": bag.count,
                "score_diff": p1_score - p2_score,
                "tuned_move": f"{m_tuned.coord_str} {m_tuned.word} (+{m_tuned.score})",
                "hybrid_move": f"{m_hybrid.coord_str} {m_hybrid.word} (+{m_hybrid.score})",
                "hybrid_meta": meta_hybrid,
            })

        # Apply m_tuned to advance game
        if m_tuned.is_pass:
            scoreless += 1
        elif m_tuned.is_exchange:
            for t in m_tuned.letters_exchanged:
                p1_rack.remove(t)
            drawn = bag.exchange(m_tuned.letters_exchanged)
            p1_rack.extend(drawn)
            scoreless += 1
        else:
            p1_score += m_tuned.score
            scoreless = 0
            # Place tiles
            dir_across = (m_tuned.direction == "Across")
            r, c = m_tuned.row, m_tuned.col
            for idx, ch in enumerate(m_tuned.word):
                curr_r = r if dir_across else r + idx
                curr_c = c + idx if dir_across else c
                if board[curr_r][curr_c] is None:
                    board[curr_r][curr_c] = ch
                    letter_to_remove = "?" if ch.islower() else ch
                    if letter_to_remove in p1_rack:
                        p1_rack.remove(letter_to_remove)
            drawn = bag.draw(7 - len(p1_rack))
            p1_rack.extend(drawn)

        if len(p1_rack) == 0 and bag.count == 0:
            break

        # Swap racks/scores for P2
        p1_rack, p2_rack = p2_rack, p1_rack
        p1_score, p2_score = p2_score, p1_score

    print(f"\nTotal Divergences: {len(divergences)}")
    for d in divergences[:8]:
        print(f"Turn {d['turn']:02d} (Bag {d['bag']:02d}, Diff {d['score_diff']:+03d}):")
        print(f"  Tuned : {d['tuned_move']}")
        print(f"  Hybrid: {d['hybrid_move']}")
        meta = d["hybrid_meta"]
        if "scored_candidates" in meta:
            for sc in meta["scored_candidates"]:
                c = sc["candidate"]
                print(f"    Cand {c.coord_str:3s} {c.word:8s} | comp={sc['composite_score']:.1f} | sim_eq={sc['sim_equity']:.1f} | wp={sc['win_prob']:.3f} | nn={sc['neural_val']:.3f} | vol={sc['volatility']:.1f}")

if __name__ == "__main__":
    diagnose()
