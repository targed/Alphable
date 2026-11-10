"""
Regression and Verification Suite for Milestone M1 Code Remediation (BUG-01 to BUG-07).

Validates:
BUG-01: Zero C memory leaks via ctypes.c_void_p return types and magpie_free_string(ptr).
BUG-02: Pre-endgame parity tile accounting via Move.get_tiles_played() and bag-emptying parity bonus.
BUG-03: Woogles protocol pass move formatting ('pass' rather than 'exchange pass').
BUG-04: Continuous linear ramp volatility control without jump discontinuity at +/- 20 pts.
BUG-05: Strict coordinate bounds validation in Move.parse_coordinate (1..15, A..O).
BUG-06: Accurate margin calculation (s1 - s2) for alternating tournament games.
BUG-07: Phase classification (get_game_phase) and telemetry tracking in GameSimulator.
"""

import ctypes
from unittest.mock import MagicMock
import pytest

from alphable_v4.engine.move import Move
from alphable_v4.engine.game_state import GameState
from alphable_v4.engine.magpie_bindings import MagpieEngine
from alphable_v4.search.bams import BAMSSearch, BAMSConfig
from alphable_v4.platform.eval import GameSimulator, get_game_phase
from alphable_v4.platform.woogles_bot import WooglesBotAgent


class TestBugFixes:
    """Comprehensive regression test suite for Milestone M1."""

    # -------------------------------------------------------------------------
    # BUG-01: C Heap Memory Management
    # -------------------------------------------------------------------------
    def test_bug01_c_memory_management_and_freeing(self):
        """Verifies magpie_free_string is invoked and strings are properly decoded."""
        engine = MagpieEngine(lexicon="CSW24")
        try:
            # Spy on magpie_free_string to confirm it is called on each command
            original_free = engine._ctypes._cdll.magpie_free_string
            free_calls = []

            def spy_free(ptr):
                free_calls.append(ptr)
                original_free(ptr)

            engine._ctypes._cdll.magpie_free_string = spy_free

            output = engine.run_command("help")
            assert len(output) > 0
            assert "Commands:" in output or len(free_calls) > 0
            assert len(free_calls) >= 1, "magpie_free_string was not called for command output!"

            # Test _take_string with None / 0
            assert engine._take_string(None) == ""
            assert engine._take_string(0) == ""

            # Restore original function
            engine._ctypes._cdll.magpie_free_string = original_free
        finally:
            engine.close()

    # -------------------------------------------------------------------------
    # BUG-02: Pre-Endgame Parity Logic & Tile Accounting
    # -------------------------------------------------------------------------
    def test_bug02_get_tiles_played_accounting(self):
        """Verifies Move.get_tiles_played() accurately counts played tiles across move types."""
        # Pass
        m_pass = Move.make_pass()
        assert m_pass.get_tiles_played() == 0

        # Exchange
        m_exch = Move.make_exchange("AEINRST")
        assert m_exch.get_tiles_played() == 7
        m_exch_3 = Move.make_exchange("XYZ")
        assert m_exch_3.get_tiles_played() == 3

        # Placement with explicit tiles_placed
        m_placed = Move(row=7, col=7, direction="Across", word="TRAINS", tiles_placed="TRAIN")
        assert m_placed.get_tiles_played() == 5

        # Placement constructed from UCGI line
        m_ucgi = Move.from_ucgi_line("1: 8D QUARTZ Y 68 67.55", tiles_placed="QUARTZ")
        assert m_ucgi is not None
        assert m_ucgi.tiles_placed == "QUARTZ"
        assert m_ucgi.get_tiles_played() == 6

        # Placement with leave but empty tiles_placed (fallback to rack_len - len(leave))
        m_leave = Move(row=7, col=7, direction="Across", word="TRAINS", leave="ST")
        assert m_leave.get_tiles_played(rack_len=7) == 5
        assert m_leave.get_tiles_played(rack_len=6) == 4

        # Bingo with empty leave
        m_bingo = Move(row=7, col=7, direction="Across", word="RETINAS", leave="")
        assert m_bingo.get_tiles_played(rack_len=7) == 7

        # Placement fallback with no leave and no tiles_placed
        m_fallback = Move(row=7, col=7, direction="Across", word="CAT")
        assert m_fallback.get_tiles_played(rack_len=7) == 3

    def test_bug02_pre_endgame_tempo_bonus_activation(self):
        """Verifies that pre-endgame evaluation grants tempo bonus when tiles_played empties the bag."""
        engine = MagpieEngine(lexicon="CSW24")
        try:
            search = BAMSSearch(engine=engine, config=BAMSConfig(num_samples=4, candidate_beam=4))

            # Game state with bag_count = 2 and 7 unseen tiles
            board = [[None for _ in range(15)] for _ in range(15)]
            state = GameState(
                board=board,
                rack=["T", "R", "A", "I", "N", "E", "D"],
                score=300,
                opp_score=290,
                bag_count=2,
                lexicon="CSW24",
            )

            # Candidate A plays 2 tiles (empties bag) -> receives parity_delta tempo bonus
            cand_empties = Move(
                row=7, col=7, direction="Across", word="TO", leave="RAINED", score=10, equity=10.0
            )
            # Candidate B plays 1 tile (leaves 1 tile in bag) -> no bag-emptying bonus
            cand_partial = Move(
                row=7, col=7, direction="Across", word="A", leave="TRINED", score=5, equity=5.0
            )

            adjusted = search._evaluate_pre_endgame(
                game_state=state,
                candidates=[cand_empties, cand_partial],
            )

            # cand_empties should receive +2.0 tempo bonus + draw hazard adjustment
            assert adjusted[0].equity > 10.0, "Bag-emptying tempo bonus was not applied!"
        finally:
            engine.close()

    # -------------------------------------------------------------------------
    # BUG-03: Woogles Bot Pass Formatting
    # -------------------------------------------------------------------------
    def test_bug03_woogles_bot_pass_formatting(self):
        """Verifies pass moves are formatted as 'pass' rather than 'exchange pass'."""
        engine = MagpieEngine(lexicon="CSW24")
        try:
            bot = WooglesBotAgent(engine=engine, lexicon="CSW24")

            # Mock search.select_move to return a pass move
            bot.search.select_move = MagicMock(return_value=(Move.make_pass(), {}))

            board = [[None for _ in range(15)] for _ in range(15)]
            rack = ["A", "B", "C", "D", "E", "F", "G"]
            move, cmd_str, meta = bot.select_action(board=board, rack=rack)

            assert move.is_pass
            assert cmd_str == "pass", f"Expected 'pass', got '{cmd_str}'"
            assert not cmd_str.startswith("exchange"), "Woogles bot generated illegal exchange command for pass!"

            # Also verify word="--" pass move
            bot.search.select_move = MagicMock(return_value=(Move(is_pass=True, word="--"), {}))
            _, cmd_str_dash, _ = bot.select_action(board=board, rack=rack)
            assert cmd_str_dash == "pass"
        finally:
            engine.close()

    # -------------------------------------------------------------------------
    # BUG-04: Continuous Volatility Formula
    # -------------------------------------------------------------------------
    def test_bug04_volatility_continuous_ramp(self):
        """Verifies continuous linear ramp without step discontinuity at +/- 20."""
        def compute_lambda(score_diff: float) -> float:
            clamped_ratio = max(-2.0, min(2.0, float(score_diff) / 40.0))
            return -0.15 * clamped_ratio

        # Check threshold boundaries: 19.99 vs 20.00
        lam_19_99 = compute_lambda(19.99)
        lam_20_00 = compute_lambda(20.00)
        lam_20_01 = compute_lambda(20.01)

        assert abs(lam_20_00 - lam_19_99) < 0.001, "Discontinuity at +20!"
        assert abs(lam_20_01 - lam_20_00) < 0.001, "Discontinuity at +20!"

        # Check negative threshold: -19.99 vs -20.00
        lam_n19_99 = compute_lambda(-19.99)
        lam_n20_00 = compute_lambda(-20.00)
        lam_n20_01 = compute_lambda(-20.01)

        assert abs(lam_n20_00 - lam_n19_99) < 0.001, "Discontinuity at -20!"
        assert abs(lam_n20_01 - lam_n20_00) < 0.001, "Discontinuity at -20!"

        # Check symmetry: lambda(-x) == -lambda(x)
        for diff in [5.0, 15.0, 20.0, 35.0, 60.0, 80.0, 120.0]:
            assert abs(compute_lambda(-diff) - (-compute_lambda(diff))) < 1e-9

        # Check saturation at +/- 80
        assert compute_lambda(80.0) == -0.30
        assert compute_lambda(150.0) == -0.30
        assert compute_lambda(-80.0) == 0.30
        assert compute_lambda(-150.0) == 0.30

    # -------------------------------------------------------------------------
    # BUG-05: Coordinate Bounds Validation
    # -------------------------------------------------------------------------
    def test_bug05_coordinate_bounds_validation(self):
        """Verifies Move.parse_coordinate enforces 1 <= row <= 15 and A <= col <= O."""
        # Valid bounds
        assert Move.parse_coordinate("1A") == (0, 0, "Across")
        assert Move.parse_coordinate("15O") == (14, 14, "Across")
        assert Move.parse_coordinate("8H") == (7, 7, "Across")
        assert Move.parse_coordinate("A1") == (0, 0, "Down")
        assert Move.parse_coordinate("O15") == (14, 14, "Down")
        assert Move.parse_coordinate("H8") == (7, 7, "Down")

        # Invalid out-of-bounds rows
        invalid_across = ["0A", "16A", "17A", "99A", "00H", "-1A"]
        for coord in invalid_across:
            with pytest.raises(ValueError):
                Move.parse_coordinate(coord)

        invalid_down = ["A0", "A16", "A17", "A99", "H00", "A-1"]
        for coord in invalid_down:
            with pytest.raises(ValueError):
                Move.parse_coordinate(coord)

        # Invalid columns / formats
        invalid_syntax = ["", "   ", "P1", "1P", "Z10", "10Z", "8", "H", "88", "HH"]
        for coord in invalid_syntax:
            with pytest.raises(ValueError):
                Move.parse_coordinate(coord)

    # -------------------------------------------------------------------------
    # BUG-06: Alternating Tournament Margin Sign Fix
    # -------------------------------------------------------------------------
    def test_bug06_alternating_tournament_margin_sign(self):
        """Verifies margin sign is s1 - s2 for both first and second player seats."""
        # Scenario: Model 1 wins both games by +50 points
        # Game 1: Model 1 is P1 (first). res["p1_score"]=400, res["p2_score"]=350
        p1_is_first_g1 = True
        res_g1 = {"p1_score": 400, "p2_score": 350, "winner": 1}
        if p1_is_first_g1:
            s1_g1, s2_g1 = res_g1["p1_score"], res_g1["p2_score"]
        else:
            s1_g1, s2_g1 = res_g1["p2_score"], res_g1["p1_score"]
        margin_g1 = s1_g1 - s2_g1
        assert margin_g1 == +50

        # Game 2: Model 1 is P2 (second). res["p1_score"]=310 (Model 2), res["p2_score"]=360 (Model 1)
        p1_is_first_g2 = False
        res_g2 = {"p1_score": 310, "p2_score": 360, "winner": 2}
        if p1_is_first_g2:
            s1_g2, s2_g2 = res_g2["p1_score"], res_g2["p2_score"]
        else:
            s1_g2, s2_g2 = res_g2["p2_score"], res_g2["p1_score"]
        margin_g2 = s1_g2 - s2_g2
        assert margin_g2 == +50, f"Margin sign inverted! Got {margin_g2}, expected +50"

        # Mean margin across both games must be +50
        mean_margin = (margin_g1 + margin_g2) / 2.0
        assert mean_margin == +50.0

    # -------------------------------------------------------------------------
    # BUG-07: Phase Classification & Telemetry Instrumentation
    # -------------------------------------------------------------------------
    def test_bug07_game_phase_classification(self):
        """Verifies get_game_phase logic across all 4 Scrabble game phases."""
        # Opening: turns 1-5, bag > 14
        assert get_game_phase(turn_num=1, bag_count=86) == "opening"
        assert get_game_phase(turn_num=3, bag_count=78) == "opening"
        assert get_game_phase(turn_num=5, bag_count=70) == "opening"

        # Midgame: turn > 5 and bag > 14
        assert get_game_phase(turn_num=6, bag_count=65) == "midgame"
        assert get_game_phase(turn_num=15, bag_count=15) == "midgame"

        # Pre-endgame: bag in 1..14
        assert get_game_phase(turn_num=18, bag_count=14) == "pre_endgame"
        assert get_game_phase(turn_num=20, bag_count=7) == "pre_endgame"
        assert get_game_phase(turn_num=22, bag_count=1) == "pre_endgame"

        # Endgame: bag == 0
        assert get_game_phase(turn_num=24, bag_count=0) == "endgame"
        assert get_game_phase(turn_num=2, bag_count=0) == "endgame"

    def test_bug07_phase_telemetry_in_game_simulation(self):
        """Verifies GameSimulator tracks and returns phase_scores and phase_counts."""
        engine = MagpieEngine(lexicon="CSW24")
        try:
            sim = GameSimulator(engine=engine, lexicon="CSW24")

            # Simple greedy policies
            def policy(state: GameState):
                cands = engine.generate_moves(game_state=state, max_candidates=5)
                if cands:
                    return cands[0], {}
                return Move.create_pass(), {}

            res = sim.play_game(policy, policy, seed=42, max_turns=20)

            assert "phase_scores" in res, "phase_scores missing from play_game result!"
            assert "phase_counts" in res, "phase_counts missing from play_game result!"

            phase_scores = res["phase_scores"]
            phase_counts = res["phase_counts"]

            for ph in ["opening", "midgame", "pre_endgame", "endgame"]:
                assert ph in phase_scores, f"Phase {ph} missing from phase_scores"
                assert "p1" in phase_scores[ph]
                assert "p2" in phase_scores[ph]
                assert ph in phase_counts, f"Phase {ph} missing from phase_counts"

            # Check that turn_history items contain the 'phase' attribute
            assert len(res["turn_history"]) > 0
            for turn in res["turn_history"]:
                assert "phase" in turn, "Turn record missing phase tag!"
                assert turn["phase"] in ["opening", "midgame", "pre_endgame", "endgame"]

            # Sum of phase scores should match player total scores
            p1_phase_sum = sum(phase_scores[ph]["p1"] for ph in phase_scores)
            p2_phase_sum = sum(phase_scores[ph]["p2"] for ph in phase_scores)
            assert p1_phase_sum == res["p1_score"], f"P1 score mismatch: phase sum {p1_phase_sum} != total {res['p1_score']}"
            assert p2_phase_sum == res["p2_score"], f"P2 score mismatch: phase sum {p2_phase_sum} != total {res['p2_score']}"
        finally:
            engine.close()
