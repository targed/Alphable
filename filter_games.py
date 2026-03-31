#!/usr/bin/env python3
"""
Filter games from Woogles metadata based on various criteria.
"""
import json
from typing import List, Dict, Any, Optional


def filter_by_rating(games: List[Dict], min_rating: Optional[int] = None,
                     max_rating: Optional[int] = None, player_index: int = 0) -> List[Dict]:
    """Filter games by player rating range."""
    filtered = []
    for game in games:
        if player_index >= len(game['players']):
            continue
        rating_str = game['players'][player_index]['rating']
        # Remove '?' for provisional ratings
        rating_str = rating_str.replace('?', '')
        try:
            rating = int(rating_str)
            if min_rating is not None and rating < min_rating:
                continue
            if max_rating is not None and rating > max_rating:
                continue
            filtered.append(game)
        except ValueError:
            continue
    return filtered


def filter_by_lexicon(games: List[Dict], lexicons: List[str]) -> List[Dict]:
    """Filter games by lexicon(s)."""
    return [g for g in games if g.get('game_request', {}).get('lexicon') in lexicons]


def filter_by_game_type(games: List[Dict], bot_game: Optional[bool] = None,
                        tournament: Optional[bool] = None) -> List[Dict]:
    """Filter games by type (bot vs human, tournament vs casual)."""
    filtered = games

    if bot_game is not None:
        filtered = [g for g in filtered
                    if g.get('game_request', {}).get('player_vs_bot', False) == bot_game]

    if tournament is not None:
        if tournament:
            filtered = [g for g in filtered if g.get('tournament_id', '')]
        else:
            filtered = [g for g in filtered if not g.get('tournament_id', '')]

    return filtered


def filter_by_time_control(games: List[Dict], time_control_names: List[str]) -> List[Dict]:
    """Filter games by time control name."""
    return [g for g in games if g.get('time_control_name') in time_control_names]


def filter_by_variant(games: List[Dict], variants: List[str]) -> List[Dict]:
    """Filter games by variant (classic, wordsmog, etc.)."""
    return [g for g in games
            if g.get('game_request', {}).get('rules', {}).get('variant_name') in variants]


def filter_by_winner(games: List[Dict], player_index: Optional[int] = None) -> List[Dict]:
    """Filter games by winner. If player_index specified, only games where that player won."""
    if player_index is None:
        return games
    return [g for g in games if g.get('winner') == player_index]


def filter_by_score_margin(games: List[Dict], min_margin: int = 0,
                           max_margin: Optional[int] = None) -> List[Dict]:
    """Filter games by score margin (absolute difference)."""
    filtered = []
    for game in games:
        scores = game.get('scores', [])
        if len(scores) >= 2:
            margin = abs(scores[0] - scores[1])
            if margin >= min_margin:
                if max_margin is None or margin <= max_margin:
                    filtered.append(game)
    return filtered


def apply_filters(games: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
    """Apply multiple filters to games based on filter dictionary."""
    result = games

    if 'min_rating' in filters or 'max_rating' in filters:
        result = filter_by_rating(
            result,
            min_rating=filters.get('min_rating'),
            max_rating=filters.get('max_rating'),
            player_index=filters.get('rating_player_index', 0)
        )

    if 'lexicons' in filters:
        result = filter_by_lexicon(result, filters['lexicons'])

    if 'bot_game' in filters:
        result = filter_by_game_type(result, bot_game=filters['bot_game'])

    if 'tournament' in filters:
        result = filter_by_game_type(result, tournament=filters['tournament'])

    if 'time_controls' in filters:
        result = filter_by_time_control(result, filters['time_controls'])

    if 'variants' in filters:
        result = filter_by_variant(result, filters['variants'])

    if 'winner_index' in filters:
        result = filter_by_winner(result, filters['winner_index'])

    if 'min_margin' in filters or 'max_margin' in filters:
        result = filter_by_score_margin(
            result,
            min_margin=filters.get('min_margin', 0),
            max_margin=filters.get('max_margin')
        )

    return result


def print_game_summary(games: List[Dict]):
    """Print summary statistics of games."""
    if not games:
        print("No games to summarize.")
        return

    print(f"\nTotal games: {len(games)}")

    # Lexicon distribution
    lexicons = {}
    for g in games:
        lex = g.get('game_request', {}).get('lexicon', 'Unknown')
        lexicons[lex] = lexicons.get(lex, 0) + 1
    print(f"\nLexicons: {dict(sorted(lexicons.items()))}")

    # Bot vs human
    bot_games = sum(1 for g in games if g.get(
        'game_request', {}).get('player_vs_bot', False))
    print(f"Bot games: {bot_games}, Human games: {len(games) - bot_games}")

    # Tournament games
    tournament_games = sum(1 for g in games if g.get('tournament_id', ''))
    print(
        f"Tournament games: {tournament_games}, Casual games: {len(games) - tournament_games}")

    # Average scores
    all_scores = [score for g in games for score in g.get('scores', [])]
    if all_scores:
        print(f"Average score: {sum(all_scores) / len(all_scores):.1f}")


if __name__ == '__main__':
    import sys

    # Load metadata
    metadata_file = sys.argv[1] if len(sys.argv) > 1 else 'woogles.json'
    with open(metadata_file, 'r') as f:
        data = json.load(f)

    games = data.get('game_info', [])
    print(f"Loaded {len(games)} games from {metadata_file}")

    # Example filters
    print("\n" + "="*60)
    print("EXAMPLE FILTERS:")

    # High-level bot games
    high_level = filter_by_rating(games, min_rating=1800)
    print(f"\n1. High-level games (rating >= 1800): {len(high_level)}")

    # CSW24 only
    csw24 = filter_by_lexicon(games, ['CSW24'])
    print(f"2. CSW24 games: {len(csw24)}")

    # Bot games only
    bot_only = filter_by_game_type(games, bot_game=True)
    print(f"3. Bot games: {len(bot_only)}")

    # Close games (margin <= 50 points)
    close_games = filter_by_score_margin(games, max_margin=50)
    print(f"4. Close games (margin <= 50): {len(close_games)}")

    # Combined: High-level CSW24 bot games
    combined_filters = {
        'min_rating': 1800,
        'lexicons': ['CSW24'],
        'bot_game': True
    }
    combined = apply_filters(games, combined_filters)
    print(f"\n5. Combined (high-level CSW24 bot games): {len(combined)}")
    print_game_summary(combined)
