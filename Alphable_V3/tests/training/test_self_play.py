import pytest
from alphable.training.self_play import compute_turn_temperature

def test_compute_turn_temperature_temp_end_none():
    assert compute_turn_temperature(0, 10, 1.5, None) == 1.5
    assert compute_turn_temperature(5, 10, 1.5, None) == 1.5

def test_compute_turn_temperature_max_turns_leq_one():
    assert compute_turn_temperature(0, 1, 1.5, 0.5) == 0.5
    assert compute_turn_temperature(0, 0, 1.5, 0.5) == 0.5
    assert compute_turn_temperature(0, -1, 1.5, 0.5) == 0.5

def test_compute_turn_temperature_interpolation():
    # turn_idx=0 -> alpha=0 -> temp_start
    assert compute_turn_temperature(0, 11, 1.0, 0.0) == 1.0
    # turn_idx=5 -> alpha=0.5 -> midpoint
    assert compute_turn_temperature(5, 11, 1.0, 0.0) == 0.5
    # turn_idx=10 -> alpha=1.0 -> temp_end
    assert compute_turn_temperature(10, 11, 1.0, 0.0) == 0.0

    # Another test case
    assert compute_turn_temperature(2, 5, 2.0, 1.0) == 1.5  # alpha = 2/4 = 0.5

def test_compute_turn_temperature_out_of_bounds():
    # alpha floored at 0
    assert compute_turn_temperature(-1, 11, 1.0, 0.0) == 1.0
    # alpha capped at 1
    assert compute_turn_temperature(11, 11, 1.0, 0.0) == 0.0
    assert compute_turn_temperature(100, 11, 1.0, 0.0) == 0.0
