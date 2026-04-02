import json
import os
import random
from collections import Counter
from tqdm import tqdm

import structure
import simulator


def parse_position(pos):
    """
    Parses a position string like '8E' (Row 8, Col E, Across)
    or 'F6' (Col F, Row 6, Down) into (row, col, dir).
    """
    if not pos:
        return None, None, None

    pos = pos.upper()
    if pos[0].isalpha():
        # Down (e.g. F6)
        col = ord(pos[0]) - ord('A')
        row = int(pos[1:]) - 1
        direction = 'Down'
    else:
        # Across (e.g. 8E)
        import re
        match = re.match(r"(\d+)([A-Z])", pos)
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


def process_game(game_line, move_gen):
    game = json.loads(game_line)
    moves = game['moves']

    board = simulator.create_empty_board()
    samples = []

    player_scores = {0: 0, 1: 0}  # 0 for first player, 1 for second
    bag_size = 100

    for i, move_data in enumerate(moves):
        player_idx = i % 2
        rack = list(move_data['rack'])
        pos = move_data.get('position', '')
        word = move_data.get('word', '')
        score = move_data.get('score', 0)

        # Keep track of bag size
        bag_size -= len(rack)  # Very rough approximation for now.
        if bag_size < 0:
            bag_size = 0

        row, col, direction = parse_position(pos)

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
            # We skip turns where the human move isn't considered "legal" by our engine
            played_move_generated = None
            for lm in legal_moves:
                # We need to match coordinates and the word
                if is_same_move(lm, played_move):
                    played_move_generated = lm
                    break

            if played_move_generated:
                # 2. Simulate Positive Sample (The human move)
                pos_board, pos_score, pos_rack = simulator.simulate_move(
                    board, played_move_generated, rack)

                # Format board state to compact string (15 rows of 15 chars)
                pos_board_compact = "".join(["".join(r) for r in pos_board])

                samples.append({
                    'board': pos_board_compact,
                    'rack': "".join(pos_rack),
                    'score_diff': score_diff + pos_score,
                    'bag': bag_size,
                    'target': 1.0  # Positive
                })

                # 3. Simulate and score all OTHER legal moves
                scored_negatives = []
                for lm in legal_moves:
                    if not is_same_move(lm, played_move_generated):
                        # Calculate the score. We do NOT need the full board or rack array for the sorting step
                        # to speed things up, but `simulate_move` returns them all anyway.
                        neg_board, neg_score, neg_rack = simulator.simulate_move(
                            board, lm, rack)
                        scored_negatives.append(
                            (neg_score, neg_board, neg_rack))

                # 4. Hard Negative Mining
                # Sort by score descending and take the top N (currently 4)
                scored_negatives.sort(key=lambda x: x[0], reverse=True)
                hard_negatives = scored_negatives[:4]

                for neg_score, neg_board, neg_rack in hard_negatives:
                    neg_board_compact = "".join(
                        ["".join(r) for r in neg_board])
                    samples.append({
                        'board': neg_board_compact,
                        'rack': "".join(neg_rack),
                        'score_diff': score_diff + neg_score,
                        'bag': bag_size,
                        'target': -1.0  # Negative
                    })

                # Finally, apply the actual human move to the board to progress the game state
                # Note: We use our simulate_move to ensure the board state updates correctly
                board, _, _ = simulator.simulate_move(
                    board, played_move_generated, rack)
            else:
                # Fallback: manually place the word (ignoring blanks for now if not found in dict)
                for idx, char in enumerate(played_move['word']):
                    if char == '.':
                        continue
                    r = row + (idx if direction == 'Down' else 0)
                    c = col + (idx if direction == 'Across' else 0)
                    if 0 <= r < 15 and 0 <= c < 15:
                        board[r][c] = char

        # Update scores
        player_scores[player_idx] += score

    return samples


def main():
    print("Loading GADDAG Dictionary...")
    # Prefer NWL2023 (WORD + definition format), then fallback.
    dict_candidates = [
        'resources/NWL2023.txt',
        'resources/CSW24.txt',
        'resources/CSW21.txt',
        'resources/NWL23.txt',
    ]
    dict_path = next((p for p in dict_candidates if os.path.exists(p)), None)
    if dict_path is None:
        raise FileNotFoundError(
            "No dictionary file found. Checked: " + ", ".join(dict_candidates)
        )

    gaddag = structure.Gaddag.load(dict_path)
    move_gen = structure.MoveGenerator(gaddag)

    input_candidates = [
        'data/training_dataset.jsonl',
        'data/whoogles/data/training_dataset.jsonl',
        'data/woogles/data/training_dataset.jsonl',
    ]
    input_file = next((p for p in input_candidates if os.path.exists(p)), None)
    if input_file is None:
        raise FileNotFoundError(
            "No training dataset found. Checked: " +
            ", ".join(input_candidates)
        )
    output_dir = 'data/supervised'
    os.makedirs(output_dir, exist_ok=True)

    out_file = os.path.join(output_dir, 'samples.jsonl')

    print(f"Processing games from {input_file}...")

    total_games = sum(1 for _ in open(input_file))

    with open(input_file, 'r') as f_in, open(out_file, 'w') as f_out:
        for line in tqdm(f_in, total=total_games):
            samples = process_game(line, move_gen)
            for sample in samples:
                f_out.write(json.dumps(sample) + "\n")

    print(f"Data generation complete. Saved to {out_file}")


if __name__ == "__main__":
    main()
