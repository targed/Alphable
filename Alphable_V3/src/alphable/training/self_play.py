import argparse
import json
import os
import random
import math
from multiprocessing import Pool
from collections import defaultdict

import torch
from tqdm import tqdm

from alphable.core import inference
from alphable.core import simulator
from alphable.core.leave_eval import compute_leave_equity


STANDARD_TILE_COUNTS = {
    'A': 9, 'B': 2, 'C': 2, 'D': 4, 'E': 12, 'F': 2, 'G': 3, 'H': 2,
    'I': 9, 'J': 1, 'K': 1, 'L': 4, 'M': 2, 'N': 6, 'O': 8, 'P': 2,
    'Q': 1, 'R': 6, 'S': 4, 'T': 6, 'U': 4, 'V': 2, 'W': 2, 'X': 1,
    'Y': 2, 'Z': 1, '?': 2,
}


_WORKER_CFG = None
_WORKER_ENGINE_CACHE = None


def build_bag(rng=None):
    if rng is None:
        rng = random
    bag = []
    for tile, count in STANDARD_TILE_COUNTS.items():
        bag.extend([tile] * count)
    rng.shuffle(bag)
    return bag


def draw_tiles(bag, n):
    drawn = []
    for _ in range(min(n, len(bag))):
        drawn.append(bag.pop())
    return drawn


def compact_board(board):
    return ''.join(''.join(row) for row in board)


def evaluate_moves(engine, board, rack, score_diff, bag_remaining, infer_batch_size=256, value_weight=25.0, unseen_counts=None):
    """
    Evaluates all legal moves for a given state using batched GPU inference.
    Returns sorted list of move evaluations with both raw points and equity.
    """
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
            s_vec_size = getattr(engine, 'state_vector_size', 36)
            s_tensors = torch.stack([
                inference.state_to_tensor(
                    ms[3], ms[4], bag_remaining,
                    unseen_counts=unseen_counts,
                    state_vector_size=s_vec_size,
                ) for ms in chunk
            ]).to(engine.device)

            chunk_vals = engine.model(b_tensors, s_tensors).view(-1)
            vals.append(chunk_vals)

    all_vals = torch.cat(vals) if vals else torch.empty(0, device=engine.device)
    points_tensor = torch.tensor([ms[2] for ms in move_states], dtype=torch.float32, device=engine.device)
    leave_tensor = torch.tensor([compute_leave_equity(ms[3], bag_remaining=bag_remaining) for ms in move_states], dtype=torch.float32, device=engine.device)
    w = float(value_weight if value_weight is not None else getattr(engine, 'value_weight', 25.0))
    equities = points_tensor + leave_tensor + w * all_vals

    sorted_indices = torch.argsort(equities, descending=True).cpu().tolist()
    vals_cpu = all_vals.cpu().tolist()
    equities_cpu = equities.cpu().tolist()

    evals = [
        {
            'move': move_states[idx][0],
            'value': vals_cpu[idx],
            'equity': equities_cpu[idx],
            'new_board': move_states[idx][1],
            'points': move_states[idx][2],
            'new_rack': move_states[idx][3],
        }
        for idx in sorted_indices
    ]
    return evals


def choose_move_with_temperature(move_evals, temperature=0.15, top_k=5):
    if not move_evals:
        return None

    top = move_evals[:max(1, min(top_k, len(move_evals)))]
    if temperature <= 1e-6:
        return top[0]

    scores = [m.get('equity', m.get('value', 0.0)) for m in top]
    has_equity = 'equity' in top[0]
    scale = 10.0 if has_equity else 1.0
    logits = torch.tensor([s / scale for s in scores], dtype=torch.float32)
    probs = torch.softmax(logits / temperature, dim=0)
    idx = torch.multinomial(probs, num_samples=1).item()
    return top[idx]


def choose_greedy_move(board, rack, move_gen):
    moves = move_gen.generate(board, rack)
    if not moves:
        return None

    best = None
    best_points = -1
    for move in moves:
        _, points, _ = simulator.simulate_move(board, move, rack)
        if points > best_points:
            best_points = points
            best = move

    new_board, points, new_rack = simulator.simulate_move(board, best, rack)
    return {
        'move': best,
        'value': 0.0,
        'equity': float(points),
        'new_board': new_board,
        'points': points,
        'new_rack': new_rack,
    }


def evaluate_moves_grouped(eval_jobs, infer_batch_size=256, value_weight=25.0):
    """Evaluate move candidates for many game states, grouped by engine.

    eval_jobs: list of {
      'engine': inference engine,
      'move_states': list[(move, new_board, points, new_rack, new_score_diff)],
      'bag_remaining': int
    }
    Returns: list of move_evals per job (same order as eval_jobs).
    """
    if not eval_jobs:
        return []

    results = [None] * len(eval_jobs)
    by_engine = defaultdict(list)
    for idx, job in enumerate(eval_jobs):
        by_engine[id(job['engine'])].append(idx)

    for _, idxs in by_engine.items():
        first = eval_jobs[idxs[0]]
        engine = first['engine']
        w = float(value_weight if value_weight is not None else getattr(engine, 'value_weight', 25.0))

        flat_items = []
        for idx in idxs:
            job = eval_jobs[idx]
            move_states = job['move_states']
            if not move_states:
                results[idx] = []
                continue

            start = len(flat_items)
            for ms in move_states:
                flat_items.append((
                    ms,
                    job['bag_remaining'],
                ))
            end = len(flat_items)
            results[idx] = {
                'range': (start, end),
                'move_states': move_states,
            }

        if not flat_items:
            continue

        vals = []
        with torch.no_grad():
            for i in range(0, len(flat_items), infer_batch_size):
                chunk = flat_items[i:i + infer_batch_size]
                b_tensors = torch.stack([
                    inference.board_to_tensor(item[0][1]) for item in chunk
                ]).to(engine.device)
                s_vec_size = getattr(engine, 'state_vector_size', 36)
                s_tensors = torch.stack([
                    inference.state_to_tensor(item[0][3], item[0][4], item[1], state_vector_size=s_vec_size) for item in chunk
                ]).to(engine.device)
                chunk_vals = engine.model(b_tensors, s_tensors).view(-1)
                vals.extend(chunk_vals.detach().cpu().tolist())

        for idx in idxs:
            entry = results[idx]
            if isinstance(entry, list):
                continue
            start, end = entry['range']
            move_states = entry['move_states']
            job_vals = vals[start:end]

            evals = []
            for i, (move, new_board, points, new_rack, _) in enumerate(move_states):
                val = job_vals[i]
                equity = float(points) + w * val
                evals.append({
                    'move': move,
                    'value': val,
                    'equity': equity,
                    'new_board': new_board,
                    'points': points,
                    'new_rack': new_rack,
                })
            evals.sort(key=lambda x: x['equity'], reverse=True)
            results[idx] = evals

    return results


def compute_turn_temperature(turn_idx, max_turns, temp_start, temp_end):
    """Linearly anneal sampling temperature across turns."""
    if temp_end is None:
        return temp_start
    if max_turns <= 1:
        return temp_end
    alpha = min(1.0, max(0.0, turn_idx / float(max_turns - 1)))
    return (1.0 - alpha) * temp_start + alpha * temp_end


def normalize_margin(margin, margin_scale):
    # Keep margin-derived targets in [-1, 1] to match tanh output range.
    return math.tanh(margin / margin_scale)


def compute_player_target(
    player,
    scores,
    reward_mode='blend',
    margin_scale=150.0,
    margin_mix=0.35,
):
    my_score = scores[player]
    opp_score = scores[1 - player]

    if my_score > opp_score:
        outcome = 1.0
    elif my_score < opp_score:
        outcome = -1.0
    else:
        outcome = 0.0

    margin = float(my_score - opp_score)
    margin_norm = normalize_margin(margin, margin_scale)

    if reward_mode == 'outcome':
        return outcome
    if reward_mode == 'margin':
        return margin_norm

    # Blend mode: preserve win/loss anchor while rewarding larger margins.
    mix = max(0.0, min(1.0, margin_mix))
    return (1.0 - mix) * outcome + mix * margin_norm


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
    elif not p0_empty and not p1_empty:
        # Both players subtract the value of their remaining unplayed tiles
        scores[0] -= rack_penalty(racks[0])
        scores[1] -= rack_penalty(racks[1])


def play_one_game(
    engine_p0,
    engine_p1,
    temp_start=0.20,
    temp_end=None,
    top_k=5,
    max_turns=200,
    infer_batch_size=256,
    reward_mode='blend',
    margin_scale=150.0,
    margin_mix=0.35,
    p0_is_greedy=False,
    p1_is_greedy=False,
    keep_p0_only=False,
):
    board = simulator.create_empty_board()
    bag = build_bag()

    racks = [draw_tiles(bag, 7), draw_tiles(bag, 7)]
    scores = [0, 0]

    player_states = {0: [], 1: []}
    consecutive_passes = 0

    for turn in range(max_turns):
        p = turn % 2
        o = 1 - p
        engine = engine_p0 if p == 0 else engine_p1

        score_diff = scores[p] - scores[o]
        bag_remaining = len(bag)
        temperature = compute_turn_temperature(
            turn,
            max_turns=max_turns,
            temp_start=temp_start,
            temp_end=temp_end,
        )
        if p0_is_greedy and p == 0:
            selected = choose_greedy_move(board, racks[p], engine.move_gen)
        elif p1_is_greedy and p == 1:
            selected = choose_greedy_move(board, racks[p], engine.move_gen)
        else:
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
            post_board = compact_board(board)
            post_rack = ''.join(racks[p])
            post_score_diff = scores[p] - scores[o]
        else:
            board = selected['new_board']
            scores[p] += selected['points']
            racks[p] = selected['new_rack']
            post_board = compact_board(board)
            post_rack = ''.join(racks[p])
            post_score_diff = scores[p] - scores[o]
            racks[p].extend(draw_tiles(bag, 7 - len(racks[p])))
            consecutive_passes = 0

        # Save after-state from the current player's perspective.
        player_states[p].append({
            'board': post_board,
            'rack': post_rack,
            'score_diff': post_score_diff,
            'bag': bag_remaining,
            'player': p,
        })

        if consecutive_passes >= 2:
            break

        if len(bag) == 0 and (len(racks[0]) == 0 or len(racks[1]) == 0):
            break

    apply_endgame_adjustments(scores, racks)

    result = {
        0: compute_player_target(
            0,
            scores,
            reward_mode=reward_mode,
            margin_scale=margin_scale,
            margin_mix=margin_mix,
        ),
        1: compute_player_target(
            1,
            scores,
            reward_mode=reward_mode,
            margin_scale=margin_scale,
            margin_mix=margin_mix,
        ),
    }

    samples = []
    players = (0,) if keep_p0_only else (0, 1)
    for p in players:
        for s in player_states[p]:
            samples.append({
                'board': s['board'],
                'rack': s['rack'],
                'score_diff': s['score_diff'],
                'bag': s['bag'],
                'target': result[p],
            })

    return samples, scores


def _load_engine_for_worker(path):
    if path not in _WORKER_ENGINE_CACHE:
        _WORKER_ENGINE_CACHE[path] = inference.AlphableInference(
            model_path=path,
            device=_WORKER_CFG['device'],
            dict_path=_WORKER_CFG['dict_path'],
        )
    return _WORKER_ENGINE_CACHE[path]


def init_worker(cfg):
    global _WORKER_CFG, _WORKER_ENGINE_CACHE
    _WORKER_CFG = cfg
    _WORKER_ENGINE_CACHE = {}


def run_one_game_worker(game_idx):
    # Deterministic but distinct randomness per game.
    game_seed = _WORKER_CFG['seed'] + (game_idx * 10007)
    random.seed(game_seed)
    torch.manual_seed(game_seed)

    main_engine = _load_engine_for_worker(_WORKER_CFG['model_path'])
    opponent_paths = _WORKER_CFG['opponent_paths']

    if opponent_paths:
        opp_path = random.choice(opponent_paths)
        opp_engine = _load_engine_for_worker(opp_path)
        if game_idx % 2 == 0:
            engine_p0, engine_p1 = main_engine, opp_engine
        else:
            engine_p0, engine_p1 = opp_engine, main_engine
    else:
        engine_p0, engine_p1 = main_engine, main_engine

    return play_one_game(
        engine_p0=engine_p0,
        engine_p1=engine_p1,
        temp_start=_WORKER_CFG['temp_start'],
        temp_end=_WORKER_CFG['temp_end'],
        top_k=_WORKER_CFG['top_k'],
        max_turns=_WORKER_CFG['max_turns'],
        infer_batch_size=_WORKER_CFG['infer_batch_size'],
        reward_mode=_WORKER_CFG['reward_mode'],
        margin_scale=_WORKER_CFG['margin_scale'],
        margin_mix=_WORKER_CFG['margin_mix'],
        p0_is_greedy=_WORKER_CFG['p0_is_greedy'],
        p1_is_greedy=_WORKER_CFG['p1_is_greedy'],
        keep_p0_only=_WORKER_CFG['keep_p0_only'],
    )


def init_single_game_state(game_id):
    rng = random.Random(game_id * 10007 + 17)
    bag = build_bag(rng=rng)
    rack0 = draw_tiles(bag, 7)
    rack1 = draw_tiles(bag, 7)
    return {
        'game_id': game_id,
        'rng': rng,
        'board': simulator.create_empty_board(),
        'bag': bag,
        'racks': [rack0, rack1],
        'scores': [0, 0],
        'player_states': {0: [], 1: []},
        'consecutive_passes': 0,
        'turn': 0,
        'engine_p0': None,
        'engine_p1': None,
    }


def finalize_game_state(
    state,
    reward_mode,
    margin_scale,
    margin_mix,
    keep_p0_only=False,
):
    apply_endgame_adjustments(state['scores'], state['racks'])
    scores = state['scores']

    result = {
        0: compute_player_target(
            0,
            scores,
            reward_mode=reward_mode,
            margin_scale=margin_scale,
            margin_mix=margin_mix,
        ),
        1: compute_player_target(
            1,
            scores,
            reward_mode=reward_mode,
            margin_scale=margin_scale,
            margin_mix=margin_mix,
        ),
    }

    players = (0,) if keep_p0_only else (0, 1)
    samples = []
    for p in players:
        for s in state['player_states'][p]:
            samples.append({
                'board': s['board'],
                'rack': s['rack'],
                'score_diff': s['score_diff'],
                'bag': s['bag'],
                'target': result[p],
            })
    return samples, scores


def run_interleaved_games(
    out,
    total_games,
    concurrent_games,
    main_engine,
    opponent_paths,
    get_engine,
    temp_start,
    temp_end,
    top_k,
    max_turns,
    infer_batch_size,
    reward_mode,
    margin_scale,
    margin_mix,
    flush_every_games,
    p0_is_greedy,
    p1_is_greedy,
    keep_p0_only,
):
    total_samples = 0
    p0_wins = 0
    p1_wins = 0
    draws = 0
    total_margin = 0.0

    next_game_id = 0
    active = []

    def assign_engines(state):
        if opponent_paths:
            opp_path = state['rng'].choice(opponent_paths)
            opp_engine = get_engine(opp_path)
            if state['game_id'] % 2 == 0:
                state['engine_p0'], state['engine_p1'] = main_engine, opp_engine
            else:
                state['engine_p0'], state['engine_p1'] = opp_engine, main_engine
        else:
            state['engine_p0'], state['engine_p1'] = main_engine, main_engine

    while len(active) < min(concurrent_games, total_games):
        st = init_single_game_state(next_game_id)
        assign_engines(st)
        active.append(st)
        next_game_id += 1

    pbar = tqdm(total=total_games, desc='Self-play games (interleaved)')

    while active:
        eval_jobs = []
        for st in active:
            p = st['turn'] % 2
            o = 1 - p
            engine = st['engine_p0'] if p == 0 else st['engine_p1']
            score_diff = st['scores'][p] - st['scores'][o]
            bag_remaining = len(st['bag'])

            if p0_is_greedy and p == 0:
                eval_jobs.append({
                    'selected': choose_greedy_move(
                        st['board'], st['racks'][p], engine.move_gen),
                    'is_greedy': True,
                })
            elif p1_is_greedy and p == 1:
                eval_jobs.append({
                    'selected': choose_greedy_move(
                        st['board'], st['racks'][p], engine.move_gen),
                    'is_greedy': True,
                })
            else:
                moves = engine.move_gen.generate(st['board'], st['racks'][p])
                move_states = []
                for move in moves:
                    new_board, points, new_rack = simulator.simulate_move(
                        st['board'], move, st['racks'][p])
                    new_score_diff = score_diff + points
                    move_states.append(
                        (move, new_board, points, new_rack, new_score_diff))

                eval_jobs.append({
                    'engine': engine,
                    'move_states': move_states,
                    'bag_remaining': bag_remaining,
                    'is_greedy': False,
                })

        nn_jobs = []
        nn_map = []
        for idx, job in enumerate(eval_jobs):
            if not job.get('is_greedy', False):
                nn_jobs.append(job)
                nn_map.append(idx)

        nn_evals = evaluate_moves_grouped(
            nn_jobs, infer_batch_size=infer_batch_size)
        all_selected = [None] * len(eval_jobs)
        for idx, job in enumerate(eval_jobs):
            if job.get('is_greedy', False):
                all_selected[idx] = job['selected']
        for j, idx in enumerate(nn_map):
            p = active[idx]['turn'] % 2
            temperature = compute_turn_temperature(
                active[idx]['turn'],
                max_turns=max_turns,
                temp_start=temp_start,
                temp_end=temp_end,
            )
            all_selected[idx] = choose_move_with_temperature(
                nn_evals[j], temperature=temperature, top_k=top_k)

        done_indices = []
        for idx, st in enumerate(active):
            p = st['turn'] % 2
            selected = all_selected[idx]

            o = 1 - p
            bag_remaining = len(st['bag'])

            if selected is None:
                st['consecutive_passes'] += 1
                post_board = compact_board(st['board'])
                post_rack = ''.join(st['racks'][p])
                post_score_diff = st['scores'][p] - st['scores'][o]
            else:
                st['board'] = selected['new_board']
                st['scores'][p] += selected['points']
                st['racks'][p] = selected['new_rack']
                post_board = compact_board(st['board'])
                post_rack = ''.join(st['racks'][p])
                post_score_diff = st['scores'][p] - st['scores'][o]
                st['racks'][p].extend(draw_tiles(
                    st['bag'], 7 - len(st['racks'][p])))
                st['consecutive_passes'] = 0

            # Save after-state from the current player's perspective.
            st['player_states'][p].append({
                'board': post_board,
                'rack': post_rack,
                'score_diff': post_score_diff,
                'bag': bag_remaining,
                'player': p,
            })

            st['turn'] += 1

            should_end = False
            if st['consecutive_passes'] >= 2:
                should_end = True
            elif len(st['bag']) == 0 and (len(st['racks'][0]) == 0 or len(st['racks'][1]) == 0):
                should_end = True
            elif st['turn'] >= max_turns:
                should_end = True

            if should_end:
                samples, scores = finalize_game_state(
                    st,
                    reward_mode=reward_mode,
                    margin_scale=margin_scale,
                    margin_mix=margin_mix,
                    keep_p0_only=keep_p0_only,
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
                total_margin += (scores[0] - scores[1])
                pbar.update(1)
                if flush_every_games > 0 and (pbar.n % flush_every_games == 0):
                    out.flush()
                done_indices.append(idx)

        for idx in reversed(done_indices):
            active.pop(idx)

        while len(active) < concurrent_games and next_game_id < total_games:
            st = init_single_game_state(next_game_id)
            assign_engines(st)
            active.append(st)
            next_game_id += 1

    pbar.close()
    return total_samples, p0_wins, p1_wins, draws, total_margin


def main():

    # mp.set_start_method('spawn', force=True)

    parser = argparse.ArgumentParser(
        description='Generate RL training samples via self-play.')
    parser.add_argument('--games', type=int, default=1000,
                        help='Number of self-play games to generate.')
    parser.add_argument(
        '--output', type=str, default='data/rl/rl_samples.jsonl', help='Output jsonl path.')
    parser.add_argument(
        '--model', type=str, default='models/alphable_rl_best_val_model.pth', help='Starting model checkpoint.')
    parser.add_argument(
        '--opponent-models', nargs='*', default=None,
        help='Optional list of opponent checkpoint paths. If set, one is sampled per game for diversity.')
    parser.add_argument(
        '--dict', type=str, default='resources/NWL2023.txt', help='Dictionary path.')
    parser.add_argument('--temperature', type=float, default=0.20,
                        help='Sampling temperature for move selection (backward-compatible alias for --temperature-start).')
    parser.add_argument('--temperature-start', type=float, default=None,
                        help='Sampling temperature at turn 0. If omitted, uses --temperature.')
    parser.add_argument('--temperature-end', type=float, default=0.10,
                        help='Sampling temperature at endgame turns (linear schedule). Set equal to start for constant temperature.')
    parser.add_argument('--top-k', type=int, default=5,
                        help='Sample from top-k moves each turn.')
    parser.add_argument('--max-turns', type=int, default=200,
                        help='Max turns per game before forced stop.')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducibility.')
    parser.add_argument('--append', action='store_true',
                        help='Append to output instead of overwriting.')
    parser.add_argument('--workers', type=int, default=1,
                        help='Parallel worker processes for self-play. Use >1 for CPU parallelism.')
    parser.add_argument('--chunksize', type=int, default=4,
                        help='Multiprocessing chunksize when --workers > 1.')
    parser.add_argument('--concurrent-games', type=int, default=1,
                        help='Single-process interleaving: keep this many games active concurrently (best with --device cuda).')
    parser.add_argument('--device', choices=['auto', 'cpu', 'cuda'], default='auto',
                        help='Inference device for self-play workers.')
    parser.add_argument('--infer-batch-size', type=int, default=256,
                        help='Inference batch size for move scoring to control GPU memory usage.')
    parser.add_argument('--reward-mode', choices=['outcome', 'margin', 'blend'], default='blend',
                        help='RL target type: pure outcome, pure normalized margin, or blended outcome+margin.')
    parser.add_argument('--margin-scale', type=float, default=150.0,
                        help='Scale for margin normalization tanh(margin / margin_scale).')
    parser.add_argument('--margin-mix', type=float, default=0.35,
                        help='Blend mix for reward-mode=blend: target=(1-mix)*outcome + mix*margin_norm.')
    parser.add_argument('--flush-every-games', type=int, default=1,
                        help='Flush output file every N completed games (0 disables periodic flush).')
    parser.add_argument('--vs-greedy', action='store_true',
                        help='Play P1 as greedy instead of model/self-play to build anti-greedy curriculum data.')
    parser.add_argument('--greedy-vs-greedy', action='store_true',
                        help='Play both P0 and P1 as greedy (good for generating synthetic rapid-growth baseline data).')
    parser.add_argument('--keep-p0-only', action='store_true',
                        help='Keep only P0 training states in output (recommended with --vs-greedy).')
    parser.add_argument('--top-k-vs-greedy', type=int, default=None,
                        help='Override top-k used on Alphable turns in --vs-greedy mode.')
    parser.add_argument('--temperature-start-vs-greedy', type=float, default=None,
                        help='Override temperature-start for --vs-greedy mode.')
    parser.add_argument('--temperature-end-vs-greedy', type=float, default=None,
                        help='Override temperature-end for --vs-greedy mode.')
    args = parser.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    if args.device == 'auto':
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
    else:
        device = args.device
        if device == 'cuda' and not torch.cuda.is_available():
            raise RuntimeError('CUDA requested but not available.')

    if args.workers < 1:
        raise ValueError('--workers must be >= 1')
    if args.chunksize < 1:
        raise ValueError('--chunksize must be >= 1')
    if args.concurrent_games < 1:
        raise ValueError('--concurrent-games must be >= 1')
    if args.flush_every_games < 0:
        raise ValueError('--flush-every-games must be >= 0')
    if args.top_k < 1:
        raise ValueError('--top-k must be >= 1')
    if args.top_k_vs_greedy is not None and args.top_k_vs_greedy < 1:
        raise ValueError('--top-k-vs-greedy must be >= 1')

    use_interleaved = (device == 'cuda' and args.concurrent_games > 1)

    if device == 'cuda' and args.workers > 1 and not use_interleaved:
        print('Warning: forcing --workers=1 on CUDA to avoid GPU contention/OOM.')
        args.workers = 1

    if device == 'cuda' and args.workers > 1 and use_interleaved:
        print('Warning: CUDA + process workers can contend heavily. For best speed/stability set --workers 1 with --concurrent-games > 1.')

    if use_interleaved and args.workers > 1:
        print('Info: using interleaved CUDA path; overriding --workers to 1.')
        args.workers = 1

    print(f'Using device: {device}')
    print(f'Loading model from: {args.model}')

    if args.temperature_start is None:
        args.temperature_start = args.temperature

    if args.vs_greedy or args.greedy_vs_greedy:
        if args.temperature_start_vs_greedy is not None:
            args.temperature_start = args.temperature_start_vs_greedy
        if args.temperature_end_vs_greedy is not None:
            args.temperature_end = args.temperature_end_vs_greedy
        if args.top_k_vs_greedy is not None:
            args.top_k = args.top_k_vs_greedy

    if args.vs_greedy and not args.keep_p0_only:
        print('Warning: --vs-greedy without --keep-p0-only will also train on greedy-player states.')

    if (args.vs_greedy or args.greedy_vs_greedy) and args.opponent_models:
        print('Warning: --opponent-models is ignored when greedy play is enabled.')

    if args.margin_scale <= 0:
        raise ValueError('--margin-scale must be > 0')

    if not (0.0 <= args.margin_mix <= 1.0):
        raise ValueError('--margin-mix must be in [0, 1]')

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

    opponent_paths = []
    if args.opponent_models and not (args.vs_greedy or args.greedy_vs_greedy):
        for p in args.opponent_models:
            if os.path.exists(p):
                opponent_paths.append(p)
            else:
                print(f'Warning: opponent checkpoint not found, skipping: {p}')
        if not opponent_paths:
            print(
                'Warning: no valid opponent checkpoints after filtering. Falling back to mirror self-play.')

    mode = 'a' if args.append else 'w'
    total_samples = 0
    p0_wins = 0
    p1_wins = 0
    draws = 0
    total_margin = 0.0

    worker_cfg = {
        'seed': args.seed,
        'device': device,
        'dict_path': args.dict,
        'model_path': model_path,
        'opponent_paths': opponent_paths,
        'temp_start': args.temperature_start,
        'temp_end': args.temperature_end,
        'top_k': args.top_k,
        'max_turns': args.max_turns,
        'infer_batch_size': args.infer_batch_size,
        'reward_mode': args.reward_mode,
        'margin_scale': args.margin_scale,
        'margin_mix': args.margin_mix,
        'p0_is_greedy': args.greedy_vs_greedy,
        'p1_is_greedy': args.vs_greedy or args.greedy_vs_greedy,
        'keep_p0_only': args.keep_p0_only,
    }

    def load_engine(checkpoint_path):
        return inference.AlphableInference(
            model_path=checkpoint_path,
            device=device,
            dict_path=args.dict,
        )

    engine_cache = {}

    def get_engine(path):
        if path not in engine_cache:
            engine_cache[path] = load_engine(path)
        return engine_cache[path]

    with open(args.output, mode) as out:
        if use_interleaved:
            print(
                f'Running interleaved CUDA self-play with concurrent_games={args.concurrent_games}')
            main_engine = get_engine(model_path)
            total_samples, p0_wins, p1_wins, draws, total_margin = run_interleaved_games(
                out=out,
                total_games=args.games,
                concurrent_games=args.concurrent_games,
                main_engine=main_engine,
                opponent_paths=opponent_paths,
                get_engine=get_engine,
                temp_start=args.temperature_start,
                temp_end=args.temperature_end,
                top_k=args.top_k,
                max_turns=args.max_turns,
                infer_batch_size=args.infer_batch_size,
                reward_mode=args.reward_mode,
                margin_scale=args.margin_scale,
                margin_mix=args.margin_mix,
                flush_every_games=args.flush_every_games,
                p0_is_greedy=args.greedy_vs_greedy,
                p1_is_greedy=args.vs_greedy or args.greedy_vs_greedy,
                keep_p0_only=args.keep_p0_only,
            )
        else:
            pool = None
            if args.workers == 1:
                init_worker(worker_cfg)
                iterator = (run_one_game_worker(i) for i in range(args.games))
                pbar = tqdm(iterator, total=args.games, desc='Self-play games')
            else:
                print(
                    f'Running parallel self-play with {args.workers} workers (chunksize={args.chunksize})')
                pool = Pool(
                    processes=args.workers,
                    initializer=init_worker,
                    initargs=(worker_cfg,),
                )
                pbar = tqdm(
                    pool.imap_unordered(run_one_game_worker, range(
                        args.games), chunksize=args.chunksize),
                    total=args.games,
                    desc='Self-play games',
                )

            try:
                for samples, scores in pbar:
                    for s in samples:
                        out.write(json.dumps(s) + '\n')

                    total_samples += len(samples)
                    if scores[0] > scores[1]:
                        p0_wins += 1
                    elif scores[1] > scores[0]:
                        p1_wins += 1
                    else:
                        draws += 1

                    total_margin += (scores[0] - scores[1])
                    completed_games = p0_wins + p1_wins + draws
                    if args.flush_every_games > 0 and (completed_games % args.flush_every_games == 0):
                        out.flush()
            finally:
                if pool is not None:
                    pool.close()
                    pool.join()

    print('Self-play generation complete.')
    print(f'Games: {args.games}')
    print(f'Samples written: {total_samples}')
    print(f'P0 wins / P1 wins / draws: {p0_wins} / {p1_wins} / {draws}')
    print(f'Avg P0-P1 margin: {total_margin / max(1, args.games):.2f}')
    print(
        f'Reward mode: {args.reward_mode} | margin_scale={args.margin_scale} | margin_mix={args.margin_mix}')
    print(
        f'Temperature schedule: start={args.temperature_start} -> end={args.temperature_end}')
    print(f'Output: {args.output}')


if __name__ == '__main__':
    main()
