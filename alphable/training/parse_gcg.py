"""
High-throughput GCG (Generic Crossword Game) parser for Alphable V4.

Parses .gcg match logs into structured board states and move sequences,
accurately handling through-tiles ('.'), designated blanks (lowercase letters),
exchanges, passes, and endgame rack deductions.
"""

from __future__ import annotations
import os
import re
import glob
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path

from alphable.engine.move import Move
from alphable.engine.game_state import GameState, STANDARD_TILE_COUNTS


@dataclass
class ParsedTurn:
    """Structured representation of a single Scrabble turn in a game."""
    turn_index: int
    player: str
    rack: str
    coord: str
    word: str
    points: int
    total_score: int
    is_pass: bool = False
    is_exchange: bool = False
    exchanged_tiles: str = ""
    placed_tiles: List[Tuple[int, int, str, bool]] = field(default_factory=list)  # (r, c, char, is_blank)
    board_before_cgp: str = ""
    board_after_cgp: str = ""
    score_diff: int = 0
    bag_remaining: int = 86
    final_margin: int = 0


@dataclass
class ParsedGame:
    """Structured representation of an entire parsed Scrabble game."""
    game_id: str
    lexicon: str
    player1: str
    player2: str
    final_score1: int
    final_score2: int
    turns: List[ParsedTurn] = field(default_factory=list)
    winner: str = ""
    spread: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def parse_gcg_coordinate(coord_str: str) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    """
    Parses GCG coordinate string (e.g. '8F', '11E', 'C10', '15A', '-', 'pass').
    Returns (row, col, direction). Both 0-indexed.
    """
    coord = coord_str.strip()
    if coord in ("-", "pass", "--") or coord.startswith("("):
        return None, None, None

    # Across: e.g. 8F, 15A
    if coord[0].isdigit():
        match = re.match(r"^(\d+)([A-Oa-o])$", coord)
        if match:
            row = int(match.group(1)) - 1
            col = ord(match.group(2).upper()) - ord('A')
            return row, col, "Across"
    else:
        # Down: e.g. C10, H8
        match = re.match(r"^([A-Oa-o])(\d+)$", coord)
        if match:
            col = ord(match.group(1).upper()) - ord('A')
            row = int(match.group(2)) - 1
            return row, col, "Down"

    return None, None, None


def parse_gcg_text(text: str, game_id: str = "") -> Optional[ParsedGame]:
    """
    Parses full GCG file content and replays the game on a 15x15 board.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return None

    lexicon = "CSW24"
    player1 = ""
    player2 = ""
    raw_moves = []
    final_scores: Dict[str, int] = {}

    for line in lines:
        if line.startswith("#id"):
            parts = line.split()
            if len(parts) >= 3 and not game_id:
                game_id = parts[2]
            elif len(parts) >= 2 and not game_id:
                game_id = parts[1]
        elif line.startswith("#lexicon"):
            parts = line.split()
            if len(parts) >= 2:
                lexicon = parts[1]
        elif line.startswith("#player1"):
            parts = line.split()
            if len(parts) >= 2:
                player1 = parts[1]
        elif line.startswith("#player2"):
            parts = line.split()
            if len(parts) >= 2:
                player2 = parts[1]
        elif line.startswith(">"):
            # Move line: >Player: RACK COORDS WORD +PTS TOTAL
            # or endgame adjustment: >Player: (LEAVE) +PTS TOTAL
            content = line[1:].strip()
            parts = content.split()
            if len(parts) < 3:
                continue

            player = parts[0].rstrip(":")

            # Check if this is an endgame rack bonus line like `>Player: (D) +4 482`
            if parts[1].startswith("(") and parts[1].endswith(")"):
                tot = 0
                for p in parts[2:]:
                    if not p.startswith("+") and p.lstrip("-").isdigit():
                        tot = int(p)
                        final_scores[player] = tot
                continue

            rack = parts[1]
            coord = parts[2]
            word = parts[3] if len(parts) > 3 else ""

            pts = 0
            tot = 0
            for part in parts[4:]:
                if part.startswith("+"):
                    try:
                        pts = int(part[1:])
                    except ValueError:
                        pass
                elif part.lstrip("-").isdigit():
                    tot = int(part)
                    final_scores[player] = tot

            raw_moves.append({
                "player": player,
                "rack": rack,
                "coord": coord,
                "word": word,
                "points": pts,
                "total": tot,
            })

    # Deduce player names if missing from headers
    if not player1 or not player2:
        seen_players = []
        for rm in raw_moves:
            if rm["player"] not in seen_players:
                seen_players.append(rm["player"])
        if len(seen_players) >= 2:
            player1 = seen_players[0]
            player2 = seen_players[1]
        elif len(seen_players) == 1:
            player1 = seen_players[0]
            player2 = "Opponent"
        else:
            return None

    # Replay board turn by turn
    board: List[List[Optional[str]]] = [[None for _ in range(15)] for _ in range(15)]
    scores = {player1: 0, player2: 0}
    tiles_played_total = 0
    parsed_turns: List[ParsedTurn] = []

    p1_final = final_scores.get(player1, scores[player1])
    p2_final = final_scores.get(player2, scores[player2])

    for t_idx, rm in enumerate(raw_moves):
        curr_p = rm["player"]
        opp_p = player2 if curr_p == player1 else player1
        curr_rack = rm["rack"].replace(".", "")

        my_score = scores.get(curr_p, 0)
        opp_score = scores.get(opp_p, 0)
        score_diff = my_score - opp_score

        bag_remaining = max(0, 100 - tiles_played_total - 14)

        # Snapshot board before move
        board_before_state = GameState(
            board=board,
            rack=list(curr_rack),
            score=my_score,
            opp_score=opp_score,
            bag_count=bag_remaining,
            lexicon=lexicon,
        )
        before_cgp = board_before_state.to_cgp()

        coord_str = rm["coord"]
        word_str = rm["word"]
        pts = rm["points"]

        is_pass = coord_str in ("-", "pass", "--") or word_str.lower() == "pass"
        is_exchange = False
        exchanged_tiles = ""
        placed_tiles = []

        if coord_str.startswith("-") and len(coord_str) > 1:
            # Exchange: e.g. -ABC
            is_exchange = True
            exchanged_tiles = coord_str[1:]
        elif word_str.startswith("-"):
            is_exchange = True
            exchanged_tiles = word_str[1:]

        if not is_pass and not is_exchange:
            row, col, direction = parse_gcg_coordinate(coord_str)
            if row is not None and col is not None and direction is not None:
                curr_r = row
                curr_c = col
                # Play word: '.' represents through tile already on board
                for ch in word_str:
                    if ch == '.':
                        # Skipped through-tile
                        pass
                    else:
                        # Placed tile: ch.islower() indicates blank tile assigned to that letter
                        is_blank = ch.islower()
                        letter_to_place = ch.lower() if is_blank else ch.upper()
                        board[curr_r][curr_c] = letter_to_place
                        placed_tiles.append((curr_r, curr_c, ch.upper(), is_blank))
                        tiles_played_total += 1

                    if direction == "Across":
                        curr_c += 1
                    else:
                        curr_r += 1

        # Update scores
        scores[curr_p] = scores.get(curr_p, 0) + pts

        # Snapshot board after move
        board_after_state = GameState(
            board=board,
            rack=[],
            score=scores[curr_p],
            opp_score=scores[opp_p],
            bag_count=max(0, 100 - tiles_played_total - 14),
            lexicon=lexicon,
        )
        after_cgp = board_after_state.to_cgp()

        final_margin = (p1_final - p2_final) if curr_p == player1 else (p2_final - p1_final)

        parsed_turns.append(ParsedTurn(
            turn_index=t_idx,
            player=curr_p,
            rack=curr_rack,
            coord=coord_str,
            word=word_str,
            points=pts,
            total_score=scores[curr_p],
            is_pass=is_pass,
            is_exchange=is_exchange,
            exchanged_tiles=exchanged_tiles,
            placed_tiles=placed_tiles,
            board_before_cgp=before_cgp,
            board_after_cgp=after_cgp,
            score_diff=score_diff,
            bag_remaining=bag_remaining,
            final_margin=final_margin,
        ))

    score1 = final_scores.get(player1, scores.get(player1, 0))
    score2 = final_scores.get(player2, scores.get(player2, 0))
    winner = player1 if score1 > score2 else (player2 if score2 > score1 else "Tie")
    spread = score1 - score2

    return ParsedGame(
        game_id=game_id,
        lexicon=lexicon,
        player1=player1,
        player2=player2,
        final_score1=score1,
        final_score2=score2,
        turns=parsed_turns,
        winner=winner,
        spread=spread,
    )


def parse_gcg_file(filepath: str) -> Optional[ParsedGame]:
    """Reads and parses a .gcg file from disk."""
    try:
        path = Path(filepath)
        game_id = path.stem
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        return parse_gcg_text(text, game_id=game_id)
    except Exception:
        return None
