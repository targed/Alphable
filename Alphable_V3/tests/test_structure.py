import pytest
import os
import tempfile
from unittest.mock import patch
from alphable.core.structure import Gaddag

def test_gaddag_load_file_not_found(capsys):
    """Test that Gaddag.load handles FileNotFoundError correctly."""
    # Cython module won't trigger python mock of builtins.open, but if we just give it a
    # file that literally doesn't exist, it will throw FileNotFoundError naturally.
    non_existent_file = "definitely_non_existent_dict_xyz123.txt"
    with pytest.raises(FileNotFoundError):
        Gaddag.load(non_existent_file)

    captured = capsys.readouterr()
    assert f"ERROR: Could not find dictionary file at {non_existent_file}" in captured.out

def test_gaddag_load_happy_path(capsys):
    """Test that Gaddag.load correctly parses a valid dictionary file."""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
        temp_file.write("APPLE A type of fruit\nBANANA Another fruit\n")
        temp_file_path = temp_file.name

    try:
        g = Gaddag.load(temp_file_path)

        captured = capsys.readouterr()
        assert "Dictionary loaded." in captured.out

        # Verify Gaddag state
        assert len(g.root.keys()) > 0
    finally:
        os.remove(temp_file_path)

def test_gaddag_load_ignores_invalid_words():
    """Test that Gaddag.load ignores single-letter words, empty lines, and non-alpha words."""
    mock_file_content = (
        "\n"              # Empty line
        "A\n"             # Single character
        "WORD123\n"       # Non-alpha
        "GOODWORD def\n"  # Valid word
        "  \n"            # Whitespace line
    )
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
        temp_file.write(mock_file_content)
        temp_file_path = temp_file.name

    try:
        with patch.object(Gaddag, 'add_word') as mock_add_word:
            Gaddag.load(temp_file_path)

        # Only GOODWORD should be added
        mock_add_word.assert_called_once_with("GOODWORD")
    finally:
        os.remove(temp_file_path)

def test_gaddag_load_strips_bom():
    """Test that Gaddag.load correctly strips Byte Order Marks (BOM)."""
    # \ufeff is the BOM
    mock_file_content = "\ufeffBOMWORD definition"
    with tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', delete=False) as temp_file:
        temp_file.write(mock_file_content)
        temp_file_path = temp_file.name

    try:
        with patch.object(Gaddag, 'add_word') as mock_add_word:
            Gaddag.load(temp_file_path)

        mock_add_word.assert_called_once_with("BOMWORD")
    finally:
        os.remove(temp_file_path)
