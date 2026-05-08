#!/usr/bin/env python3
"""
Enhanced game metadata fetching with pagination support.
"""
import os
import requests
import json
import time
from typing import List, Dict

API_KEY = os.environ.get("WOOGLES_API_KEY", "YOUR_API_KEY_HERE")


def fetch_games_batch(username: str, num_games: int = 500, offset: int = 0) -> tuple:
    """Fetch a single batch of game metadata."""
    api_url = 'https://woogles.io/api/game_service.GameMetadataService/GetRecentGames'

    headers = {
        "X-Api-Key": API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "username": username,
        "num_games": num_games,
        "offset": offset
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            games = data.get('game_info', [])
            return games, None
        else:
            return None, f"Status {response.status_code}: {response.text[:200]}"
    except Exception as e:
        return None, str(e)


def fetch_all_games(username: str, max_games: int = None, batch_size: int = 500,
                    delay: float = 0.2) -> List[Dict]:
    """
    Fetch all available games for a user using pagination.

    Args:
        username: Woogles username
        max_games: Maximum total games to fetch (None = all available)
        batch_size: Games per request (max 500)
        delay: Delay between requests in seconds
    """
    all_games = []
    offset = 0
    batch_num = 1

    while True:
        # Determine how many games to fetch in this batch
        if max_games:
            remaining = max_games - len(all_games)
            if remaining <= 0:
                break
            current_batch_size = min(batch_size, remaining)
        else:
            current_batch_size = batch_size

        print(
            f"Fetching batch {batch_num} (offset={offset}, count={current_batch_size})...")

        games, error = fetch_games_batch(
            username, num_games=current_batch_size, offset=offset)

        if error:
            print(f"Error: {error}")
            break

        if not games:
            print("No more games available.")
            break

        all_games.extend(games)
        print(f"  Retrieved {len(games)} games (total: {len(all_games)})")

        # If we got fewer games than requested, we've reached the end
        if len(games) < current_batch_size:
            print("Reached end of available games.")
            break

        offset += len(games)
        batch_num += 1

        if delay > 0:
            time.sleep(delay)

    return all_games


def save_games(games: List[Dict], output_file: str):
    """Save games to JSON file."""
    data = {'game_info': games}
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\nSaved {len(games)} games to {output_file}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Fetch game metadata from Woogles.io')
    parser.add_argument('username', help='Woogles username to fetch games for')
    parser.add_argument('-n', '--num-games', type=int, default=None,
                        help='Maximum number of games to fetch (default: all)')
    parser.add_argument('-b', '--batch-size', type=int, default=500,
                        help='Games per request (max 500, default: 500)')
    parser.add_argument('-d', '--delay', type=float, default=0.2,
                        help='Delay between requests in seconds (default: 0.2)')
    parser.add_argument('-o', '--output', default='woogles_games.json',
                        help='Output file (default: woogles_games.json)')

    args = parser.parse_args()

    print(f"Fetching games for user: {args.username}")
    print(f"Max games: {args.num_games or 'all'}")
    print("=" * 60)

    games = fetch_all_games(
        args.username,
        max_games=args.num_games,
        batch_size=args.batch_size,
        delay=args.delay
    )

    if games:
        save_games(games, args.output)
    else:
        print("No games fetched.")
