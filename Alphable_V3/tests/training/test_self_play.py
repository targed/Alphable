import random
from collections import Counter
import pytest

from alphable.training.self_play import build_bag, STANDARD_TILE_COUNTS

def test_build_bag_length():
    """Test that the bag contains exactly 100 tiles."""
    bag = build_bag()
    assert len(bag) == 100, f"Expected 100 tiles, got {len(bag)}"

def test_build_bag_tile_counts():
    """Test that the bag contains the correct frequencies of each tile."""
    bag = build_bag()
    counts = Counter(bag)

    # Assert each tile in the standard distribution matches the counts in the bag
    for tile, expected_count in STANDARD_TILE_COUNTS.items():
        assert counts[tile] == expected_count, f"Expected {expected_count} for tile '{tile}', got {counts[tile]}"

    # Ensure no extra unexpected tiles were added
    assert len(counts) == len(STANDARD_TILE_COUNTS), "Bag contains unexpected tile types"

def test_build_bag_deterministic():
    """Test that the bag is generated deterministically when seeded."""
    rng1 = random.Random(42)
    bag1 = build_bag(rng=rng1)

    rng2 = random.Random(42)
    bag2 = build_bag(rng=rng2)

    assert bag1 == bag2, "Bags generated with the same seed should be identical"

    # Verify exact first 10 items for the seed 42 to detect any future behavioral changes
    expected_start = ['I', 'I', 'V', 'B', 'O', 'L', 'A', 'R', 'D', 'S']
    assert bag1[:10] == expected_start, f"Expected start {expected_start}, got {bag1[:10]}"

def test_build_bag_default_rng():
    """Test that calling build_bag without an rng argument works and uses random."""
    # Since random without seed is non-deterministic, we just ensure it builds correctly
    bag1 = build_bag()
    bag2 = build_bag()

    assert len(bag1) == 100
    assert len(bag2) == 100
    # While highly unlikely to be identical, it's not strictly impossible, but they shouldn't be the same list object
    assert bag1 is not bag2
    assert Counter(bag1) == STANDARD_TILE_COUNTS
    assert Counter(bag2) == STANDARD_TILE_COUNTS
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
from alphable.training.self_play import draw_tiles

def test_draw_tiles_normal():
    """Test drawing fewer items than available."""
    bag = ['A', 'B', 'C', 'D', 'E']
    drawn = draw_tiles(bag, 3)
    # pop() takes from the end of the list
    assert drawn == ['E', 'D', 'C']
    assert bag == ['A', 'B']

def test_draw_tiles_exact():
    """Test drawing exactly the number of items available."""
    bag = ['A', 'B', 'C']
    drawn = draw_tiles(bag, 3)
    assert drawn == ['C', 'B', 'A']
    assert bag == []

def test_draw_tiles_more_than_available():
    """Test drawing more items than are available in the bag."""
    bag = ['A', 'B']
    drawn = draw_tiles(bag, 5)
    assert drawn == ['B', 'A']
    assert bag == []

def test_draw_tiles_zero():
    """Test drawing 0 items."""
    bag = ['A', 'B', 'C']
    drawn = draw_tiles(bag, 0)
    assert drawn == []
    assert bag == ['A', 'B', 'C']

def test_draw_tiles_negative():
    """Test drawing a negative number of items."""
    bag = ['A', 'B', 'C']
    drawn = draw_tiles(bag, -2)
    assert drawn == []
    assert bag == ['A', 'B', 'C']

def test_draw_tiles_empty_bag():
    """Test drawing from an empty bag."""
    bag = []
    drawn = draw_tiles(bag, 5)
    assert drawn == []
    assert bag == []
from alphable.training.self_play import rack_penalty

def test_rack_penalty_empty_rack():
    """Test that an empty rack results in 0 penalty."""
    assert rack_penalty([]) == 0

def test_rack_penalty_standard_letters():
    """Test standard uppercase letters."""
    # A=1, B=3, C=3 => 1 + 3 + 3 = 7
    assert rack_penalty(['A', 'B', 'C']) == 7
    # Z=10, Q=10 => 20
    assert rack_penalty(['Z', 'Q']) == 20

def test_rack_penalty_blank_tile():
    """Test that a blank tile ('?') results in 0 penalty."""
    # A=1, ?=0 => 1
    assert rack_penalty(['A', '?']) == 1

def test_rack_penalty_all_blanks():
    """Test a rack full of blank tiles."""
    assert rack_penalty(['?', '?']) == 0

def test_rack_penalty_lowercase_letters():
    """Test that lowercase letters are correctly converted and penalized."""
    # The current code uses `.upper()` to fetch values from LETTER_VALUES.
    # a=1, b=3 => 4
    assert rack_penalty(['a', 'b']) == 4

def test_rack_penalty_invalid_characters():
    """Test that invalid/unknown characters result in 0 penalty."""
    # A=1, !=0, -=0 => 1
    assert rack_penalty(['A', '!', '-']) == 1

def test_rack_penalty_mixed_case_and_symbols():
    """Test a mix of uppercase, lowercase, blanks, and symbols."""
    # Z=10, q=10, ?=0, *=0, x=8 => 28
    assert rack_penalty(['Z', 'q', '?', '*', 'x']) == 28
