import random
from unittest import mock
from alphable.core.search import sample_opponent_rack

def test_sample_opponent_rack_deterministic():
    """Test with unseen_tiles larger than sample_size using a fixed random seed to ensure determinism and duplicate handling."""
    random.seed(42)
    unseen_tiles = ['A', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', '?']
    sample_size = 7
    result = sample_opponent_rack(unseen_tiles, sample_size)

    assert len(result) == sample_size

    # Asserting exactly the expected sampled tiles from seed 42 in python 3
    expected_result = ['J', 'A', 'A', 'D', 'C', '?', 'F']
    assert result == expected_result

    # Check that it's a valid subset, including handling duplicates correctly
    for tile in set(result):
        assert result.count(tile) <= unseen_tiles.count(tile)

def test_sample_opponent_rack_empty_list():
    """Test with empty unseen_tiles."""
    unseen_tiles = []
    result = sample_opponent_rack(unseen_tiles, sample_size=7)
    assert result == []
    assert result is not unseen_tiles

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

def test_sample_opponent_rack_original_not_mutated():
    """Test that the original list is not mutated."""
    unseen_tiles = ['A', 'B', 'C']
    original_copy = unseen_tiles.copy()
    sample_opponent_rack(unseen_tiles, 7)
    assert unseen_tiles == original_copy

    unseen_tiles = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    original_copy = unseen_tiles.copy()
    sample_opponent_rack(unseen_tiles, 7)
    assert unseen_tiles == original_copy

def test_sample_opponent_rack_randomness_mock():
    """Verify that random.sample is actually called when unseen_tiles > sample_size."""
    unseen_tiles = ['A', 'B', 'C', 'D']
    sample_size = 2

    with mock.patch('random.sample', return_value=['A', 'B']) as mock_sample:
        result = sample_opponent_rack(unseen_tiles, sample_size)

        mock_sample.assert_called_once_with(unseen_tiles, sample_size)
        assert result == ['A', 'B']

def test_candidate_eval_includes_points():
    """Verify that candidate sorting factors in move points."""
    # Two moves: move A has value 0.3, points 10; move B has value 0.1, points 70
    # move A blended: 0.3 + 10/50 = 0.50
    # move B blended: 0.1 + 70/50 = 1.50 -> move B should rank higher!
    evals = [
        {'move': 'A', 'value': 0.3, 'points': 10},
        {'move': 'B', 'value': 0.1, 'points': 70},
    ]
    evals.sort(key=lambda x: x['value'] + (x['points'] / 50.0), reverse=True)
    assert evals[0]['move'] == 'B'
