import argparse
import json
import os
import random
from collections import Counter

import torch
from tqdm import tqdm

import inference
import simulator


STANDARD_TILE_COUNTS = {
    'A': 9, 'B': 2, 'C': 2, 'D': 4, 'E': 12, 'F': 2, 'G': 3, 'H': 2,
    'I': 9, 'J': 1, 'K': 1, 'L': 4, 'M': 2, 'N': 6, 'O': 8, 'P': 2,
    'Q': 1, 'R': 6, 'S': 4, 'T': 6, 'U': 4, 'V': 2, 'W': 2, 'X': 1,
    'Y': 2, 'Z': 1, '?': 2,
}


def build_bag():
    bag = []
    for tile, count in STANDARD_TILE_COUNTS.items():
        bag.extend([tile] * count)
    random.shuffle(bag)
    return bag


def draw_tiles(bag, n):
    drawn = []
    for _ in range(min(n, len(bag))):
        drawn.append(bag.pop())
    return drawn


def compact_board(board):
    return ''.join(''.join(row) for row in board)


def evaluate_moves(engine, board, rack, score_diff, bag_remaining, infer_batch_size=256):
    moves = engine.move_gen.generate(board, rack)
    if not moves:
        return []

    move_states = []

    for move in moves:
        new_board, points, new_rack = simulator.simulate_move(
            board, move, rack)
        new_score_diff = score_diff + points

        move_states.append((move, new_board, points, new_rack, new_score_diff))

    vals = []
    with torch.no_grad():
        for i in range(0, len(move_states), infer_batch_size):
            chunk = move_states[i:i + infer_batch_size]
            b_tensors = torch.stack([
                inference.board_to_tensor(ms[1]) for ms in chunk
            ]).to(engine.device)
            s_tensors = torch.stack([
                inference.state_to_tensor(ms[3], ms[4], bag_remaining) for ms in chunk
            ]).to(engine.device)

            chunk_vals = engine.model(b_tensors, s_tensors).view(-1)
            vals.extend(chunk_vals.detach().cpu().tolist())

    evals = []
    for i, (move, new_board, points, new_rack, _) in enumerate(move_states):
        evals.append({
            'move': move,
            'value': vals[i],
            'new_board': new_board,
            'points': points,
            'new_rack': new_rack,
        })

    evals.sort(key=lambda x: x['value'], reverse=True)
    return evals


def choose_move_with_temperature(move_evals, temperature=0.15, top_k=5):
    if not move_evals:
        return None

    top = move_evals[:max(1, min(top_k, len(move_evals)))]
    if temperature <= 1e-6:
        return top[0]

    logits = torch.tensor([m['value'] for m in top], dtype=torch.float32)
    probs = torch.softmax(logits / temperature, dim=0)
    idx = torch.multinomial(probs, num_samples=1).item()
    return top[idx]


def rack_penalty(rack):
    total = 0
    for t in rack:
        total += simulator.LETTER_VALUES.get(t.upper(), 0)
    return total


def apply_endgame_adjustments(scores, racks):
    p0_empty = len(racks[0]) == 0
    p1_empty = len(racks[1]) == 0

    if p0_empty and not p1_empty:
        bonus = rack_penalty(racks[1])
        scores[0] += bonus
        scores[1] -= bonus
    elif p1_empty and not p0_empty:
        bonus = rack_penalty(racks[0])
        scores[1] += bonus
        scores[0] -= bonus
    elif p0_empty and p1_empty:
        return


def play_one_game(engine, temperature=0.15, top_k=5, max_turns=200, infer_batch_size=256):
    board = simulator.create_empty_board()
    bag = build_bag()

    racks = [draw_tiles(bag, 7), draw_tiles(bag, 7)]
    scores = [0, 0]

    player_states = {0: [], 1: []}
    consecutive_passes = 0

    for turn in range(max_turns):
        p = turn % 2
        o = 1 - p

        score_diff = scores[p] - scores[o]
        bag_remaining = len(bag)

        # Save pre-move state from the current player's perspective.
        player_states[p].append({
            'board': compact_board(board),
            'rack': ''.join(racks[p]),
            'score_diff': score_diff,
            'bag': bag_remaining,
            'player': p,
        })

        move_evals = evaluate_moves(
            engine,
            board,
            racks[p],
            score_diff,
            bag_remaining,
            infer_batch_size=infer_batch_size,
        )
        selected = choose_move_with_temperature(
            move_evals, temperature=temperature, top_k=top_k)

        if selected is None:
            consecutive_passes += 1
        else:
            board = selected['new_board']
            scores[p] += selected['points']
            racks[p] = selected['new_rack']
            racks[p].extend(draw_tiles(bag, 7 - len(racks[p])))
            consecutive_passes = 0

        if consecutive_passes >= 2:
            break

        if len(bag) == 0 and (len(racks[0]) == 0 or len(racks[1]) == 0):
            break

    apply_endgame_adjustments(scores, racks)

    if scores[0] > scores[1]:
        result = {0: 1.0, 1: -1.0}
    elif scores[1] > scores[0]:
        result = {0: -1.0, 1: 1.0}
    else:
        result = {0: 0.0, 1: 0.0}

    samples = []
    for p in (0, 1):
        for s in player_states[p]:
            samples.append({
                'board': s['board'],
                'rack': s['rack'],
                'score_diff': s['score_diff'],
                'bag': s['bag'],
                'target': result[p],
            })

    return samples, scores


def main():
    parser = argparse.ArgumentParser(
        description='Generate RL training samples via self-play.')
    parser.add_argument('--games', type=int, default=1000,
                        help='Number of self-play games to generate.')
    parser.add_argument(
        '--output', type=str, default='data/rl/rl_samples.jsonl', help='Output jsonl path.')
    parser.add_argument(
        '--model', type=str, default='models/alphable_rl_best_val_model.pth', help='Starting model checkpoint.')
    parser.add_argument(
        '--dict', type=str, default='resources/NWL2023.txt', help='Dictionary path.')
    parser.add_argument('--temperature', type=float, default=0.20,
                        help='Sampling temperature for move selection.')
    parser.add_argument('--top-k', type=int, default=5,
                        help='Sample from top-k moves each turn.')
    parser.add_argument('--max-turns', type=int, default=200,
                        help='Max turns per game before forced stop.')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducibility.')
    parser.add_argument('--append', action='store_true',
                        help='Append to output instead of overwriting.')
    parser.add_argument('--infer-batch-size', type=int, default=256,
                        help='Inference batch size for move scoring to control GPU memory usage.')
    args = parser.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f'Using device: {device}')
    print(f'Loading model from: {args.model}')

    model_path = args.model
    if not os.path.exists(model_path):
        fallback_model = 'models/alphable_best_val_model.pth'
        if os.path.exists(fallback_model):
            print(
                f'Warning: model file not found at {model_path}. Falling back to {fallback_model}.')
            model_path = fallback_model
        else:
            print(
                f'Warning: model file not found at {model_path}. Using random weights.')
            model_path = None

    engine = inference.AlphableInference(
        model_path=model_path,
        device=device,
        dict_path=args.dict,
    )

    mode = 'a' if args.append else 'w'
    total_samples = 0
    p0_wins = 0
    p1_wins = 0
    draws = 0

    with open(args.output, mode) as out:
        for _ in tqdm(range(args.games), desc='Self-play games'):
            samples, scores = play_one_game(
                engine,
                temperature=args.temperature,
                top_k=args.top_k,
                max_turns=args.max_turns,
                infer_batch_size=args.infer_batch_size,
            )

            for s in samples:
                out.write(json.dumps(s) + '\n')

            total_samples += len(samples)
            if scores[0] > scores[1]:
                p0_wins += 1
            elif scores[1] > scores[0]:
                p1_wins += 1
            else:
                draws += 1

    print('Self-play generation complete.')
    print(f'Games: {args.games}')
    print(f'Samples written: {total_samples}')
    print(f'P0 wins / P1 wins / draws: {p0_wins} / {p1_wins} / {draws}')
    print(f'Output: {args.output}')


if __name__ == '__main__':
    main()
