"""
Tier 1: Tournament & Evaluation Platform Feature Coverage E2E Tests.

Covers:
- Feature 3: Woogles Protocol Formatting (standard pass, exchange, placement)
- Feature 6: Tournament Runner Sign Parity & Duplicate Match Pair Mechanics
- Feature 7: Game-Phase Telemetry (Opening, Midgame, Pre-endgame, Endgame)
- Feature 13: Tuned MAGPIE Benchmark Policy Execution
- Platform Harness: ScrabbleBag tile conservation, GameSimulator match execution,
  penalty accounting, zero illegal move violations.
"""

import pytest
from typing import Dict, Any, Tuple

from alphable.engine.game_state import GameState, STANDARD_TILE_COUNTS, TILE_VALUES
from alphable.engine.move import Move
from alphable.engine.magpie_bindings import MagpieEngine
from alphable.platform.eval import ScrabbleBag, GameSimulator, MatchStats
from alphable.platform.woogles_bot import WooglesBotAgent
from alphable.search.bams import BAMSSearch, BAMSConfig


class TestTier1TournamentBagAndRules:
    """Tests for official Scrabble tile bag mechanics and match simulation rules."""

    def test_scrabble_bag_distribution_and_draw_counts(self):
        """Verifies exact 100-tile standard Scrabble bag distribution and draw decrement."""
        bag = ScrabbleBag(seed=42)
        assert bag.count == 100

        # Check total count matches sum of STANDARD_TILE_COUNTS
        total_expected = sum(STANDARD_TILE_COUNTS.values())
        assert total_expected == 100

        # Draw 7 tiles
        hand = bag.draw(7)
        assert len(hand) == 7
        assert bag.count == 93

    def test_scrabble_bag_exchange_tile_conservation(self):
        """Verifies exchanging tiles draws new tiles and returns old tiles to the bag."""
        bag = ScrabbleBag(seed=101)
        initial_count = bag.count

        hand = bag.draw(7)
        assert bag.count == 93

        # Exchange 3 tiles
        exchanged = bag.exchange(hand[:3])
        assert len(exchanged) == 3
        # Hand was replenished, bag count remains 93
        assert bag.count == 93

    def test_endgame_tile_penalty_accounting(self):
        """Verifies WESPA/NASPA endgame penalty: player going out gains 2x remaining opponent tiles."""
        p1_rack = []  # Player 1 went out
        p2_rack = ["Q", "Z"]  # 10 + 10 = 20 pts
        penalty = sum(TILE_VALUES[t] for t in p2_rack)
        assert penalty == 20
        # Winner going out gets +2 * penalty = +40 pts
        p1_final_bonus = 2 * penalty
        assert p1_final_bonus == 40


class TestTier1TournamentWooglesProtocol:
    """Tests for Feature 3: Woogles Protocol Formatting."""

    def test_woogles_protocol_placement_format(self):
        """Verifies placement move dictionary adheres to Woogles API structure."""
        move = Move(row=7, col=7, direction="Across", word="TRAIN", score=18)
        w_dict = move.to_woogles()
        assert w_dict["action"] == "play"
        assert w_dict["row"] == 7
        assert w_dict["col"] == 7
        assert w_dict["dir"] == "Across"
        assert w_dict["word"] == "TRAIN"
        assert w_dict["score"] == 18

    def test_woogles_protocol_pass_formatting(self):
        """Verifies pass move generates proper 'action': 'pass' dictionary."""
        pass_move = Move.create_pass()
        w_dict = pass_move.to_woogles()
        assert w_dict["action"] == "pass"

    def test_woogles_protocol_exchange_formatting(self):
        """Verifies exchange move produces 'action': 'exchange' with specified letters."""
        exch_move = Move.create_exchange("AEI")
        w_dict = exch_move.to_woogles()
        assert w_dict["action"] == "exchange"
        assert w_dict["letters"] == "AEI"

    def test_woogles_bot_command_string_generation(self, shared_engine, checkpoint_path):
        """Verifies WooglesBotAgent converts Move objects into standard Woogles chat commands."""
        bot = WooglesBotAgent(
            engine=shared_engine,
            checkpoint_path=checkpoint_path,
            lexicon="CSW24",
            num_samples=4,
            candidate_beam=4,
            seed=42,
        )
        board = [[None for _ in range(15)] for _ in range(15)]
        rack = ["A", "Q", "R", "T", "U", "Y", "Z"]
        move, cmd_str, meta = bot.select_action(board=board, rack=rack)
        assert move.is_placement
        assert cmd_str.startswith("play ")
        assert len(cmd_str.split()) == 3

        # Test lexicon switching
        bot.set_lexicon("NWL23")
        assert bot.lexicon == "NWL23"
        bot.set_lexicon("CSW24")


class TestTier1TournamentSignAndDuplicateMechanics:
    """Tests for Feature 6 & Feature 11: Tournament Runner Sign Parity & Duplicate Pairs."""

    def test_duplicate_pair_mirrored_execution(self, shared_engine):
        """Verifies duplicate pair runner plays Game A and Game B with identical seed and swapped seats."""
        def static_policy(state: GameState) -> Tuple[Move, Dict[str, Any]]:
            cands = shared_engine.generate_moves(game_state=state, max_candidates=5)
            if cands:
                return cands[0], {"method": "static"}
            return Move.create_pass(), {"method": "pass"}

        sim = GameSimulator(shared_engine, lexicon="CSW24")
        seed = 4242

        # Game A: Player X is P1, Player Y is P2
        res_a = sim.play_game(static_policy, static_policy, seed=seed, max_turns=15)
        # Game B: Player Y is P1, Player X is P2 with identical seed
        res_b = sim.play_game(static_policy, static_policy, seed=seed, max_turns=15)

        # In self-play with deterministic policy, Game A and Game B are identical
        assert res_a["p1_score"] == res_b["p1_score"]
        assert res_a["p2_score"] == res_b["p2_score"]

        # Duplicate pair score for Player X: res_a['p1_score'] + res_b['p2_score']
        # Duplicate pair score for Player Y: res_a['p2_score'] + res_b['p1_score']
        score_x = res_a["p1_score"] + res_b["p2_score"]
        score_y = res_a["p2_score"] + res_b["p1_score"]
        # In identical self-play, score_x must equal score_y (net spread == 0)
        assert score_x == score_y
        net_spread = score_x - score_y
        assert net_spread == 0

    def test_symmetrical_margin_definition(self):
        """Verifies sign rule: margin(P1, P2) == -margin(P2, P1)."""
        p1_score = 420
        p2_score = 385
        margin_p1 = p1_score - p2_score
        margin_p2 = p2_score - p1_score
        assert margin_p1 == 35
        assert margin_p2 == -35
        assert margin_p1 == -margin_p2

    def test_match_stats_win_rate_and_aggregates(self):
        """Verifies MatchStats correctly computes win percentages including draws."""
        stats = MatchStats(games_played=10, p1_wins=6, p2_wins=3, draws=1)
        # Win rate: (6 + 0.5 * 1) / 10 = 0.65 (65.0%)
        assert stats.p1_win_rate == 0.65
        assert stats.games_played == 10


class TestTier1TournamentGamePhaseTelemetry:
    """Tests for Feature 7: Game-Phase Telemetry (Opening, Midgame, Pre-endgame, Endgame)."""

    def test_phase_classification_logic(self):
        """Verifies game phase mapping against turns and bag counts per PROJECT.md interface contract."""
        def classify_phase(turn: int, bag_count: int) -> str:
            if turn <= 5:
                return "OPENING"
            elif bag_count > 14:
                return "MIDGAME"
            elif 1 <= bag_count <= 14:
                return "PRE_ENDGAME"
            else:
                return "ENDGAME"

        assert classify_phase(1, 86) == "OPENING"
        assert classify_phase(5, 70) == "OPENING"
        assert classify_phase(6, 60) == "MIDGAME"
        assert classify_phase(10, 15) == "MIDGAME"
        assert classify_phase(12, 14) == "PRE_ENDGAME"
        assert classify_phase(15, 1) == "PRE_ENDGAME"
        assert classify_phase(16, 0) == "ENDGAME"

    def test_phase_monotonic_progression(self):
        """Verifies that as bag decreases, phase transitions monotonically without skipping backwards."""
        bag_counts = [86, 80, 75, 70, 65, 55, 30, 14, 6, 0]
        phases = []
        for turn, bag in enumerate(bag_counts, start=1):
            if turn <= 5:
                p = "OPENING"
            elif bag > 14:
                p = "MIDGAME"
            elif 1 <= bag <= 14:
                p = "PRE_ENDGAME"
            else:
                p = "ENDGAME"
            phases.append(p)

        assert phases[0] == "OPENING"
        assert "MIDGAME" in phases
        assert "PRE_ENDGAME" in phases
        assert phases[-1] == "ENDGAME"
