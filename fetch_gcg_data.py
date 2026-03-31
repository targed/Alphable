#!/usr/bin/env python3
"""
Fetch GCG (game move data) for games from Woogles.io API.
"""
import requests
import json
import os
import time
from pathlib import Path

API_KEY = "drXbCNvPVQTN5gfetRK6hW3zxLmDGbh8XRhcJkvdmWHT"
GCG_DIR = "data/gcg"


def fetch_gcg(game_id, delay=0.01):
    """Fetch GCG data for a single game."""
    api_url = 'https://woogles.io/api/game_service.GameMetadataService/GetGCG'

    headers = {
        "X-Api-Key": API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {"game_id": game_id}

    try:
        if delay > 0:
            time.sleep(delay)
        response = requests.post(api_url, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            return data.get('gcg', ''), None
        else:
            return None, f"Status {response.status_code}: {response.text[:200]}"
    except Exception as e:
        return None, str(e)


def fetch_gcg_batch(game_ids, output_dir=GCG_DIR, delay=0.1, resume=True):
    """Fetch GCG data for multiple games."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    results = {
        'success': [],
        'failed': [],
        'skipped': []
    }

    total = len(game_ids)
    for i, game_id in enumerate(game_ids, 1):
        output_path = Path(output_dir) / f"{game_id}.gcg"

        # Skip if already exists and resume is enabled
        if resume and output_path.exists():
            results['skipped'].append(game_id)
            if i % 50 == 0:
                print(
                    f"Progress: {i}/{total} - Skipped {game_id} (already exists)")
            continue

        gcg_data, error = fetch_gcg(game_id, delay=delay)

        if gcg_data:
            with open(output_path, 'w') as f:
                f.write(gcg_data)
            results['success'].append(game_id)
            if i % 50 == 0:
                print(f"Progress: {i}/{total} - Fetched {game_id}")
        else:
            results['failed'].append({'game_id': game_id, 'error': error})
            print(f"Failed to fetch {game_id}: {error}")

    return results


def fetch_from_metadata_file(metadata_file='woogles.json', output_dir=GCG_DIR, delay=0.1):
    """Load game IDs from metadata file and fetch GCG data."""
    with open(metadata_file, 'r') as f:
        data = json.load(f)

    games = data.get('game_info', [])
    game_ids = [game['game_id'] for game in games]

    print(f"Found {len(game_ids)} games in {metadata_file}")
    print(f"Fetching GCG data to {output_dir}/")
    print(f"Delay between requests: {delay}s")
    print("-" * 60)

    results = fetch_gcg_batch(game_ids, output_dir=output_dir, delay=delay)

    print("\n" + "=" * 60)
    print("RESULTS:")
    print(f"  Successful: {len(results['success'])}")
    print(f"  Skipped (already exist): {len(results['skipped'])}")
    print(f"  Failed: {len(results['failed'])}")

    if results['failed']:
        print("\nFailed games:")
        for fail in results['failed'][:10]:
            print(f"  - {fail['game_id']}: {fail['error']}")
        if len(results['failed']) > 10:
            print(f"  ... and {len(results['failed']) - 10} more")

    return results


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        metadata_file = sys.argv[1]
    else:
        metadata_file = 'woogles.json'

    if len(sys.argv) > 2:
        delay = float(sys.argv[2])
    else:
        delay = 0.1

    fetch_from_metadata_file(metadata_file, delay=delay)
