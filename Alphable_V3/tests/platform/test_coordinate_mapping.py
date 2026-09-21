import pytest
from alphable.platform.woogles.selectors import (
    to_woogles_coords,
    from_woogles_coords,
    format_move_description,
)


def test_to_woogles_coords_valid():
    assert to_woogles_coords(0, 0) == "A1"
    assert to_woogles_coords(7, 7) == "H8"
    assert to_woogles_coords(14, 14) == "O15"
    assert to_woogles_coords(0, 14) == "O1"
    assert to_woogles_coords(14, 0) == "A15"


def test_to_woogles_coords_invalid():
    with pytest.raises(ValueError):
        to_woogles_coords(-1, 0)
    with pytest.raises(ValueError):
        to_woogles_coords(0, 15)
    with pytest.raises(ValueError):
        to_woogles_coords(15, 7)


def test_from_woogles_coords_valid():
    assert from_woogles_coords("A1") == (0, 0)
    assert from_woogles_coords("H8") == (7, 7)
    assert from_woogles_coords("8h") == (7, 7)
    assert from_woogles_coords("O15") == (14, 14)
    assert from_woogles_coords("15o") == (14, 14)
    assert from_woogles_coords("  c10  ") == (9, 2)


def test_from_woogles_coords_invalid():
    with pytest.raises(ValueError):
        from_woogles_coords("P1")
    with pytest.raises(ValueError):
        from_woogles_coords("A0")
    with pytest.raises(ValueError):
        from_woogles_coords("A16")
    with pytest.raises(ValueError):
        from_woogles_coords("invalid")


def test_format_move_description():
    desc_across = format_move_description("BLASTER", 7, 7, "Across")
    assert desc_across == "H8 Across BLASTER"

    desc_down = format_move_description("QUIZ", 0, 0, "down")
    assert desc_down == "A1 Down QUIZ"
