"""
Woogles.io Game Collection and Scraper for Alphable V4.

Fetches grandmaster-level games and tournament logs via Woogles API,
applying rating filters (>= 1800), bot/human tags, and lexicon filters.
"""

from __future__ import annotations
import os
import sys
import time
import json
import argparse
from typing import List, Dict, Optional, Any
from pathlib import Path
import requests
from tqdm import tqdm


WOOGLES_BASE_URL = "https://woogles.io/api"


class WooglesCollector:
    """Scraper and manager for Woogles.io games."""

    def __init__(
        self,
        output_dir: str = "data/raw_games",
        delay_seconds: float = 0.5,
        timeout: int = 15,
    ):
        self.output_dir = output_dir
        self.delay = delay_seconds
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Alphable-V4-Research-Bot/1.0 (+https://github.com/targed/Alphable)"
        })
        os.makedirs(self.output_dir, exist_ok=True)

    def fetch_user_game_ids(
        self,
        username: str = "BestBot",
        max_games: int = 1000,
        min_rating: int = 1800,
        lexicon: Optional[str] = "CSW24",
    ) -> List[str]:
        """
        Retrieves game IDs for a given username/bot from Woogles recent_games API.
        """
        game_ids = []
        page_size = 50
        num_pages = (max_games + page_size - 1) // page_size

        print(f"Fetching up to {max_games} game IDs for {username}...")
        for page in range(num_pages):
            url = f"{WOOGLES_BASE_URL}/recent_games"
            params = {
                "username": username,
                "limit": page_size,
                "page": page,
            }
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                if resp.status_code != 200:
                    print(f"Failed to fetch page {page}: HTTP {resp.status_code}")
                    break

                data = resp.json()
                games = data.get("games", [])
                if not games:
                    break

                for g in games:
                    # Filter by lexicon if specified
                    if lexicon and g.get("lexicon", "").upper() != lexicon.upper():
                        continue
                    # Filter by rating if available
                    ratings = [
                        g.get("player1_rating", 0) or 0,
                        g.get("player2_rating", 0) or 0,
                    ]
                    if min_rating and max(ratings) < min_rating:
                        continue

                    gid = g.get("game_id") or g.get("id")
                    if gid and gid not in game_ids:
                        game_ids.append(gid)
                        if len(game_ids) >= max_games:
                            break

                time.sleep(self.delay)
            except Exception as e:
                print(f"Error fetching page {page}: {e}")
                break

            if len(game_ids) >= max_games:
                break

        print(f"Retrieved {len(game_ids)} matching game IDs.")
        return game_ids

    def fetch_gcg(self, game_id: str) -> Optional[str]:
        """Fetches the raw GCG representation of a game."""
        url = f"{WOOGLES_BASE_URL}/game/{game_id}/gcg"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.text
            return None
        except Exception:
            return None

    def download_games_batch(self, game_ids: List[str]) -> int:
        """Downloads and saves GCG files for a list of game IDs."""
        downloaded = 0
        for gid in tqdm(game_ids, desc="Downloading GCGs"):
            out_file = os.path.join(self.output_dir, f"{gid}.gcg")
            if os.path.exists(out_file) and os.path.getsize(out_file) > 50:
                downloaded += 1
                continue

            gcg_text = self.fetch_gcg(gid)
            if gcg_text:
                with open(out_file, "w", encoding="utf-8") as f:
                    f.write(gcg_text)
                downloaded += 1

            time.sleep(self.delay)

        return downloaded
