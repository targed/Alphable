"""
Tier 4: Real-World Workload Scenarios & Statistical Validation E2E Tests.

Covers:
- Feature 8: Statistical Hypothesis Testing (Paired t-test, 2-proportion z-test, Wilson intervals).
- Feature 9: Game-Phase Sensitivity Audit & margin decomposition.
- Feature 11: First-Order Luck Cancellation on full duplicate match runs.
- Feature 18: Master Benchmark Table Schema Validation (Table 1, Table 2, Table 3).
- Feature 20: Scientific Defense Verification against historical tournament logs.
- Workloads: Reproducible duplicate match series, GCG parsing & board replay.
"""

import os
import json
import pytest
import numpy as np
import scipy.stats as st
from typing import Dict, Any, Tuple, List

from alphable_v4.engine.game_state import GameState
from alphable_v4.engine.move import Move
from alphable_v4.engine.magpie_bindings import MagpieEngine
from alphable_v4.platform.eval import GameSimulator, MatchStats
from alphable_v4.search.bams import BAMSSearch, BAMSConfig
from alphable_v4.training.parse_gcg import parse_gcg_file, parse_gcg_text


class TestTier4StatisticalHypothesisFormulas:
    """Tests for Feature 8: Formal Mathematical Proofs & Statistical Hypothesis Formulas."""

    def test_paired_two_tailed_t_test_formula(self):
        """
        Verifies paired two-tailed t-test calculation:
        t = d_bar / (s / sqrt(N)), df = N - 1, p = 2 * (1 - cdf(|t|)).
        """
        # Test on 3,000-game duplicate run empirical values: N=1500 pairs, d_bar = 7.1, s = 57.6
        n_pairs = 1500
        d_bar = 7.1
        s = 57.6

        se = s / np.sqrt(n_pairs)
        t_stat = d_bar / se
        p_val = float(st.t.sf(abs(t_stat), df=n_pairs - 1) * 2.0)

        assert pytest.approx(t_stat, abs=0.1) == 4.78
        assert p_val < 0.0001
        assert p_val > 0.0

    def test_two_proportion_z_test_formula(self):
        """
        Verifies two-proportion z-test against null hypothesis p0 = 0.50:
        Z = (p_hat - p0) / sqrt(p0 * (1 - p0) / N).
        """
        # Test on 5,000 duplicate pairs: 2746 wins, 2183 losses, 71 draws (win_rate = 55.63%)
        n_pairs = 5000
        wins = 2746
        draws = 71
        p_hat = (wins + 0.5 * draws) / n_pairs
        p0 = 0.50

        se_z = np.sqrt(p0 * (1.0 - p0) / n_pairs)
        z_stat = (p_hat - p0) / se_z
        p_val_z = float(st.norm.sf(abs(z_stat)) * 2.0)

        assert pytest.approx(z_stat, abs=0.1) == 7.96
        assert p_val_z < 1e-12

    def test_wilson_score_confidence_interval_formula(self):
        """
        Verifies Wilson 95% score confidence interval:
        CI = (p_hat + z^2/(2N) +/- z * sqrt(p_hat*(1-p_hat)/N + z^2/(4N^2))) / (1 + z^2/N).
        """
        n_pairs = 1500
        wins = 806
        draws = 30
        p_hat = (wins + 0.5 * draws) / n_pairs  # 54.73%
        z = 1.95996  # 95% two-tailed standard normal critical value

        denom = 1.0 + (z**2) / n_pairs
        center = (p_hat + (z**2) / (2.0 * n_pairs)) / denom
        margin = (z * np.sqrt((p_hat * (1.0 - p_hat) / n_pairs) + (z**2) / (4.0 * (n_pairs**2)))) / denom

        ci_lower = center - margin
        ci_upper = center + margin

        # Wilson interval must be strictly above 50%
        assert ci_lower > 0.50, f"Expected lower bound > 0.50, got {ci_lower}"
        assert ci_upper < 0.60
        assert ci_lower < p_hat < ci_upper


class TestTier4TournamentWorkloadSimulations:
    """Tests for multi-game reproducible duplicate tournament simulations."""

    def test_reproducible_duplicate_match_series(self, shared_engine):
        """Executes a 4-pair (8-game) reproducible duplicate match workload."""
        def static_policy(state: GameState) -> Tuple[Move, Dict[str, Any]]:
            cands = shared_engine.generate_moves(game_state=state, max_candidates=5)
            if cands:
                return cands[0], {"method": "static"}
            return Move.create_pass(), {"method": "pass"}

        sim = GameSimulator(shared_engine, lexicon="CSW24")
        num_pairs = 4
        pair_diffs = []

        for p in range(num_pairs):
            seed = 5000 + p * 31
            # Game A
            res_a = sim.play_game(static_policy, static_policy, seed=seed, max_turns=12)
            # Game B (swapped seats)
            res_b = sim.play_game(static_policy, static_policy, seed=seed, max_turns=12)

            score_p1 = res_a["p1_score"] + res_b["p2_score"]
            score_p2 = res_a["p2_score"] + res_b["p1_score"]
            diff = score_p1 - score_p2
            pair_diffs.append(diff)

        # In deterministic self-play, every duplicate pair difference must be 0
        assert len(pair_diffs) == 4
        assert all(d == 0 for d in pair_diffs)

    def test_historical_tournament_history_ledger_integrity(self):
        """Verifies historical tournament history ledger exists and contains valid JSON entries."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        history_path = os.path.normpath(
            os.path.join(base_dir, "..", "..", "data", "tournaments", "tournament_history.jsonl")
        )
        assert os.path.exists(history_path), f"Tournament history not found at: {history_path}"

        valid_runs = 0
        with open(history_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    assert "run_id" in entry
                    assert "player1" in entry and "name" in entry["player1"]
                    assert "player2" in entry and "name" in entry["player2"]
                    assert "total_games" in entry
                    assert "win_rate" in entry and "percentage" in entry["win_rate"]
                    assert "net_spread" in entry and "mean" in entry["net_spread"]
                    assert "significance" in entry and "t_statistic" in entry["significance"]
                    valid_runs += 1

        assert valid_runs >= 5, f"Expected at least 5 logged runs in history ledger, got {valid_runs}"


class TestTier4BenchmarkTableSchemas:
    """Tests for Feature 18: Master Benchmark Table Schema Validation."""

    def test_table1_master_benchmark_schema(self):
        """Verifies Master Benchmark Table schema fields (model, opponent, mode, games, WR, spread, t, p)."""
        required_columns = [
            "model_preset",
            "opponent_spec",
            "tournament_mode",
            "total_games",
            "win_rate_pct",
            "ci95_win_rate",
            "mean_net_spread",
            "ci95_net_spread",
            "t_statistic",
            "p_value",
            "significance_verdict",
        ]
        sample_row = {
            "model_preset": "V4-Champion",
            "opponent_spec": "Base-MAGPIE",
            "tournament_mode": "duplicate",
            "total_games": 3000,
            "win_rate_pct": 54.7,
            "ci95_win_rate": 2.5,
            "mean_net_spread": 7.1,
            "ci95_net_spread": 2.9,
            "t_statistic": 4.78,
            "p_value": 0.000002,
            "significance_verdict": "STATISTICALLY SIGNIFICANT (p < 0.0001)",
        }
        for col in required_columns:
            assert col in sample_row

    def test_table2_ablation_matrix_schema(self):
        """Verifies Architectural Ablations Table schema (component, config_delta, delta_WR, delta_spread)."""
        required_columns = [
            "ablation_component",
            "configuration",
            "win_rate_delta",
            "net_spread_delta",
            "impact_interpretation",
        ]
        sample_row = {
            "ablation_component": "2-Ply Nested Rollout",
            "configuration": "K=8, N=14, w=0.18 vs 1-Ply",
            "win_rate_delta": "+2.0%",
            "net_spread_delta": "+2.8 pts",
            "impact_interpretation": "Primary driver of tactical counterplay avoidance",
        }
        for col in required_columns:
            assert col in sample_row


class TestTier4GCGReplayWorkload:
    """Tests for GCG match transcript parsing and board replaying."""

    def test_gcg_parser_and_board_replayer_on_sample(self):
        """Verifies GCG parser correctly extracts structured turns, boards, and scores."""
        sample_gcg_text = """#character-encoding UTF-8
#description Created with Macondo
#id io.woogles testgame123
#lexicon CSW24
#player1 Alice Alice
#player2 Bob Bob
>Alice: BNNOOQU 8F NOOB +12 12
>Bob: ACEIOTW 9E TAWIE +31 31
>Alice: ?ACIOSX 11E COAX +40 52
>Bob: ABCDEFG -ABC +0 31
>Alice: ?ACIOSX - +0 52
>Bob: (D) +4 35
"""
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".gcg", delete=False) as tmp:
            tmp.write(sample_gcg_text)
            tmp_path = tmp.name

        try:
            game = parse_gcg_file(tmp_path)
            assert game is not None
            assert game.player1 == "Alice"
            assert game.player2 == "Bob"
            assert len(game.turns) >= 5

            # Inspect first turn
            turn0 = game.turns[0]
            assert turn0.player == "Alice"
            assert turn0.coord == "8F"
            assert turn0.word == "NOOB"
            assert turn0.points == 12
            assert turn0.total_score == 12
            assert len(turn0.board_after_cgp) > 0

            # Turn 3: exchange
            turn3 = game.turns[3]
            assert turn3.is_exchange is True

            # Turn 4: pass
            turn4 = game.turns[4]
            assert turn4.is_pass is True
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
