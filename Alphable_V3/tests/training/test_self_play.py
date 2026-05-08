import pytest
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
