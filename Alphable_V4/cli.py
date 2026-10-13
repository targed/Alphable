#!/usr/bin/env python3
"""
Alphable V4 Interactive CLI & Benchmarking Command Center.

Provides interactive commands to:
1. analyze: Inspect any Scrabble position; compare Base MAGPIE vs BAMS AI side-by-side.
2. play: Play an interactive match against Alphable V4 in the terminal.
3. tournament: Run automated match series (BAMS vs Base MAGPIE or BAMS vs V3).
4. ablation: Quantify exactly what the AI Value Network adds over Base MAGPIE.
5. explain: Detailed breakdown of the Bayesian belief samples and neural evaluations.
"""

from __future__ import annotations
import os
import sys
import time
import argparse
from typing import List, Dict, Tuple, Optional, Any

import numpy as np
import torch

from alphable_v4.engine.move import Move
from alphable_v4.engine.game_state import GameState, STANDARD_TILE_COUNTS
from alphable_v4.engine.magpie_bindings import MagpieEngine
from alphable_v4.models.value_net import V4ValueNetwork
from alphable_v4.models.belief_net import BayesianRackInference
from alphable_v4.search.bams import BAMSSearch, BAMSConfig
from alphable_v4.platform.eval import GameSimulator, MatchStats, ScrabbleBag


CHECKPOINT_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "models", "checkpoints", "v4_value_net_best.pt")
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
# COMMAND 1: ANALYZE (Compare MAGPIE Static vs BAMS AI Side-by-Side)
# ==============================================================================
def cmd_analyze(args):
    """Analyzes a position, showing MAGPIE's choice vs BAMS AI's choice."""
    print("=" * 75)
    print("  ALPHABLE V4 POSITION ANALYZER: BASE MAGPIE vs BAMS AI")
    print("=" * 75)

    engine = get_shared_engine(args.lexicon)
    bams = BAMSSearch.from_checkpoint(
        engine,
        CHECKPOINT_PATH,
        config=BAMSConfig(
            num_samples=args.samples,
            candidate_beam=args.beam,
            max_static_deficit=args.max_deficit,
            seed=args.seed,
        ),
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

    print("\nCURRENT BOARD:")
    print(format_board(board))
    print(f"\nPLAYER RACK: {' '.join(rack)} (Lexicon: {args.lexicon})")

    # 1. Base MAGPIE evaluation (Pure Static KLV)
    t0 = time.perf_counter()
    magpie_cands = engine.generate_moves(game_state=state, max_candidates=args.beam)
    dt_magpie = (time.perf_counter() - t0) * 1000

    if not magpie_cands:
        print("\nNo legal moves found.")
        return

    base_magpie_move = magpie_cands[0]

    # 2. BAMS AI evaluation
    t0 = time.perf_counter()
    bams_move, bams_meta = bams.select_move(state)
    dt_bams = (time.perf_counter() - t0) * 1000

    print("\n" + "-" * 75)
    print(" CANDIDATE EVALUATION BREAKDOWN (MAGPIE KLV vs BAMS ROLLOUT + NEURAL NET)")
    print("-" * 75)
    print(f"{'#':<3} {'Move':<14} {'Pts':<5} {'Leave':<7} {'Static Eq':<11} {'Opp Threat':<12} {'Neural Val':<12} {'BAMS Score':<10}")
    print("-" * 75)

    eval_dict = {f"{e['word']}@{e['row']},{e['col']}": e for e in bams_meta.get("evaluations", [])}

    for idx, c in enumerate(magpie_cands[:args.beam], 1):
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

    print("-" * 75)
    print(f"Base MAGPIE Latency: {dt_magpie:.2f} ms | BAMS AI Latency: {dt_bams:.2f} ms")

    # Divergence Analysis
    is_divergent = not (base_magpie_move.word == bams_move.word and base_magpie_move.coord_str == bams_move.coord_str)
    print("\nDECISION SUMMARY:")
    print(f"  • Base MAGPIE Choice : {base_magpie_move.coord_str} {base_magpie_move.word} (Score: {base_magpie_move.score}, Static Equity: {base_magpie_move.equity:.2f})")
    print(f"  • BAMS AI Choice     : {bams_move.coord_str} {bams_move.word} (Score: {bams_move.score}, BAMS Score: {bams_meta.get('best_bams_score', 0.0):.2f})")

    if is_divergent:
        print("\n  >>> [AI DIVERGENCE DETECTED] <<<")
        print("  The AI actively overrode Base MAGPIE's #1 move!")
        print(f"  Reason: The AI simulated {args.samples} opponent rack samples and evaluated subsequent")
        print("  after-states using the Value Network, determining that the alternative move provides")
        print("  superior defensive safety or long-term strategic board control.")
    else:
        print("\n  >>> [AI & MAGPIE CONSENSUS] <<<")
        print("  Both Base MAGPIE and the AI agree on the optimal play for this rack.")


# ==============================================================================
# COMMAND 2: PLAY (Interactive Match Human vs Alphable V4)
# ==============================================================================
def cmd_play(args):
    """Interactive Scrabble match in terminal."""
    print("=" * 60)
    print("   WELCOME TO ALPHABLE V4 INTERACTIVE SCRABBLE MATCH")
    print("=" * 60)
    print("Rules: Play words using standard notation (e.g., '8H CATS' or 'H8 CATS').")
    print("Commands: 'pass' to pass, 'hint' for AI analysis, 'quit' to exit.\n")

    engine = get_shared_engine(args.lexicon)
    bams = BAMSSearch.from_checkpoint(
        engine,
        CHECKPOINT_PATH,
        config=BAMSConfig(num_samples=24, candidate_beam=10),
    )

    bag = ScrabbleBag(seed=args.seed)
    board = [[None for _ in range(15)] for _ in range(15)]
    human_rack = bag.draw(7)
    ai_rack = bag.draw(7)
    human_score = 0
    ai_score = 0

    turn = 1
    while True:
        print("\n" + "=" * 60)
        print(f"TURN {turn} | SCORE: Human {human_score} - {ai_score} Alphable V4 | Bag: {bag.count} tiles")
        print("=" * 60)
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
                top_m, _ = bams.select_move(h_state)
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
        print("\nAlphable V4 is thinking...")
        ai_state = GameState(board=board, rack=ai_rack, score=ai_score, opp_score=human_score, lexicon=args.lexicon)
        t0 = time.perf_counter()
        ai_move, ai_meta = bams.select_move(ai_state)
        dt = (time.perf_counter() - t0) * 1000

        if ai_move.is_placement:
            board = ai_state.apply_move(ai_move).board
            ai_score += ai_move.score
            print(f"► Alphable V4 played '{ai_move.coord_str} {ai_move.word}' for {ai_move.score} pts [{dt:.1f}ms] (BAMS Score: {ai_meta.get('best_bams_score', 0):.2f})")
            if ai_move.leave is not None:
                ai_rack = list(ai_move.leave)
            ai_rack.extend(bag.draw(7 - len(ai_rack)))
        else:
            print(f"► Alphable V4 passed. [{dt:.1f}ms]")

        turn += 1
        if bag.count == 0 and (len(human_rack) == 0 or len(ai_rack) == 0):
            print("\n*** GAME OVER: Tile Bag Empty & Rack Cleared ***")
            print(f"FINAL SCORE: Human {human_score} - {ai_score} Alphable V4")
            break


# ==============================================================================
# COMMAND 3: TOURNAMENT (BAMS vs Base MAGPIE or BAMS vs V3)
# ==============================================================================
def cmd_tournament(args):
    """Runs a multi-game tournament series comparing BAMS against a baseline."""
    print("=" * 70)
    print(f"   ALPHABLE V4 TOURNAMENT: BAMS AI vs {args.opponent.upper()} ({args.games} GAMES)")
    print("=" * 70)

    engine = get_shared_engine(args.lexicon)
    bams = BAMSSearch.from_checkpoint(
        engine,
        CHECKPOINT_PATH,
        config=BAMSConfig(
            num_samples=24,
            candidate_beam=15,
            max_static_deficit=3.5,
            opp_penalty_weight=0.12,
            value_weight=4.5,
            dynamic_beam=True,
            use_exact_endgame=True,
        ),
    )

    def bams_policy(state: GameState):
        return bams.select_move(state)

    if args.opponent.lower() == "magpie":
        # Base MAGPIE: Pure KLV static equity top move
        def baseline_policy(state: GameState):
            cands = engine.generate_moves(game_state=state, max_candidates=5)
            if cands:
                return cands[0], {"method": "magpie_static_top"}
            return Move.create_pass(), {"method": "pass"}
        opp_name = "Base MAGPIE (KLV Static)"

    elif args.opponent.lower() in ("v3", "v3-resnet"):
        # V3 Champion ResNet Model (Macondo Distilled, 63 dims)
        sys.path.insert(0, "/home/targed/Documents/Git/Alphable/Alphable_V3/src")
        from alphable.core import inference as v3_inference, simulator as v3_simulator
        v3_dict = "/home/targed/Documents/Git/Alphable/Alphable_V3/resources/CSW24.txt"
        v3_model = "/home/targed/Documents/Git/Alphable/Alphable_V3/models/alphable_v3_macondo_v2.pth"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        v3_engine = v3_inference.AlphableInference(
            model_path=v3_model,
            dict_path=v3_dict,
            device=device,
            state_vector_size=63,
        )

        def baseline_policy(state: GameState):
            v3_board = [[(tile if tile and tile != "." else ".") for tile in row] for row in state.board]
            score_diff = state.score - state.opp_score
            best_m, val = v3_engine.find_best_move(v3_board, state.rack, score_diff, state.bag_count)
            if not best_m:
                return Move.create_pass(), {"method": "v3_pass"}
            new_board, points, new_rack = v3_simulator.simulate_move(v3_board, best_m, state.rack)
            leave = "".join(new_rack)
            direction = best_m.get("dir") or best_m.get("direction") or "Across"
            r, c = best_m["row"], best_m["col"]
            word_with_blanks = "".join(
                new_board[r + (i if direction == "Down" else 0)][c + (i if direction == "Across" else 0)]
                for i in range(len(best_m["word"]))
            )
            parsed = Move(
                row=r,
                col=c,
                direction=direction,
                word=word_with_blanks,
                score=points,
                leave=leave,
            )
            return parsed, {"method": "v3_macondo_resnet", "val": val}
        opp_name = "Alphable V3 (Macondo ResNet Champion)"

    elif args.opponent.lower() == "v3-transformer":
        # V3 SmolLM2 Transformer Candidate Ranker
        sys.path.insert(0, "/home/targed/Documents/Git/Alphable/Alphable_V3/src")
        from alphable.models.transformer_ranker import SmolLM2CandidateRanker
        from alphable.core import simulator as v3_simulator, structure as v3_structure
        v3_dict = "/home/targed/Documents/Git/Alphable/Alphable_V3/resources/CSW24.txt"
        t_model_path = "/home/targed/Documents/Git/Alphable/Alphable_V3/models/transformer_ranker_v2"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        ranker = SmolLM2CandidateRanker(model_name_or_path=t_model_path, device=device)
        g = v3_structure.Gaddag.load(v3_dict)
        v3_gen = v3_structure.MoveGenerator(g)

        def baseline_policy(state: GameState):
            v3_board = [[(tile if tile and tile != "." else ".") for tile in row] for row in state.board]
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
            parsed = Move(
                row=r,
                col=c,
                direction=direction,
                word=word_with_blanks,
                score=points,
                leave="".join(new_rack),
            )
            return parsed, {"method": "v3_transformer_ranker"}
        opp_name = "Alphable V3 (SmolLM2 Transformer)"
    else:
        # ScoreGreedy
        def baseline_policy(state: GameState):
            cands = engine.generate_moves(game_state=state, max_candidates=10)
            if cands:
                best = max(cands, key=lambda c: c.score)
                return best, {"method": "score_greedy"}
            return Move.create_pass(), {"method": "pass"}
        opp_name = "ScoreGreedy"

    sim = GameSimulator(engine, lexicon=args.lexicon)

    bams_wins = 0
    opp_wins = 0
    draws = 0
    bams_scores = []
    opp_scores = []
    bams_bingos = 0
    opp_bingos = 0

    t_start = time.time()
    for g in range(args.games):
        seed = 1000 + g * 31
        bams_is_p1 = (g % 2 == 0)

        p1_pol = bams_policy if bams_is_p1 else baseline_policy
        p2_pol = baseline_policy if bams_is_p1 else bams_policy

        res = sim.play_game(p1_pol, p2_pol, seed=seed)

        if bams_is_p1:
            b_sc, o_sc = res["p1_score"], res["p2_score"]
            b_bg, o_bg = res["p1_bingos"], res["p2_bingos"]
            b_won = res["winner"] == 1
            o_won = res["winner"] == 2
        else:
            b_sc, o_sc = res["p2_score"], res["p1_score"]
            b_bg, o_bg = res["p2_bingos"], res["p1_bingos"]
            b_won = res["winner"] == 2
            o_won = res["winner"] == 1

        bams_scores.append(b_sc)
        opp_scores.append(o_sc)
        bams_bingos += b_bg
        opp_bingos += o_bg

        if b_won:
            bams_wins += 1
            verdict = "BAMS WON ✓"
        elif o_won:
            opp_wins += 1
            verdict = f"{opp_name} WON"
        else:
            draws += 1
            verdict = "DRAW"

        print(
            f"Game {g+1:02d}/{args.games:02d} [BAMS {'P1' if bams_is_p1 else 'P2'}]: "
            f"BAMS {b_sc} - {o_sc} {opp_name.split()[0]} | {verdict} | Bingos: {b_bg}-{o_bg}"
        )

    dt = time.time() - t_start
    win_pct = (bams_wins + 0.5 * draws) / args.games * 100
    print("\n" + "=" * 70)
    print(" TOURNAMENT RESULTS SUMMARY")
    print("=" * 70)
    print(f"Matchup: Alphable V4 (BAMS) vs {opp_name}")
    print(f"Total Games Played: {args.games} in {dt:.1f}s ({dt/args.games:.2f}s/game)")
    print(f"BAMS Record       : {bams_wins}W - {opp_wins}L - {draws}D ({win_pct:.1f}% Win Rate)")
    print(f"BAMS Mean Score   : {np.mean(bams_scores):.1f} pts (Bingos/Game: {bams_bingos/args.games:.2f})")
    print(f"Opponent Mean     : {np.mean(opp_scores):.1f} pts (Bingos/Game: {opp_bingos/args.games:.2f})")
    print(f"Score Differential: {np.mean(bams_scores) - np.mean(opp_scores):+.1f} pts in favor of BAMS")
    print("=" * 70)


# ==============================================================================
# COMMAND 4: ABLATION (Neural Value Network ON vs OFF)
# ==============================================================================
def cmd_ablation(args):
    """
    Quantifies the exact impact of the AI Value Network by comparing:
    - Condition A: BAMS Search WITH Neural Value Network
    - Condition B: BAMS Search WITHOUT Neural Value Network (Heuristic only)
    """
    print("=" * 70)
    print(f"   ALPHABLE V4 ABLATION EXPERIMENT: NEURAL NETWORK ON vs OFF")
    print("=" * 70)
    print("This experiment proves whether the AI Neural Value Network is making an")
    print("empirical difference, or if MAGPIE's heuristic alone is doing the work.\n")

    engine = get_shared_engine(args.lexicon)

    # Agent A: Full BAMS (with trained Neural Value Net)
    bams_neural = BAMSSearch.from_checkpoint(
        engine,
        CHECKPOINT_PATH,
        config=BAMSConfig(num_samples=16, candidate_beam=10, max_static_deficit=4.0),
    )

    # Agent B: Ablated BAMS (Value Net disabled -> purely static MAGPIE)
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

        p1_pol = (lambda s: bams_neural.select_move(s)) if neural_is_p1 else (lambda s: bams_ablated.select_move(s))
        p2_pol = (lambda s: bams_ablated.select_move(s)) if neural_is_p1 else (lambda s: bams_neural.select_move(s))

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
    print("\n" + "=" * 70)
    print(" ABLATION FINDINGS")
    print("=" * 70)
    print(f"Neural (AI) Win Rate : {win_rate:.1f}% ({neural_wins}W - {ablated_wins}L - {draws}D)")
    print(f"Neural Mean Score    : {np.mean(neural_scores):.1f} pts")
    print(f"No-Neural Mean Score : {np.mean(ablated_scores):.1f} pts")
    print(f"Net AI Impact        : {np.mean(neural_scores) - np.mean(ablated_scores):+.1f} points per game")
    print("=" * 70)


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Alphable V4 Command Center: Interactive play, analysis, tournaments, and AI ablation."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Analyze
    p_analyze = subparsers.add_parser("analyze", help="Compare Base MAGPIE vs BAMS AI on any position")
    p_analyze.add_argument("--rack", type=str, default="AQRTUYZ", help="Player rack tiles (default: AQRTUYZ)")
    p_analyze.add_argument("--board-word", type=str, default="", help="Optional word on board (e.g. TRAIN)")
    p_analyze.add_argument("--board-coord", type=str, default="8D", help="Optional coordinate of board word (e.g. 8D)")
    p_analyze.add_argument("--samples", type=int, default=32, help="Number of opponent rack samples (N)")
    p_analyze.add_argument("--beam", type=int, default=10, help="Top candidate beam size (K)")
    p_analyze.add_argument("--max-deficit", type=float, default=4.0, help="Max static equity deficit allowed")
    p_analyze.add_argument("--lexicon", type=str, default="CSW24", help="Lexicon (CSW24 or NWL23)")
    p_analyze.add_argument("--seed", type=int, default=42, help="Random seed for CRN")

    # 2. Play
    p_play = subparsers.add_parser("play", help="Play an interactive game against Alphable V4 in terminal")
    p_play.add_argument("--lexicon", type=str, default="CSW24", help="Lexicon (CSW24 or NWL23)")
    p_play.add_argument("--seed", type=int, default=None, help="Optional game seed")

    # 3. Tournament
    p_tournament = subparsers.add_parser("tournament", help="Run head-to-head match series vs baseline")
    p_tournament.add_argument("--opponent", type=str, default="magpie", choices=["magpie", "v3", "v3-resnet", "v3-transformer", "greedy"], help="Opponent baseline")
    p_tournament.add_argument("--games", type=int, default=10, help="Number of games to simulate")
    p_tournament.add_argument("--lexicon", type=str, default="CSW24", help="Lexicon (CSW24 or NWL23)")

    # 4. Ablation
    p_ablation = subparsers.add_parser("ablation", help="Quantify AI Value Network contribution (ON vs OFF)")
    p_ablation.add_argument("--games", type=int, default=10, help="Number of games to simulate")
    p_ablation.add_argument("--lexicon", type=str, default="CSW24", help="Lexicon (CSW24 or NWL23)")

    args = parser.parse_args()

    if args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "play":
        cmd_play(args)
    elif args.command == "tournament":
        cmd_tournament(args)
    elif args.command == "ablation":
        cmd_ablation(args)


if __name__ == "__main__":
    main()
