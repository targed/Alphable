import argparse
import heapq
import json
import os
from multiprocessing import Pool, cpu_count

from tqdm import tqdm

from alphable.core import simulator
from alphable.core import structure


DEFAULT_DICT_CANDIDATES = [
    'resources/CSW24.txt',
    'resources/NWL2023.txt',
    'resources/CSW21.txt',
    'resources/NWL23.txt',
]

DEFAULT_INPUT_CANDIDATES = [
    'data/whoogles/training_HastyBot100k_CSW24.jsonl',
    'data/training_dataset.jsonl',
    'data/whoogles/data/training_dataset.jsonl',
    'data/woogles/data/training_dataset.jsonl',
]


_WORKER_MOVE_GEN = None


def parse_position(pos):
    """
    Parses a position string like '8E' (Row 8, Col E, Across)
    or 'F6' (Col F, Row 6, Down) into (row, col, dir).
    """
    if not pos:
        return None, None, None

    pos = pos.upper()
    import re
    if pos[0].isalpha():
        # Down (e.g. F6)
        match = re.match(r"^([A-Z])(\d+)$", pos)
        if match:
            col = ord(match.group(1)) - ord('A')
            row = int(match.group(2)) - 1
            direction = 'Down'
        else:
            return None, None, None
    else:
        # Across (e.g. 8E)
        match = re.match(r"^(\d+)([A-Z])$", pos)
        if match:
            row = int(match.group(1)) - 1
            col = ord(match.group(2)) - ord('A')
            direction = 'Across'
        else:
            return None, None, None

    return row, col, direction


def is_same_move(m1, m2):
    """Checks if two generated/parsed moves are identical."""
    if not m1 or not m2:
        return False
    return m1['row'] == m2['row'] and \
        m1['col'] == m2['col'] and \
        m1['dir'] == m2['dir'] and \
        m1['word'].upper() == m2['word'].upper()


def resolve_first_existing(path_candidates):
    return next((p for p in path_candidates if os.path.exists(p)), None)


def count_lines(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return sum(1 for _ in f)


def process_game(game_line, move_gen, negatives_top_k=4):
    game = json.loads(game_line)

    # If the line represents a pre-compiled sample rather than a game replay, just return it
    if 'board' in game and 'target' in game:
        return [game]

    moves = game.get('moves')
    if moves is None:
        moves = game.get('turns')
    if not isinstance(moves, list):
        return []

    board = simulator.create_empty_board()
    samples = []

    player_scores = {0: 0, 1: 0}  # 0 for first player, 1 for second
    bag_size = 86  # Standard 100 tiles minus two 7-tile starting racks

    # Map player names or IDs to 0 and 1
    player_map = {}
    players_meta = game.get('players') or []
    if isinstance(players_meta, list) and len(players_meta) >= 2:
        for p_idx, p_name in enumerate(players_meta[:2]):
            if isinstance(p_name, str) and p_name.strip():
                player_map[p_name] = p_idx
                token = p_name.split()[0]
                player_map[token] = p_idx

    simulate_move = simulator.simulate_move

    for i, move_data in enumerate(moves):
        p_raw = move_data.get('player')
        if p_raw in (0, 1):
            player_idx = p_raw
        elif p_raw in ('0', '1'):
            player_idx = int(p_raw)
        elif p_raw in player_map:
            player_idx = player_map[p_raw]
        else:
            if p_raw is not None:
                if 0 not in player_map.values():
                    player_map[p_raw] = 0
                    player_idx = 0
                elif 1 not in player_map.values():
                    player_map[p_raw] = 1
                    player_idx = 1
                else:
                    player_idx = 0
            else:
                player_idx = i % 2

        rack_raw = move_data.get('rack')
        if rack_raw is None:
            rack_raw = move_data.get('rack_before', [])

        if isinstance(rack_raw, str):
            rack = list(rack_raw)
        elif isinstance(rack_raw, list):
            rack = rack_raw
        else:
            rack = []

        pos_raw = move_data.get('position', '')
        word = str(move_data.get('word', '') or '')
        score = move_data.get('score', 0)
        if not isinstance(score, (int, float)):
            try:
                score = int(score)
            except (TypeError, ValueError):
                score = 0

        if isinstance(pos_raw, list) and len(pos_raw) == 2:
            row, col = pos_raw
            direction = move_data.get('direction', '')
            if direction:
                direction = direction.capitalize()
        else:
            row, col, direction = parse_position(pos_raw)

        # If it's not a pass/exchange
        if row is not None and col is not None and len(word) > 0:
            played_move = {
                'row': row,
                'col': col,
                'dir': direction,
                # GCG format uses '.' for existing tiles, but GADDAG outputs full word
                'word': word.replace('.', '').upper()
            }

            score_diff = player_scores[player_idx] - \
                player_scores[1 - player_idx]

            # 1. Generate all legal moves using GADDAG
            legal_moves = move_gen.generate(board, rack)

            # Sometimes the played word is missing from GADDAG (e.g. different dictionary).
            # We skip turns where the human move isn't considered "legal" by our engine.
            played_move_generated = None
            for lm in legal_moves:
                if is_same_move(lm, played_move):
                    played_move_generated = lm
                    break

            if played_move_generated:
                # 2. Simulate Positive Sample (the human move).
                pos_board, pos_score, pos_rack = simulate_move(
                    board, played_move_generated, rack)

                # Format board state to compact string (15 rows of 15 chars).
                pos_board_compact = "".join(["".join(r) for r in pos_board])

                samples.append({
                    'board': pos_board_compact,
                    'rack': "".join(pos_rack),
                    'score_diff': score_diff + pos_score,
                    'bag': bag_size,
                    'target': 1.0  # Positive
                })

                # 3/4. Simulate and keep only top-K hard negatives by score.
                # This preserves data quality while reducing memory and sort overhead.
                hard_heap = []
                heap_counter = 0
                for lm in legal_moves:
                    if is_same_move(lm, played_move_generated):
                        continue

                    neg_board, neg_score, neg_rack = simulate_move(
                        board, lm, rack)
                    item = (neg_score, heap_counter, neg_board, neg_rack)
                    heap_counter += 1

                    if len(hard_heap) < negatives_top_k:
                        heapq.heappush(hard_heap, item)
                    elif neg_score > hard_heap[0][0]:
                        heapq.heapreplace(hard_heap, item)

                hard_negatives = sorted(
                    hard_heap, key=lambda x: x[0], reverse=True)
                for neg_score, _, neg_board, neg_rack in hard_negatives:
                    # If the alternative move scored as well as or better than the human move,
                    # do not poison the dataset by labeling it as a negative sample.
                    if neg_score >= pos_score:
                        continue

                    deficit_ratio = min(1.0, (pos_score - neg_score) / max(10, pos_score))
                    neg_target = max(-1.0, 1.0 - 2.0 * deficit_ratio)

                    neg_board_compact = "".join(
                        ["".join(r) for r in neg_board])
                    samples.append({
                        'board': neg_board_compact,
                        'rack': "".join(neg_rack),
                        'score_diff': score_diff + neg_score,
                        'bag': bag_size,
                        'target': neg_target,
                    })

                # Finally, apply the positive move to board and decrement bag
                board = pos_board
                tiles_used = max(0, len(rack) - len(pos_rack))
                bag_size = max(0, bag_size - tiles_used)
            else:
                # Fallback: manually place the word (ignoring blanks for now if not found in dict)
                tiles_placed = 0
                for idx, char in enumerate(played_move['word']):
                    if char == '.':
                        continue
                    r = row + (idx if direction == 'Down' else 0)
                    c = col + (idx if direction == 'Across' else 0)
                    if 0 <= r < 15 and 0 <= c < 15:
                        if board[r][c] == ' ':
                            tiles_placed += 1
                        board[r][c] = char
                bag_size = max(0, bag_size - tiles_placed)

        # Update scores
        player_scores[player_idx] += score

    return samples


def init_worker(dict_path):
    global _WORKER_MOVE_GEN
    gaddag = structure.Gaddag.load(dict_path)
    _WORKER_MOVE_GEN = structure.MoveGenerator(gaddag)


def process_game_line_worker(payload):
    game_line, negatives_top_k = payload
    try:
        return process_game(game_line, _WORKER_MOVE_GEN, negatives_top_k)
    except Exception as e:
        print(f"Error: {e}")
        return []


def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate supervised board/rack value samples from human game logs.'
    )
    parser.add_argument(
        '--dict',
        dest='dict_path',
        default=None,
        help='Explicit dictionary path. If omitted, first existing from --dict-candidates is used.',
    )
    parser.add_argument(
        '--dict-candidates',
        nargs='*',
        default=DEFAULT_DICT_CANDIDATES,
        help='Dictionary fallback paths in priority order.',
    )
    parser.add_argument(
        '--input',
        dest='input_file',
        default=None,
        help='Explicit input JSONL path. If omitted, first existing from --input-candidates is used.',
    )
    parser.add_argument(
        '--input-candidates',
        nargs='*',
        default=DEFAULT_INPUT_CANDIDATES,
        help='Input JSONL fallback paths in priority order.',
    )
    parser.add_argument(
        '--output',
        dest='out_file',
        default='data/supervised/samples.jsonl',
        help='Output JSONL path for generated samples.',
    )
    parser.add_argument(
        '--negatives',
        type=int,
        default=4,
        help='Number of hard negatives to keep per positive sample.',
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=max(1, cpu_count() - 1),
        help='Number of worker processes. Use 1 to disable multiprocessing.',
    )
    parser.add_argument(
        '--chunksize',
        type=int,
        default=32,
        help='Multiprocessing chunksize (larger can improve throughput).',
    )
    parser.add_argument(
        '--max-games',
        type=int,
        default=None,
        help='Optional cap on number of games to process (for smoke tests).',
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.negatives < 1:
        raise ValueError('--negatives must be >= 1')
    if args.workers < 1:
        raise ValueError('--workers must be >= 1')
    if args.chunksize < 1:
        raise ValueError('--chunksize must be >= 1')

    dict_path = args.dict_path or resolve_first_existing(args.dict_candidates)
    if dict_path is None:
        raise FileNotFoundError(
            'No dictionary file found. Checked: ' +
            ', '.join(args.dict_candidates)
        )

    input_file = args.input_file or resolve_first_existing(
        args.input_candidates)
    if input_file is None:
        raise FileNotFoundError(
            'No training dataset found. Checked: ' +
            ', '.join(args.input_candidates)
        )

    out_dir = os.path.dirname(args.out_file) or '.'
    os.makedirs(out_dir, exist_ok=True)

    total_games = count_lines(input_file)
    if args.max_games is not None:
        total_games = min(total_games, args.max_games)

    print('Using dictionary:', dict_path)
    print('Input file:', input_file)
    print('Output file:', args.out_file)
    print('Hard negatives per position:', args.negatives)
    print('Workers:', args.workers)
    print('Total games to process:', total_games)

    processed_games = 0
    emitted_samples = 0

    with open(input_file, 'r', encoding='utf-8') as f_in, open(args.out_file, 'w', encoding='utf-8') as f_out:
        if args.workers == 1:
            print('Loading GADDAG dictionary (single-process mode)...')
            gaddag = structure.Gaddag.load(dict_path)
            move_gen = structure.MoveGenerator(gaddag)

            for line in tqdm(f_in, total=total_games, desc='Preparing samples'):
                if args.max_games is not None and processed_games >= args.max_games:
                    break
                samples = process_game(
                    line, move_gen, negatives_top_k=args.negatives)
                for sample in samples:
                    f_out.write(json.dumps(sample) + '\n')
                emitted_samples += len(samples)
                processed_games += 1
        else:
            print('Loading GADDAG dictionary per worker (multi-process mode)...')

            def payload_iter():
                count = 0
                for line in f_in:
                    if args.max_games is not None and count >= args.max_games:
                        break
                    yield (line, args.negatives)
                    count += 1

            with Pool(
                processes=args.workers,
                initializer=init_worker,
                initargs=(dict_path,),
            ) as pool:
                results_iter = pool.imap(
                    process_game_line_worker,
                    payload_iter(),
                    chunksize=args.chunksize,
                )
                for samples in tqdm(results_iter, total=total_games, desc='Preparing samples'):
                    for sample in samples:
                        f_out.write(json.dumps(sample) + '\n')
                    emitted_samples += len(samples)
                    processed_games += 1

    print(f'Processed games: {processed_games}')
    print(f'Emitted samples: {emitted_samples}')
    print(f'Data generation complete. Saved to {args.out_file}')


if __name__ == "__main__":
    main()
