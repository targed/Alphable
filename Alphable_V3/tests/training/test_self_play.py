import pytest
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
