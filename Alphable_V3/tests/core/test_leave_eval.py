import pytest
from alphable.core.leave_eval import compute_leave_equity, BASE_TILE_EQUITY, DUPLICATE_PENALTIES


def test_empty_leave():
    assert compute_leave_equity([]) == 0.0
    assert compute_leave_equity("") == 0.0


def test_blank_valuation():
    # Blank should have massive positive equity (+26.5 pts)
    blank_eq = compute_leave_equity(["?"])
    assert blank_eq >= 25.0
    assert blank_eq == pytest.approx(26.5)


def test_s_tile_valuation():
    # S should have high equity (+8.2 pts)
    s_eq = compute_leave_equity(["S"])
    assert s_eq == pytest.approx(8.2)


def test_blank_plus_s_synergy():
    # ? + S has synergy bonus
    qs_eq = compute_leave_equity(["?", "S"])
    # 26.5 + 8.2 + 5.0 synergy = 39.7
    assert qs_eq >= 38.0


def test_qu_synergy():
    # Q alone is heavily penalized (-7.5)
    q_eq = compute_leave_equity(["Q"])
    assert q_eq <= -7.0

    # Q with U neutralizes much of the penalty with +6.5 bonus
    qu_eq = compute_leave_equity(["Q", "U"])
    # -7.5 (Q) - 4.0 (U) + 6.5 (QU) = -5.0
    assert qu_eq > q_eq


def test_duplicate_penalties():
    # Single U vs Double U vs Triple U
    single_u = compute_leave_equity(["U", "S", "T"])
    double_u = compute_leave_equity(["U", "U", "S", "T"])
    triple_u = compute_leave_equity(["U", "U", "U", "S", "T"])

    assert double_u < single_u
    assert triple_u < double_u


def test_duplicate_s_penalty():
    # Second S has severe diminishing returns (marginal value ~+2.0 pts instead of +8.2)
    single_s = compute_leave_equity(["A", "S"])
    double_s = compute_leave_equity(["A", "S", "S"])
    # Second S should only add ~2 points, not +8.2
    assert double_s > single_s
    assert (double_s - single_s) == pytest.approx(2.0, abs=0.5)


def test_vowel_consonant_imbalance():
    # All consonants penalty (e.g. BCDFR)
    all_cons = compute_leave_equity(["B", "C", "D", "F", "R"])
    # Balanced (e.g. ADEFR)
    balanced = compute_leave_equity(["A", "D", "E", "F", "R"])
    assert all_cons < balanced

    # All vowels penalty (e.g. AEIOU)
    all_vow = compute_leave_equity(["A", "E", "I", "O", "U"])
    assert all_vow < balanced
