"""
Evaluation Harness and Match Simulation Engine for Alphable V4.

Simulates complete, tournament-rule Scrabble games between Alphable V4 (BAMS)
and baseline engines (Static Greedy, HastyBot, or self-play).
Tracks:
- Win rate
- Mean scores
- Bingos per game
- Invalid move violations (must be 0)
- End-game tile penalties according to official WESPA/NASPA rules
"""

from __future__ import annotations
import random
import time
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any, Callable

import numpy as np

from alphable_v4.engine.move import Move
from alphable_v4.engine.game_state import GameState, STANDARD_TILE_COUNTS, TILE_VALUES
from alphable_v4.engine.magpie_bindings import MagpieEngine
from alphable_v4.search.bams import BAMSSearch, BAMSConfig


@dataclass
class MatchStats:
    """Aggregated match series metrics."""
    games_played: int = 0
    p1_wins: int = 0
    p2_wins: int = 0
    draws: int = 0
    p1_total_score: int = 0
    p2_total_score: int = 0
    p1_total_bingos: int = 0
    p2_total_bingos: int = 0
    p1_invalid_moves: int = 0
    p2_invalid_moves: int = 0
    game_results: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def p1_win_rate(self) -> float:
        return (self.p1_wins + 0.5 * self.draws) / max(1, self.games_played)

    @property
    def p1_mean_score(self) -> float:
        return self.p1_total_score / max(1, self.games_played)

    @property
    def p2_mean_score(self) -> float:
        return self.p2_total_score / max(1, self.games_played)

    @property
    def p1_bingos_per_game(self) -> float:
        return self.p1_total_bingos / max(1, self.games_played)

    @property
    def p2_bingos_per_game(self) -> float:
        return self.p2_total_bingos / max(1, self.games_played)


class ScrabbleBag:
    """Simulates the physical Scrabble tile bag."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.tiles: List[str] = []
        for tile, count in STANDARD_TILE_COUNTS.items():
            self.tiles.extend([tile] * count)
        self.rng.shuffle(self.tiles)

    def draw(self, n: int) -> List[str]:
        drawn = []
        for _ in range(min(n, len(self.tiles))):
            drawn.append(self.tiles.pop())
        return drawn

    def exchange(self, rack_tiles: List[str]) -> List[str]:
        drawn = self.draw(len(rack_tiles))
        self.tiles.extend(rack_tiles)
        self.rng.shuffle(self.tiles)
        return drawn

    @property
    def count(self) -> int:
        return len(self.tiles)


def get_game_phase(turn_num: int, bag_count: int) -> str:
    """
    Classifies the game state into one of four distinct phases:
    - OPENING: turns 1 to 5
    - MIDGAME: turn > 5 and bag > 14
    - PRE_ENDGAME: bag in 1..14
    - ENDGAME: bag == 0
    """
    if bag_count == 0:
        return "endgame"
    elif 1 <= bag_count <= 14:
        return "pre_endgame"
    elif turn_num <= 5:
        return "opening"
    else:
        return "midgame"


class GameSimulator:
    """Runs full 2-player Scrabble matches."""

    def __init__(self, engine: MagpieEngine, lexicon: str = "CSW24"):
        self.engine = engine
        self.lexicon = lexicon

    def play_game(
        self,
        p1_policy: Callable[[GameState], Tuple[Move, Dict[str, Any]]],
        p2_policy: Callable[[GameState], Tuple[Move, Dict[str, Any]]],
        seed: Optional[int] = None,
        max_turns: int = 60,
    ) -> Dict[str, Any]:
        """
        Plays a single game to completion.

        Returns:
            Dict containing scores, winner, turn history, and bingo statistics.
        """
        bag = ScrabbleBag(seed=seed)
        board = [[None for _ in range(15)] for _ in range(15)]
        p1_rack = bag.draw(7)
        p2_rack = bag.draw(7)
        p1_score = 0
        p2_score = 0
        p1_bingos = 0
        p2_bingos = 0
        p1_invalid = 0
        p2_invalid = 0

        scoreless_turns = 0
        turn_history = []
        phase_scores: Dict[str, Dict[str, int]] = {
            "opening": {"p1": 0, "p2": 0},
            "midgame": {"p1": 0, "p2": 0},
            "pre_endgame": {"p1": 0, "p2": 0},
            "endgame": {"p1": 0, "p2": 0},
        }
        phase_counts: Dict[str, Dict[str, int]] = {
            "opening": {"p1": 0, "p2": 0},
            "midgame": {"p1": 0, "p2": 0},
            "pre_endgame": {"p1": 0, "p2": 0},
            "endgame": {"p1": 0, "p2": 0},
        }

        turn_num = 0
        while turn_num < max_turns:
            # Player 1's Turn
            turn_num += 1
            phase_p1 = get_game_phase(turn_num, bag.count)
            phase_counts[phase_p1]["p1"] += 1
            state_p1 = GameState(
                board=board,
                rack=p1_rack,
                opp_rack=p2_rack,
                score=p1_score,
                opp_score=p2_score,
                scoreless_turns=scoreless_turns,
                bag_count=bag.count,
                lexicon=self.lexicon,
            )

            try:
                move_p1, meta_p1 = p1_policy(state_p1)
            except Exception:
                move_p1 = Move.create_pass()
                meta_p1 = {"error": "policy_exception"}

            if move_p1.is_placement:
                try:
                    board = state_p1.apply_move(move_p1).board
                except Exception:
                    p1_invalid += 1

                p1_score += move_p1.score
                phase_scores[phase_p1]["p1"] += move_p1.score
                if move_p1.leave is not None and len(move_p1.leave) <= len(p1_rack):
                    tiles_played = len(p1_rack) - len(move_p1.leave)
                    p1_rack = list(move_p1.leave)
                else:
                    tiles_played = min(len(p1_rack), len(move_p1.word))
                    for t in move_p1.word:
                        if t in p1_rack:
                            p1_rack.remove(t)
                        elif '?' in p1_rack:
                            p1_rack.remove('?')

                if tiles_played == 7:
                    p1_bingos += 1

                # Draw new tiles
                p1_rack.extend(bag.draw(7 - len(p1_rack)))
                scoreless_turns = 0
            elif move_p1.is_exchange:
                # Exchange tiles with the bag
                if move_p1.leave is not None and len(move_p1.leave) < len(p1_rack):
                    exch_tiles = list(p1_rack)
                    for t in move_p1.leave:
                        if t in exch_tiles:
                            exch_tiles.remove(t)
                else:
                    exch_tiles = [t.upper() for t in move_p1.word if t.upper() in p1_rack]

                if bag.count >= len(exch_tiles) and len(exch_tiles) > 0:
                    for t in exch_tiles:
                        p1_rack.remove(t)
                    drawn = bag.exchange(exch_tiles)
                    p1_rack.extend(drawn)
                scoreless_turns += 1
            else:
                scoreless_turns += 1

            turn_history.append({
                "player": 1,
                "turn": turn_num,
                "phase": phase_p1,
                "move": str(move_p1),
                "score": move_p1.score,
                "total": p1_score,
            })

            # Check Player 1 out of tiles and bag empty
            if len(p1_rack) == 0 and bag.count == 0:
                penalty = sum(TILE_VALUES.get(t.upper(), 0) for t in p2_rack)
                p1_score += 2 * penalty
                phase_scores["endgame"]["p1"] += 2 * penalty
                break

            if scoreless_turns >= 6:
                break

            # Player 2's Turn
            turn_num += 1
            phase_p2 = get_game_phase(turn_num, bag.count)
            phase_counts[phase_p2]["p2"] += 1
            state_p2 = GameState(
                board=board,
                rack=p2_rack,
                opp_rack=p1_rack,
                score=p2_score,
                opp_score=p1_score,
                scoreless_turns=scoreless_turns,
                bag_count=bag.count,
                lexicon=self.lexicon,
            )

            try:
                move_p2, meta_p2 = p2_policy(state_p2)
            except Exception:
                move_p2 = Move.create_pass()
                meta_p2 = {"error": "policy_exception"}

            if move_p2.is_placement:
                try:
                    board = state_p2.apply_move(move_p2).board
                except Exception:
                    p2_invalid += 1

                p2_score += move_p2.score
                phase_scores[phase_p2]["p2"] += move_p2.score
                if move_p2.leave is not None and len(move_p2.leave) <= len(p2_rack):
                    tiles_played = len(p2_rack) - len(move_p2.leave)
                    p2_rack = list(move_p2.leave)
                else:
                    tiles_played = min(len(p2_rack), len(move_p2.word))
                    for t in move_p2.word:
                        if t in p2_rack:
                            p2_rack.remove(t)
                        elif '?' in p2_rack:
                            p2_rack.remove('?')

                if tiles_played == 7:
                    p2_bingos += 1

                p2_rack.extend(bag.draw(7 - len(p2_rack)))
                scoreless_turns = 0
            elif move_p2.is_exchange:
                # Exchange tiles with the bag
                if move_p2.leave is not None and len(move_p2.leave) < len(p2_rack):
                    exch_tiles = list(p2_rack)
                    for t in move_p2.leave:
                        if t in exch_tiles:
                            exch_tiles.remove(t)
                else:
                    exch_tiles = [t.upper() for t in move_p2.word if t.upper() in p2_rack]

                if bag.count >= len(exch_tiles) and len(exch_tiles) > 0:
                    for t in exch_tiles:
                        p2_rack.remove(t)
                    drawn = bag.exchange(exch_tiles)
                    p2_rack.extend(drawn)
                scoreless_turns += 1
            else:
                scoreless_turns += 1

            turn_history.append({
                "player": 2,
                "turn": turn_num,
                "phase": phase_p2,
                "move": str(move_p2),
                "score": move_p2.score,
                "total": p2_score,
            })

            if len(p2_rack) == 0 and bag.count == 0:
                penalty = sum(TILE_VALUES.get(t.upper(), 0) for t in p1_rack)
                p2_score += 2 * penalty
                phase_scores["endgame"]["p2"] += 2 * penalty
                break

            if scoreless_turns >= 6:
                break

        # If game ended with passes, deduct remaining rack points from each player
        if bag.count > 0 or (len(p1_rack) > 0 and len(p2_rack) > 0):
            p1_rem = sum(TILE_VALUES.get(t.upper(), 0) for t in p1_rack)
            p2_rem = sum(TILE_VALUES.get(t.upper(), 0) for t in p2_rack)
            p1_score -= p1_rem
            p2_score -= p2_rem
            phase_scores["endgame"]["p1"] -= p1_rem
            phase_scores["endgame"]["p2"] -= p2_rem

        winner = 1 if p1_score > p2_score else (2 if p2_score > p1_score else 0)
        return {
            "winner": winner,
            "p1_score": p1_score,
            "p2_score": p2_score,
            "p1_bingos": p1_bingos,
            "p2_bingos": p2_bingos,
            "p1_invalid": p1_invalid,
            "p2_invalid": p2_invalid,
            "total_turns": turn_num,
            "turn_history": turn_history,
            "phase_scores": phase_scores,
            "phase_counts": phase_counts,
        }

    def run_match_series(
        self,
        p1_policy: Callable[[GameState], Tuple[Move, Dict[str, Any]]],
        p2_policy: Callable[[GameState], Tuple[Move, Dict[str, Any]]],
        num_games: int = 10,
        start_seed: int = 1000,
        verbose: bool = True,
    ) -> MatchStats:
        """Executes a multi-game tournament series."""
        stats = MatchStats()

        for g_idx in range(num_games):
            seed = start_seed + g_idx
            res = self.play_game(p1_policy, p2_policy, seed=seed)

            stats.games_played += 1
            stats.p1_total_score += res["p1_score"]
            stats.p2_total_score += res["p2_score"]
            stats.p1_total_bingos += res["p1_bingos"]
            stats.p2_total_bingos += res["p2_bingos"]
            stats.p1_invalid_moves += res["p1_invalid"]
            stats.p2_invalid_moves += res["p2_invalid"]
            stats.game_results.append(res)

            if res["winner"] == 1:
                stats.p1_wins += 1
            elif res["winner"] == 2:
                stats.p2_wins += 1
            else:
                stats.draws += 1

            if verbose:
                print(
                    f"Game {g_idx+1:03d}/{num_games:03d}: P1 {res['p1_score']} - {res['p2_score']} P2 "
                    f"| Winner: {'P1' if res['winner']==1 else ('P2' if res['winner']==2 else 'Tie')} "
                    f"| Bingos: {res['p1_bingos']}-{res['p2_bingos']}"
                )

        return stats
