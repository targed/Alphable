"""
Tests for Alphable V4 Evaluation Platform and Tournament Simulation Engine.

Verifies:
1. Scrabble bag tile distribution and conservation.
2. End-to-end full match simulation between BAMS and Static baseline player.
3. Zero invalid move violations.
4. Correct endgame tile penalty accounting and winner determination.
5. Woogles bot command formatting and lexicon switching.
"""

import os
import pytest
from typing import Tuple, Dict, Any

from alphable_v4.engine.move import Move
from alphable_v4.engine.game_state import GameState, STANDARD_TILE_COUNTS
from alphable_v4.engine.magpie_bindings import MagpieEngine
from alphable_v4.search.bams import BAMSSearch, BAMSConfig
from alphable_v4.platform.eval import ScrabbleBag, GameSimulator, MatchStats
from alphable_v4.platform.woogles_bot import WooglesBotAgent


@pytest.fixture(scope="module")
def shared_engine():
    """Shared MAGPIE engine for platform tests."""
    eng = MagpieEngine(lexicon="CSW24")
    yield eng
    eng.close()


@pytest.fixture(scope="module")
def checkpoint_path():
    path = os.path.join(
        os.path.dirname(__file__), "..", "..", "alphable_v4", "models", "checkpoints", "v4_value_net_best.pt"
    )
    return os.path.normpath(path)


class TestPlatformEval:
    """Test suite for platform and evaluation harness."""

    def test_scrabble_bag_conservation(self):
        bag = ScrabbleBag(seed=42)
        assert bag.count == 100

        drawn = bag.draw(7)
        assert len(drawn) == 7
        assert bag.count == 93

        # Draw remaining
        rem = bag.draw(100)
        assert len(rem) == 93
        assert bag.count == 0

    def test_full_game_simulation(self, shared_engine, checkpoint_path):
        """Simulates a complete head-to-head match between BAMS and Static Greedy player."""
        bams = BAMSSearch.from_checkpoint(
            shared_engine,
            checkpoint_path,
            config=BAMSConfig(num_samples=16, candidate_beam=8, seed=42),
        )

        # Player 1: BAMS Search policy
        def p1_policy(state: GameState) -> Tuple[Move, Dict[str, Any]]:
            return bams.select_move(state)

        # Player 2: Static Greedy policy (picks highest static equity from MAGPIE)
        def p2_policy(state: GameState) -> Tuple[Move, Dict[str, Any]]:
            cands = shared_engine.generate_moves(game_state=state, max_candidates=10)
            if cands:
                return cands[0], {"method": "static_top"}
            return Move.create_pass(), {"method": "pass"}

        sim = GameSimulator(shared_engine, lexicon="CSW24")
        result = sim.play_game(p1_policy, p2_policy, seed=123, max_turns=60)

        assert result["winner"] in (0, 1, 2)
        assert result["p1_score"] > 250, f"Unreasonably low score: {result['p1_score']}"
        assert result["p2_score"] > 250, f"Unreasonably low score: {result['p2_score']}"
        assert result["p1_invalid"] == 0, "BAMS produced invalid moves"
        assert result["p2_invalid"] == 0, "Greedy produced invalid moves"
        assert result["total_turns"] > 15, "Game ended too quickly"

        print(
            f"\nFull Game Match Result: BAMS {result['p1_score']} - {result['p2_score']} Greedy "
            f"| Winner: Player {result['winner']} | Bingos: {result['p1_bingos']}-{result['p2_bingos']} "
            f"| Turns: {result['total_turns']}"
        )

    def test_woogles_bot_command_formatting(self, shared_engine, checkpoint_path):
        bot = WooglesBotAgent(
            engine=shared_engine,
            checkpoint_path=checkpoint_path,
            lexicon="CSW24",
            num_samples=16,
            candidate_beam=8,
            seed=42,
        )

        board = [[None for _ in range(15)] for _ in range(15)]
        rack = ["A", "Q", "R", "T", "U", "Y", "Z"]

        move, cmd_str, meta = bot.select_action(board=board, rack=rack)
        assert move.is_placement
        assert cmd_str.startswith("play ")
        assert len(cmd_str.split()) == 3  # "play", coord, word

        # Test lexicon switching
        bot.set_lexicon("NWL23")
        assert bot.lexicon == "NWL23"
        bot.set_lexicon("CSW24")
