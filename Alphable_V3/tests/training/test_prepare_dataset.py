import pytest

from alphable.training.prepare_dataset import parse_position

def test_parse_position_down():
    # Test valid 'Down' positions
    assert parse_position("F6") == (5, 5, "Down")
    assert parse_position("A1") == (0, 0, "Down")
    assert parse_position("O15") == (14, 14, "Down")

def test_parse_position_across():
    # Test valid 'Across' positions
    assert parse_position("8E") == (7, 4, "Across")
    assert parse_position("1A") == (0, 0, "Across")
    assert parse_position("15O") == (14, 14, "Across")

def test_parse_position_case_insensitivity():
    # Test lowercase inputs
    assert parse_position("f6") == (5, 5, "Down")
    assert parse_position("a1") == (0, 0, "Down")
    assert parse_position("o15") == (14, 14, "Down")
    assert parse_position("8e") == (7, 4, "Across")
    assert parse_position("1a") == (0, 0, "Across")
    assert parse_position("15o") == (14, 14, "Across")

def test_parse_position_empty():
    # Test None and empty string
    assert parse_position(None) == (None, None, None)
    assert parse_position("") == (None, None, None)

def test_parse_position_invalid():
    # Test invalid inputs
    assert parse_position("INVALID") == (None, None, None)
    assert parse_position("123") == (None, None, None)
    assert parse_position("ABC") == (None, None, None)
    assert parse_position("12") == (None, None, None)
    assert parse_position("A") == (None, None, None)
    # Testing other invalid inputs that might fail regex
    assert parse_position("88") == (None, None, None)
    assert parse_position("EE") == (None, None, None)
    assert parse_position("1E2") == (None, None, None)
    assert parse_position("E2E") == (None, None, None)
