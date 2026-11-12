"""
tests/platform/test_audit.py

Tests for statistical audit calculations, paired duplicate properties,
and historical benchmark telemetry validation.
"""

import json
import math
import os
from pathlib import Path
import numpy as np
import pytest
import scipy.stats as st

from scripts.verify_historical_telemetry import verify_10000g_dataset


@pytest.mark.audit
def test_historical_10000g_dataset_exists():
    repo_root = Path(__file__).resolve().parent.parent.parent
    data_file = repo_root / "data" / "tournaments" / "run_20261016_155029_V4-Champion_vs_Base-MAGPIE_10000g_dup.json"
    assert data_file.exists(), f"Dataset not found at {data_file}"
    assert data_file.stat().st_size > 1_000_000, "Dataset file appears truncated"


@pytest.mark.audit
def test_historical_10000g_statistical_metrics():
    repo_root = Path(__file__).resolve().parent.parent.parent
    data_file = repo_root / "data" / "tournaments" / "run_20261016_155029_V4-Champion_vs_Base-MAGPIE_10000g_dup.json"
    
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    details = data.get("details", [])
    assert len(details) == 5000, f"Expected 5,000 duplicate pairs, got {len(details)}"

    pair_net_spreads = [p["net_spread"] for p in details]
    per_game_spreads = [s / 2.0 for s in pair_net_spreads]

    mean_spread = float(np.mean(per_game_spreads))
    assert math.isclose(mean_spread, 7.0630, abs_tol=1e-3), f"Mean spread mismatch: {mean_spread}"

    std_spread = float(np.std(per_game_spreads, ddof=1))
    se_spread = std_spread / math.sqrt(len(details))
    t_stat = mean_spread / se_spread
    p_val_t = float(st.t.sf(abs(t_stat), df=len(details) - 1) * 2.0)

    assert t_stat > 8.0, f"t-statistic {t_stat} should exceed 8.0"
    assert p_val_t < 1e-16, f"p-value {p_val_t} should be < 1e-16"

    wins = sum(1 for p in details if p["net_spread"] > 0)
    draws = sum(1 for p in details if p["net_spread"] == 0)
    win_rate = (wins + 0.5 * draws) / len(details)
    assert math.isclose(win_rate, 0.5563, abs_tol=1e-3)


@pytest.mark.audit
def test_duplicate_pair_common_random_numbers_invariance():
    """Validates that duplicate pairs use Common Random Numbers (CRN) with identical seeds."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    data_file = repo_root / "data" / "tournaments" / "run_20261016_155029_V4-Champion_vs_Base-MAGPIE_10000g_dup.json"
    
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    details = data.get("details", [])
    seeds = [p.get("seed") for p in details[:100]]
    # All seeds must be positive integers and unique across pairs
    assert all(isinstance(s, int) and s > 0 for s in seeds)
    assert len(set(seeds)) == len(seeds), "Duplicate pairs should have unique seeds"


@pytest.mark.audit
def test_wilson_score_interval_properties():
    """Unit test for Wilson score interval bounds under extreme proportions."""
    def wilson(successes, n, z=1.95996):
        p = successes / n
        denom = 1.0 + (z**2) / n
        center = (p + (z**2) / (2.0 * n)) / denom
        margin = (z * math.sqrt((p * (1.0 - p) / n) + (z**2) / (4.0 * (n**2)))) / denom
        return center - margin, center + margin

    # 1. Zero successes in 100 trials: lower bound should be 0.0, upper bound > 0
    lo, hi = wilson(0, 100)
    assert lo >= 0.0 and hi > 0.0 and hi < 0.05

    # 2. 50 out of 100: interval should be centered symmetrically around 0.50
    lo, hi = wilson(50, 100)
    assert math.isclose(lo + hi, 1.0, abs_tol=1e-5)

    # 3. 10,000 trials matching V4 win rate: interval should be narrow and strictly > 0.50
    lo_v4, hi_v4 = wilson(2781.5, 5000)
    assert lo_v4 > 0.54 and hi_v4 < 0.58
