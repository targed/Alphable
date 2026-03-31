#!/usr/bin/env python3
"""
Process GCG game data into structured formats for ML training or analysis.
"""
import json
import csv
import os
from pathlib import Path
from typing import List, Dict, Any, Optional


def parse_gcg_file(gcg_path: str) -> Dict[str, Any]:
    """
    Parse a GCG file and extract structured information.

    Returns a dictionary with:
    - players: List of player names
    - moves: List of moves with details
    - final_scores: Final scores
    - game_id: Game identifier
    """
    with open(gcg_path, 'r') as f:
        lines = f.readlines()

    game_data = {
        'game_id': Path(gcg_path).stem,
        'players': [],
        'moves': [],
        'final_scores': [],
        'encoding': None,
        'lexicon': None
    }

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Parse metadata
        if line.startswith('#'):
            parts = line.split()
            if len(parts) >= 3:
                tag = parts[0]
                if tag == '#player1':
                    game_data['players'].append(' '.join(parts[1:]))
                elif tag == '#player2':
                    game_data['players'].append(' '.join(parts[1:]))
                elif tag == '#character-encoding':
                    game_data['encoding'] = parts[1]
                elif tag == '#lexicon':
                    game_data['lexicon'] = parts[1]

        # Parse moves
        elif line.startswith('>'):
            # Move format: >PlayerName: RACK POSITION WORD SCORE CUMULATIVE
            parts = line[1:].split(': ', 1)
            if len(parts) == 2:
                player_name = parts[0]
                move_parts = parts[1].split()
                if len(move_parts) >= 5:
                    move = {
                        'player': player_name,
                        'rack': move_parts[0],
                        'position': move_parts[1],
                        'word': move_parts[2],
                        'score': int(move_parts[3]),
                        'cumulative': int(move_parts[4])
                    }
                    game_data['moves'].append(move)

    # Extract final scores from last moves
    if game_data['moves']:
        player_scores = {}
        for move in game_data['moves']:
            player_scores[move['player']] = move['cumulative']
        game_data['final_scores'] = list(player_scores.values())

    return game_data


def process_gcg_directory(gcg_dir: str = 'data/gcg',
                          output_csv: str = 'data/games_processed.csv',
                          output_json: str = 'data/games_processed.json',
                          metadata_file: str = 'woogles.json') -> List[Dict]:
    """
    Process all GCG files in a directory and create structured datasets.
    """
    gcg_files = list(Path(gcg_dir).glob('*.gcg'))
    print(f"Found {len(gcg_files)} GCG files in {gcg_dir}")

    # Load metadata for enrichment
    metadata_lookup = {}
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        for game in metadata.get('game_info', []):
            metadata_lookup[game['game_id']] = game
        print(f"Loaded metadata for {len(metadata_lookup)} games")

    processed_games = []

    for i, gcg_file in enumerate(gcg_files, 1):
        if i % 100 == 0:
            print(f"Processing: {i}/{len(gcg_files)}")

        try:
            game_data = parse_gcg_file(str(gcg_file))

            # Enrich with metadata
            game_id = game_data['game_id']
            if game_id in metadata_lookup:
                meta = metadata_lookup[game_id]
                game_data['metadata'] = {
                    'players_info': meta.get('players', []),
                    'time_control': meta.get('time_control_name'),
                    'created_at': meta.get('created_at'),
                    'winner': meta.get('winner'),
                    'game_end_reason': meta.get('game_end_reason'),
                    'tournament_id': meta.get('tournament_id', ''),
                    'rating_mode': meta.get('game_request', {}).get('rating_mode'),
                }

            processed_games.append(game_data)

        except Exception as e:
            print(f"Error processing {gcg_file}: {e}")

    print(f"\nSuccessfully processed {len(processed_games)} games")

    # Save to JSON
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, 'w') as f:
        json.dump(processed_games, f, indent=2)
    print(f"Saved detailed JSON to {output_json}")

    # Save to CSV (summary format)
    if processed_games:
        Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
        with open(output_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'game_id', 'lexicon', 'player1', 'player2',
                'num_moves', 'final_score_p1', 'final_score_p2',
                'winner', 'rating_mode', 'time_control'
            ])

            for game in processed_games:
                metadata = game.get('metadata', {})
                writer.writerow([
                    game['game_id'],
                    game.get('lexicon', ''),
                    game['players'][0] if len(game['players']) > 0 else '',
                    game['players'][1] if len(game['players']) > 1 else '',
                    len(game['moves']),
                    game['final_scores'][0] if len(
                        game['final_scores']) > 0 else 0,
                    game['final_scores'][1] if len(
                        game['final_scores']) > 1 else 0,
                    metadata.get('winner', ''),
                    metadata.get('rating_mode', ''),
                    metadata.get('time_control', '')
                ])
        print(f"Saved summary CSV to {output_csv}")

    return processed_games


def create_training_dataset(processed_games: List[Dict],
                            output_file: str = 'data/training_dataset.jsonl'):
    """
    Create a training dataset in JSONL format.
    Each line is a game with moves sequence.
    """
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        for game in processed_games:
            training_sample = {
                'game_id': game['game_id'],
                'lexicon': game.get('lexicon'),
                'players': game['players'],
                'moves': game['moves'],
                'final_scores': game['final_scores'],
                'metadata': game.get('metadata', {})
            }
            f.write(json.dumps(training_sample) + '\n')

    print(
        f"Created training dataset: {output_file} ({len(processed_games)} games)")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Process GCG files into structured formats')
    parser.add_argument('-g', '--gcg-dir', default='data/gcg',
                        help='Directory containing GCG files')
    parser.add_argument('-m', '--metadata', default='woogles.json',
                        help='Metadata JSON file')
    parser.add_argument('--csv', default='data/games_processed.csv',
                        help='Output CSV file')
    parser.add_argument('--json', default='data/games_processed.json',
                        help='Output detailed JSON file')
    parser.add_argument('--training', default='data/training_dataset.jsonl',
                        help='Output training dataset (JSONL format)')

    args = parser.parse_args()

    games = process_gcg_directory(
        gcg_dir=args.gcg_dir,
        output_csv=args.csv,
        output_json=args.json,
        metadata_file=args.metadata
    )

    if games:
        create_training_dataset(games, output_file=args.training)
