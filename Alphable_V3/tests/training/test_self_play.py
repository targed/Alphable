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
