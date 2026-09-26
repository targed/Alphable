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


def test_lipkin_smith_bingo_stem_equities():
    # RETIN stem should have strong positive synergy (+10.0 to +16.0)
    retin_equity = compute_leave_equity("RETIN")
    assert retin_equity >= 10.0, f"Expected RETIN equity >= 10.0, got {retin_equity}"

    # E, R, T individual baselines should be positive
    e_val = compute_leave_equity("E")
    r_val = compute_leave_equity("R")
    t_val = compute_leave_equity("T")
    assert e_val >= 1.5, f"Expected E equity >= 1.5, got {e_val}"
    assert r_val >= 1.5, f"Expected R equity >= 1.5, got {r_val}"
    assert t_val >= 1.5, f"Expected T equity >= 1.5, got {t_val}"


def test_multi_tile_stem_synergies():
    # 3-letter stems like RET or SAT should have bonus beyond raw sum
    ret_equity = compute_leave_equity("RET")
    assert ret_equity >= 7.0, f"Expected RET equity >= 7.0, got {ret_equity}"


def test_endgame_zero_bag_deduction():
    # When bag is 0, leave equity is pure face value deduction: Q (10) + Z (10) = -20 pts
    qz_endgame = compute_leave_equity("QZ", bag_remaining=0)
    assert qz_endgame == -20.0, f"Expected QZ endgame penalty -20.0, got {qz_endgame}"


def test_duplicate_blank_diminishing_returns():
    # Single blank is worth +26.5; second blank should have diminishing returns (+6.0 pts)
    single_blank = compute_leave_equity(["?"])
    double_blank = compute_leave_equity(["?", "?"])
    assert single_blank == pytest.approx(26.5)
    assert double_blank == pytest.approx(32.5)
    assert double_blank > single_blank
    # Difference should be ~6.0 pts, preventing equity hoarding over 60+ pt bingos
    assert (double_blank - single_blank) == pytest.approx(6.0, abs=0.5)


