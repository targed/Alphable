#!/usr/bin/env python3
"""
Woogles Data Collection Tool
A unified CLI for fetching, filtering, and processing game data from Woogles.io
"""
import argparse
import json
import sys

# Import our modules
import fetch_more_games
import fetch_gcg_data
import filter_games
import process_games


def cmd_fetch_metadata(args):
    """Fetch game metadata."""
    print(f"Fetching metadata for user: {args.username}")
    print("=" * 60)

    games = fetch_more_games.fetch_all_games(
        args.username,
        max_games=args.num_games,
        batch_size=args.batch_size,
        delay=args.delay
    )

    if games:
        fetch_more_games.save_games(games, args.output)
        return games
    else:
        print("No games fetched.")
        return []


def cmd_fetch_gcg(args):
    """Fetch GCG (move data) for games."""
    print(f"Fetching GCG data from: {args.metadata}")
    results = fetch_gcg_data.fetch_from_metadata_file(
        metadata_file=args.metadata,
        output_dir=args.output_dir,
        delay=args.delay
    )
    return results


def cmd_filter(args):
    """Filter games based on criteria."""
    # Load metadata
    with open(args.input, 'r') as f:
        data = json.load(f)

    games = data.get('game_info', [])
    print(f"Loaded {len(games)} games from {args.input}")

    # Build filter dict
    filters = {}

    if args.min_rating:
        filters['min_rating'] = args.min_rating
    if args.max_rating:
        filters['max_rating'] = args.max_rating
    if args.lexicon:
        filters['lexicons'] = args.lexicon
    if args.bot_only:
        filters['bot_game'] = True
    if args.human_only:
        filters['bot_game'] = False
    if args.tournament_only:
        filters['tournament'] = True
    if args.casual_only:
        filters['tournament'] = False
    if args.variant:
        filters['variants'] = args.variant
    if args.time_control:
        filters['time_controls'] = args.time_control
    if args.min_margin is not None:
        filters['min_margin'] = args.min_margin
    if args.max_margin is not None:
        filters['max_margin'] = args.max_margin

    # Apply filters
    if filters:
        print(f"\nApplying filters: {filters}")
        filtered = filter_games.apply_filters(games, filters)
    else:
        filtered = games

    print(f"\nFiltered to {len(filtered)} games")
    filter_games.print_game_summary(filtered)

    # Save filtered results
    if args.output:
        output_data = {'game_info': filtered}
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"\nSaved filtered games to {args.output}")

    return filtered


def cmd_process(args):
    """Process GCG files into structured formats."""
    print(f"Processing GCG files from: {args.gcg_dir}")

    games = process_games.process_gcg_directory(
        gcg_dir=args.gcg_dir,
        output_csv=args.csv,
        output_json=args.json,
        metadata_file=args.metadata
    )

    if games and not args.no_training:
        process_games.create_training_dataset(games, output_file=args.training)

    return games


def cmd_full_pipeline(args):
    """Run the complete pipeline: fetch metadata -> filter -> fetch GCG -> process."""
    print("RUNNING FULL PIPELINE")
    print("=" * 60)

    # Step 1: Fetch metadata
    print("\n[1/4] Fetching metadata...")
    metadata_file = args.output or 'woogles_pipeline.json'
    games = fetch_more_games.fetch_all_games(
        args.username,
        max_games=args.num_games,
        batch_size=500,
        delay=0.2
    )

    if not games:
        print("Failed to fetch games. Exiting.")
        return

    fetch_more_games.save_games(games, metadata_file)

    # Step 2: Filter (if filters specified)
    filters = {}
    if args.min_rating:
        filters['min_rating'] = args.min_rating
    if args.lexicon:
        filters['lexicons'] = args.lexicon
    if args.bot_only:
        filters['bot_game'] = True

    if filters:
        print(f"\n[2/4] Applying filters: {filters}")
        games = filter_games.apply_filters(games, filters)
        print(f"Filtered to {len(games)} games")
        # Save filtered metadata
        filtered_metadata = metadata_file.replace('.json', '_filtered.json')
        with open(filtered_metadata, 'w') as f:
            json.dump({'game_info': games}, f, indent=2)
        metadata_file = filtered_metadata
    else:
        print("\n[2/4] No filters specified, using all games")

    # Step 3: Fetch GCG data
    print(f"\n[3/4] Fetching GCG data for {len(games)} games...")
    fetch_gcg_data.fetch_from_metadata_file(
        metadata_file=metadata_file,
        output_dir=args.gcg_dir,
        delay=args.delay
    )

    # Step 4: Process data
    print("\n[4/4] Processing GCG data...")
    processed = process_games.process_gcg_directory(
        gcg_dir=args.gcg_dir,
        output_csv=args.csv or 'data/games_processed.csv',
        output_json=args.json or 'data/games_processed.json',
        metadata_file=metadata_file
    )

    if processed:
        training_file = args.training or 'data/training_dataset.jsonl'
        process_games.create_training_dataset(
            processed, output_file=training_file)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Woogles Data Collection Tool - Fetch and process game data from Woogles.io',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Fetch metadata command
    fetch_meta = subparsers.add_parser(
        'fetch-metadata', help='Fetch game metadata')
    fetch_meta.add_argument('username', help='Woogles username')
    fetch_meta.add_argument('-n', '--num-games',
                            type=int, help='Max games to fetch')
    fetch_meta.add_argument('-b', '--batch-size', type=int, default=500)
    fetch_meta.add_argument('-d', '--delay', type=float, default=0.2)
    fetch_meta.add_argument('-o', '--output', default='woogles_games.json')

    # Fetch GCG command
    fetch_gcg = subparsers.add_parser('fetch-gcg', help='Fetch GCG move data')
    fetch_gcg.add_argument('-m', '--metadata', default='woogles.json',
                           help='Metadata file with game IDs')
    fetch_gcg.add_argument('-o', '--output-dir', default='data/gcg')
    fetch_gcg.add_argument('-d', '--delay', type=float, default=0.1)

    # Filter command
    filter_cmd = subparsers.add_parser('filter', help='Filter games')
    filter_cmd.add_argument('input', help='Input metadata JSON file')
    filter_cmd.add_argument('-o', '--output', help='Output filtered JSON file')
    filter_cmd.add_argument('--min-rating', type=int)
    filter_cmd.add_argument('--max-rating', type=int)
    filter_cmd.add_argument('--lexicon', nargs='+',
                            help='Lexicons (e.g., CSW24 NWL23)')
    filter_cmd.add_argument('--bot-only', action='store_true')
    filter_cmd.add_argument('--human-only', action='store_true')
    filter_cmd.add_argument('--tournament-only', action='store_true')
    filter_cmd.add_argument('--casual-only', action='store_true')
    filter_cmd.add_argument('--variant', nargs='+',
                            help='Variants (e.g., classic wordsmog)')
    filter_cmd.add_argument('--time-control', nargs='+')
    filter_cmd.add_argument('--min-margin', type=int)
    filter_cmd.add_argument('--max-margin', type=int)

    # Process command
    process = subparsers.add_parser('process', help='Process GCG files')
    process.add_argument('-g', '--gcg-dir', default='data/gcg')
    process.add_argument('-m', '--metadata', default='woogles.json')
    process.add_argument('--csv', default='data/games_processed.csv')
    process.add_argument('--json', default='data/games_processed.json')
    process.add_argument('--training', default='data/training_dataset.jsonl')
    process.add_argument('--no-training', action='store_true')

    # Full pipeline command
    pipeline = subparsers.add_parser('pipeline', help='Run full pipeline')
    pipeline.add_argument('username', help='Woogles username')
    pipeline.add_argument('-n', '--num-games', type=int,
                          help='Max games to fetch')
    pipeline.add_argument('-o', '--output', help='Metadata output file')
    pipeline.add_argument('--min-rating', type=int,
                          help='Filter: minimum rating')
    pipeline.add_argument('--lexicon', nargs='+', help='Filter: lexicons')
    pipeline.add_argument('--bot-only', action='store_true',
                          help='Filter: bot games only')
    pipeline.add_argument('--gcg-dir', default='data/gcg')
    pipeline.add_argument('-d', '--delay', type=float, default=0.1)
    pipeline.add_argument('--csv', help='Output CSV file')
    pipeline.add_argument('--json', help='Output JSON file')
    pipeline.add_argument('--training', help='Output training dataset file')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == 'fetch-metadata':
        cmd_fetch_metadata(args)
    elif args.command == 'fetch-gcg':
        cmd_fetch_gcg(args)
    elif args.command == 'filter':
        cmd_filter(args)
    elif args.command == 'process':
        cmd_process(args)
    elif args.command == 'pipeline':
        cmd_full_pipeline(args)


if __name__ == '__main__':
    main()
