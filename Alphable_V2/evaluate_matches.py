import argparse
import random

import inference
import simulator
import torch

from self_play import apply_endgame_adjustments, build_bag, draw_tiles


def evaluate_moves(engine, board, rack, score_diff, bag_remaining):
    moves = engine.move_gen.generate(board, rack)
    if not moves:
        return []

    batch_boards = []
    batch_states = []
    move_states = []

    for move in moves:
        new_board, points, new_rack = simulator.simulate_move(
            board, move, rack)
        new_score_diff = score_diff + points

        batch_boards.append(inference.board_to_tensor(new_board))
        batch_states.append(inference.state_to_tensor(
            new_rack, new_score_diff, bag_remaining))
        move_states.append((move, new_board, points, new_rack))

    b_tensors = torch.stack(batch_boards).to(engine.device)
    s_tensors = torch.stack(batch_states).to(engine.device)

    with torch.no_grad():
        vals = engine.model(b_tensors, s_tensors).view(-1)

    evals = []
    for i, (move, new_board, points, new_rack) in enumerate(move_states):
        evals.append({
            'move': move,
            'value': vals[i].item(),
            'new_board': new_board,
            'points': points,
            'new_rack': new_rack,
        })

    evals.sort(key=lambda x: x['value'], reverse=True)
    return evals


def choose_move(evals, temperature=0.0, top_k=3):
    if not evals:
        return None

    top = evals[:max(1, min(top_k, len(evals)))]
    if temperature <= 1e-6:
        return top[0]

    logits = torch.tensor([e['value'] for e in top], dtype=torch.float32)
    probs = torch.softmax(logits / temperature, dim=0)
    idx = torch.multinomial(probs, 1).item()
    return top[idx]


def play_match(engine_a, engine_b, temperature=0.0, top_k=3, max_turns=200):
    board = simulator.create_empty_board()
    bag = build_bag()
    racks = [draw_tiles(bag, 7), draw_tiles(bag, 7)]
    scores = [0, 0]
    consecutive_passes = 0

    for turn in range(max_turns):
        p = turn % 2
        o = 1 - p
        engine = engine_a if p == 0 else engine_b

        score_diff = scores[p] - scores[o]
        bag_remaining = len(bag)

        evals = evaluate_moves(
            engine, board, racks[p], score_diff, bag_remaining)
        chosen = choose_move(evals, temperature=temperature, top_k=top_k)

        if chosen is None:
            consecutive_passes += 1
        else:
            board = chosen['new_board']
            scores[p] += chosen['points']
            racks[p] = chosen['new_rack']
            racks[p].extend(draw_tiles(bag, 7 - len(racks[p])))
            consecutive_passes = 0

        if consecutive_passes >= 2:
            break

        if len(bag) == 0 and (len(racks[0]) == 0 or len(racks[1]) == 0):
            break

    apply_endgame_adjustments(scores, racks)
    return scores


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate two checkpoints by direct head-to-head matches.')
    parser.add_argument('--model-a', type=str, required=True,
                        help='Checkpoint path for model A (reported first).')
    parser.add_argument('--model-b', type=str, required=True,
                        help='Checkpoint path for model B (reported second).')
    parser.add_argument('--games', type=int, default=50,
                        help='Number of games to play.')
    parser.add_argument('--temperature', type=float,
                        default=0.0, help='Move sampling temperature.')
    parser.add_argument('--top-k', type=int, default=3,
                        help='Sampling pool size.')
    parser.add_argument(
        '--dict', type=str, default='resources/NWL2023.txt', help='Dictionary path.')
    parser.add_argument('--seed', type=int, default=42, help='Random seed.')
    args = parser.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f'Using device: {device}')

    engine_a = inference.AlphableInference(
        model_path=args.model_a, device=device, dict_path=args.dict)
    engine_b = inference.AlphableInference(
        model_path=args.model_b, device=device, dict_path=args.dict)

    wins_a = 0
    wins_b = 0
    draws = 0
    total_diff = 0

    for g in range(args.games):
        # Alternate first player to reduce first-move bias.
        if g % 2 == 0:
            s0, s1 = play_match(engine_a, engine_b,
                                temperature=args.temperature, top_k=args.top_k)
            diff_a = s0 - s1
        else:
            s0, s1 = play_match(engine_b, engine_a,
                                temperature=args.temperature, top_k=args.top_k)
            diff_a = s1 - s0

        total_diff += diff_a

        if diff_a > 0:
            wins_a += 1
        elif diff_a < 0:
            wins_b += 1
        else:
            draws += 1

    print('Evaluation complete.')
    print(
        f'Model A wins / Model B wins / draws: {wins_a} / {wins_b} / {draws}')
    print(f'Model A win rate: {wins_a / args.games:.3f}')
    print(f'Average score diff (A - B): {total_diff / args.games:.2f}')


if __name__ == '__main__':
    main()
