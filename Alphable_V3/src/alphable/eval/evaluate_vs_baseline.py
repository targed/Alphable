import argparse
import json
import os
import random
from datetime import datetime

import torch

from alphable.core import inference
from alphable.core import simulator
from alphable.logging.game_logger import GameLogger
from alphable.core.search import AlphableSearch
from alphable.training.self_play import apply_endgame_adjustments, build_bag, draw_tiles, evaluate_moves


def board_to_visualizer_string(board):
    lines = []
    for r in range(15):
        row_cells = " ".join(board[r])
        lines.append(f"{r:2d} {row_cells}")
    return "\n".join(lines)


def move_to_desc(move):
    return f"Plays '{move['word']}' at {move['row']},{move['col']} {move['dir']}"


def choose_baseline_move(opponent, legal_moves, board, rack):
    if not legal_moves:
        return None

    if opponent == 'random':
        return random.choice(legal_moves)

    if opponent == 'greedy':
        best = None
        best_points = -1
        for move in legal_moves:
            _, points, _ = simulator.simulate_move(board, move, rack)
            if points > best_points:
                best_points = points
                best = move
        return best

    raise ValueError(f"Unknown opponent type: {opponent}")


def run_game(
    game_idx,
    engine,
    searcher,
    opponent,
    output_dir,
    timestamp,
    max_turns,
    infer_batch_size,
):
    board = simulator.create_empty_board()
    bag = build_bag()
    racks = [draw_tiles(bag, 7), draw_tiles(bag, 7)]
    scores = [0, 0]
    consecutive_passes = 0

    alphable_first = game_idx % 2 == 0
    p0_name = 'Alphable' if alphable_first else opponent.capitalize()
    p1_name = opponent.capitalize() if alphable_first else 'Alphable'

    logger = GameLogger(p0_name, p1_name)
    logger.set_metadata(
        match_type=f"Alphable_vs_{opponent}",
        mode=searcher.mode,
        model_path=getattr(engine, 'model_path', 'unknown'),
        simulations=searcher.num_simulations,
        top_k=searcher.top_k_candidates,
        opp_reply_top_k=searcher.opp_reply_top_k,
    )

    txt_path = os.path.join(output_dir, f"game{game_idx+1}_{timestamp}.txt")
    json_path = os.path.join(output_dir, f"game{game_idx+1}_{timestamp}.json")

    move_count = 0
    with open(txt_path, 'w', encoding='utf-8') as logtxt:
        logtxt.write("=" * 70 + "\n")
        logtxt.write(f"Alphable vs {opponent.capitalize()}\n")
        logtxt.write(f"Game {game_idx+1}\n")
        logtxt.write(f"Player 0: {p0_name}\n")
        logtxt.write(f"Player 1: {p1_name}\n")
        logtxt.write("=" * 70 + "\n\n")

        for turn_index in range(max_turns):
            player = turn_index % 2
            is_alphable_turn = (player == 0 and alphable_first) or (
                player == 1 and not alphable_first)
            rack_before = racks[player].copy()
            score_before = scores[player]
            tiles_in_bag = len(bag)

            score_diff = scores[player] - scores[1 - player]
            legal_moves = engine.move_gen.generate(board, racks[player])

            chosen_move = None
            chosen_value = None
            top_candidates = []

            if is_alphable_turn:
                move_evals = evaluate_moves(
                    engine,
                    board,
                    racks[player],
                    score_diff,
                    tiles_in_bag,
                    infer_batch_size=infer_batch_size,
                )
                top_candidates = [
                    {
                        'word': m['move']['word'],
                        'row': m['move']['row'],
                        'col': m['move']['col'],
                        'dir': m['move']['dir'],
                        'value': round(m['value'], 4),
                        'points': m['points'],
                    }
                    for m in move_evals[:3]
                ]

                if move_evals:
                    if searcher.mode == 'bc_0ply':
                        selected = move_evals[0]
                        chosen_move = selected['move']
                        chosen_value = selected['value']
                    else:
                        best_move, best_val = searcher.find_best_move(
                            board,
                            racks[player],
                            score_diff,
                            tiles_in_bag,
                        )
                        chosen_move = best_move
                        chosen_value = best_val
                action_id = 0 if chosen_move else -1
            else:
                chosen_move = choose_baseline_move(
                    opponent, legal_moves, board, racks[player])
                action_id = 0 if chosen_move else -1

            action_type = 'PASS'
            word = None
            position = None
            direction = None

            if chosen_move is None:
                consecutive_passes += 1
                score_delta = 0
            else:
                action_type = 'PLAY'
                word = chosen_move['word']
                position = (chosen_move['row'], chosen_move['col'])
                direction = chosen_move['dir']

                board, points, new_rack = simulator.simulate_move(
                    board, chosen_move, racks[player])
                scores[player] += points
                racks[player] = new_rack
                racks[player].extend(draw_tiles(bag, 7 - len(racks[player])))
                score_delta = scores[player] - score_before
                consecutive_passes = 0
                move_count += 1

            board_state = board_to_visualizer_string(board)
            rack_after = racks[player].copy()

            logger.log_move(
                turn_index=turn_index,
                player=player,
                action_type=action_type,
                action_id=action_id,
                word=word,
                position=position,
                direction=direction,
                score=score_delta,
                rack_before=rack_before,
                rack_after=rack_after,
                board_state=board_state,
                tiles_in_bag=len(bag),
                consecutive_passes=consecutive_passes,
                additional_info={
                    'is_alphable_turn': is_alphable_turn,
                    'alphable_value': round(chosen_value, 4) if chosen_value is not None else None,
                    'top_candidates': top_candidates,
                },
            )

            if chosen_move is None:
                logtxt.write(f"Turn {turn_index+1} P{player}: PASS\n")
            else:
                who = 'Alphable' if is_alphable_turn else opponent.capitalize()
                line = f"Turn {turn_index+1} P{player} ({who}): {move_to_desc(chosen_move)} (+{score_delta})"
                if chosen_value is not None:
                    line += f" [value={chosen_value:.3f}]"
                logtxt.write(line + "\n")
                if top_candidates:
                    logtxt.write(f"   Top candidates: {top_candidates}\n")

            if consecutive_passes >= 2:
                logtxt.write("Game ended by consecutive passes.\n")
                break

            if len(bag) == 0 and (len(racks[0]) == 0 or len(racks[1]) == 0):
                logtxt.write("Game ended by empty rack in endgame.\n")
                break

        apply_endgame_adjustments(scores, racks)

        logger.set_final_score([scores[0], scores[1]])
        stats = logger.get_statistics()

        az_idx = 0 if alphable_first else 1
        opp_idx = 1 - az_idx
        az_score = scores[az_idx]
        opp_score = scores[opp_idx]

        logtxt.write("\n" + "=" * 70 + "\n")
        logtxt.write("FINAL RESULTS\n")
        logtxt.write("=" * 70 + "\n")
        logtxt.write(f"Total Played Moves: {move_count}\n")
        logtxt.write(f"Alphable Score: {az_score}\n")
        logtxt.write(f"{opponent.capitalize()} Score: {opp_score}\n")
        logtxt.write(
            f"Alphable Bingos: {stats['player_stats'][az_idx]['bingos']}\n")
        logtxt.write(
            f"{opponent.capitalize()} Bingos: {stats['player_stats'][opp_idx]['bingos']}\n")

        if az_score > opp_score:
            logtxt.write(
                f"Winner: Alphable (by {az_score - opp_score} points)\n")
            alphable_won = True
        elif opp_score > az_score:
            logtxt.write(
                f"Winner: {opponent.capitalize()} (by {opp_score - az_score} points)\n")
            alphable_won = False
        else:
            logtxt.write("Result: TIE\n")
            alphable_won = False

    logger.save_json(json_path)
    summary = {
        'game_index': game_idx + 1,
        'game_id': logger.game_id,
        'timestamp': logger.timestamp,
        'players': logger.player_names,
        'opponent': opponent,
        'mode': searcher.mode,
        'winner': 'alphable' if az_score > opp_score else (
            opponent if opp_score > az_score else 'tie'
        ),
        'alphable_won': alphable_won,
        'tie': az_score == opp_score,
        'alphable_score': az_score,
        'opponent_score': opp_score,
        'score_margin': az_score - opp_score,
        'total_played_moves': move_count,
        'alphable_bingos': stats['player_stats'][az_idx]['bingos'],
        'opponent_bingos': stats['player_stats'][opp_idx]['bingos'],
        'alphable_avg_score_per_move': stats['player_stats'][az_idx]['average_score_per_move'],
        'opponent_avg_score_per_move': stats['player_stats'][opp_idx]['average_score_per_move'],
        'replay_json': os.path.abspath(json_path),
        'replay_txt': os.path.abspath(txt_path),
    }

    summaries_dir = os.path.join(output_dir, 'summaries')
    os.makedirs(summaries_dir, exist_ok=True)
    summary_path = os.path.join(
        summaries_dir,
        f"game{game_idx+1}_{timestamp}_summary.json",
    )
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    return {
        'alphable_won': alphable_won,
        'az_score': az_score,
        'opp_score': opp_score,
        'txt_path': txt_path,
        'json_path': json_path,
        'summary_path': summary_path,
    }


def evaluate(args):
    os.makedirs(args.output_dir, exist_ok=True)

    random.seed(args.seed)
    torch.manual_seed(args.seed)

    device = args.device
    if device == 'auto':
        device = 'cuda' if torch.cuda.is_available() else 'cpu'

    if not os.path.exists(args.model):
        raise FileNotFoundError(f"Model not found: {args.model}")

    print(f"Loading model from {args.model}")
    engine = inference.AlphableInference(
        model_path=args.model,
        device=device,
        dict_path=args.dict,
    )
    engine.model_path = args.model

    searcher = AlphableSearch(
        engine,
        num_simulations=args.simulations,
        top_k_candidates=args.top_k,
        opp_reply_top_k=args.opp_reply_top_k,
        mode=args.mode,
        infer_batch_size=args.infer_batch_size,
    )

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    print(
        f"--- Alphable vs {args.opponent.capitalize()} ({args.games} games) ---")

    wins = 0
    ties = 0
    game_results = []
    for i in range(args.games):
        result = run_game(
            game_idx=i,
            engine=engine,
            searcher=searcher,
            opponent=args.opponent,
            output_dir=args.output_dir,
            timestamp=timestamp,
            max_turns=args.max_turns,
            infer_batch_size=args.infer_batch_size,
        )
        game_results.append(result)

        if result['az_score'] == result['opp_score']:
            ties += 1
            print(
                f"Game {i+1}: TIE ({result['az_score']} vs {result['opp_score']}) -> {result['json_path']}")
        elif result['alphable_won']:
            wins += 1
            print(
                f"Game {i+1}: Alphable wins ({result['az_score']} vs {result['opp_score']}) -> {result['json_path']}")
        else:
            print(
                f"Game {i+1}: {args.opponent.capitalize()} wins ({result['opp_score']} vs {result['az_score']}) -> {result['json_path']}")

    losses = args.games - wins - ties
    run_summary = {
        'timestamp': timestamp,
        'opponent': args.opponent,
        'model': os.path.abspath(args.model),
        'mode': args.mode,
        'games': args.games,
        'wins': wins,
        'losses': losses,
        'ties': ties,
        'win_rate': (wins / args.games) if args.games > 0 else 0.0,
        'avg_margin': (
            sum(r['az_score'] - r['opp_score']
                for r in game_results) / len(game_results)
            if game_results else 0.0
        ),
        'output_dir': os.path.abspath(args.output_dir),
        'game_summaries': [r['summary_path'] for r in game_results],
    }

    summaries_dir = os.path.join(args.output_dir, 'summaries')
    os.makedirs(summaries_dir, exist_ok=True)
    run_summary_path = os.path.join(
        summaries_dir,
        f"run_{timestamp}_summary.json",
    )
    with open(run_summary_path, 'w', encoding='utf-8') as f:
        json.dump(run_summary, f, indent=2)

    print("\n=== Summary ===")
    print(f"Win Rate: {wins}/{args.games}")
    print(f"Losses: {losses}")
    print(f"Ties: {ties}")
    print(f"Logs directory: {args.output_dir}")
    print(f"Run summary: {run_summary_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate Alphable V2 vs a baseline and log replay files.')
    parser.add_argument(
        '--model', default='models/alphable_rl_best_val_model.pth')
    parser.add_argument(
        '--opponent', choices=['random', 'greedy'], required=True)
    parser.add_argument('--games', type=int, default=5)
    parser.add_argument(
        '--mode', choices=['bc_0ply', 'lookahead'], default='lookahead')
    parser.add_argument('--simulations', type=int, default=16)
    parser.add_argument('--top-k', type=int, default=3)
    parser.add_argument('--opp-reply-top-k', type=int, default=5)
    parser.add_argument('--infer-batch-size', type=int, default=128)
    parser.add_argument('--dict', default='resources/CSW24.txt')
    parser.add_argument('--device', default='auto', help='auto|cpu|cuda')
    parser.add_argument('--max-turns', type=int, default=200)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output-dir', default=None,
                        help='Output directory for logs. If omitted, uses data/vs_<opponent>.')
    args = parser.parse_args()

    if args.output_dir is None:
        args.output_dir = os.path.join('data', f'vs_{args.opponent}')

    evaluate(args)


if __name__ == '__main__':
    main()
