import pytest
from alphable.core.search import sample_opponent_rack

def test_sample_opponent_rack_normal():
    # Test when len(unseen_tiles) > sample_size
    unseen_tiles = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    sample_size = 7
    result = sample_opponent_rack(unseen_tiles, sample_size)
    assert len(result) == sample_size
    assert all(tile in unseen_tiles for tile in result)
    # Ensure it's not the same object
    assert result is not unseen_tiles

def test_sample_opponent_rack_exact_boundary():
    # Test when len(unseen_tiles) == sample_size
    unseen_tiles = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    sample_size = 7
    result = sample_opponent_rack(unseen_tiles, sample_size)
    assert len(result) == sample_size
    assert result == unseen_tiles

def test_sample_opponent_rack_underflow():
    # Test when len(unseen_tiles) < sample_size
    unseen_tiles = ['A', 'B', 'C']
    sample_size = 7
    result = sample_opponent_rack(unseen_tiles, sample_size)
    assert len(result) == len(unseen_tiles)
    assert result == unseen_tiles

def test_sample_opponent_rack_empty():
    # Test when unseen_tiles is empty
    unseen_tiles = []
    sample_size = 7
    result = sample_opponent_rack(unseen_tiles, sample_size)
    assert len(result) == 0
    assert result == []

def test_sample_opponent_rack_original_not_mutated():
    unseen_tiles = ['A', 'B', 'C']
    original_copy = unseen_tiles.copy()
    sample_opponent_rack(unseen_tiles, 7)
    assert unseen_tiles == original_copy
import random
import unittest.mock as mock
from alphable.core.search import sample_opponent_rack

def test_sample_opponent_rack_larger_than_sample_size():
    """Test with unseen_tiles larger than sample_size."""
    unseen_tiles = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    sample_size = 7
    result = sample_opponent_rack(unseen_tiles, sample_size)

    assert len(result) == sample_size
    assert all(tile in unseen_tiles for tile in result)
    # Check that it's a subset (considering counts if necessary)
    for tile in set(result):
        assert result.count(tile) <= unseen_tiles.count(tile)

def test_sample_opponent_rack_empty_list():
    """Test with empty unseen_tiles."""
    unseen_tiles = []
    result = sample_opponent_rack(unseen_tiles, sample_size=7)
    assert result == []

def test_sample_opponent_rack_smaller_than_sample_size():
    """Test with unseen_tiles smaller than sample_size."""
    unseen_tiles = ['A', 'B', 'C']
    sample_size = 7
    result = sample_opponent_rack(unseen_tiles, sample_size)

    assert len(result) == 3
    assert sorted(result) == sorted(unseen_tiles)
    assert result is not unseen_tiles # Should be a copy

def test_sample_opponent_rack_exact_size():
    """Test with unseen_tiles exactly the same size as sample_size."""
    unseen_tiles = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    sample_size = 7
    result = sample_opponent_rack(unseen_tiles, sample_size)

    assert len(result) == 7
    assert sorted(result) == sorted(unseen_tiles)
    assert result is not unseen_tiles # Should be a copy

def test_sample_opponent_rack_randomness():
    """Verify that random.sample is called when unseen_tiles > sample_size."""
    unseen_tiles = ['A', 'B', 'C']
    sample_size = 2

    with mock.patch('random.sample', return_value=['A', 'B']) as mock_sample:
        result = sample_opponent_rack(unseen_tiles, sample_size)

        mock_sample.assert_called_once_with(unseen_tiles, sample_size)
        assert result == ['A', 'B']
