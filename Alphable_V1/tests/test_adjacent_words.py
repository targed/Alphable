"""
Test adjacent word validation in the same direction.
This tests the critical bug where placing tiles adjacent to existing tiles
in the same direction creates invalid combined words.

Tests Requirements: 4.1, 4.2, 4.3 (extended to same-direction adjacency)
"""
import pyspiel
import scrabble

def test_adjacent_word_before():
    """Test that placing a word immediately before existing tiles validates the combined word"""
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Place "GUT" on the board at (7, 9)
    state.board[7][9] = 'G'
    state.board[7][10] = 'U'
    state.board[7][11] = 'T'
    
    # Try to place "NOOT" at (7, 5) which would create "NOOTGUT"
    # This should be INVALID because "NOOTGUT" is not a word
    adjacent_words = state.find_adjacent_words_same_direction(7, 5, "NOOT", "Across")
    
    print(f"Adjacent words found: {adjacent_words}")
    assert len(adjacent_words) > 0, "Should find adjacent word"
    assert adjacent_words[0][0] == "NOOTGUT", f"Should form NOOTGUT, got {adjacent_words[0][0]}"
    
    # Validate - should fail
    is_valid = state.validate_adjacent_words(adjacent_words)
    assert not is_valid, "NOOTGUT should be invalid"
    
    print("✓ Adjacent word before test passed")


def test_adjacent_word_after():
    """Test that placing a word immediately after existing tiles validates the combined word"""
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Place "BOXERS" on the board at (7, 5)
    for i, char in enumerate("BOXERS"):
        state.board[7][5 + i] = char
    
    # Try to place "JOES" at (7, 11) which would create "BOXERSJOES"
    # This should be INVALID because "BOXERSJOES" is not a word
    adjacent_words = state.find_adjacent_words_same_direction(7, 11, "JOES", "Across")
    
    print(f"Adjacent words found: {adjacent_words}")
    assert len(adjacent_words) > 0, "Should find adjacent word"
    assert adjacent_words[0][0] == "BOXERSJOES", f"Should form BOXERSJOES, got {adjacent_words[0][0]}"
    
    # Validate - should fail
    is_valid = state.validate_adjacent_words(adjacent_words)
    assert not is_valid, "BOXERSJOES should be invalid"
    
    print("✓ Adjacent word after test passed")


def test_adjacent_word_both_sides():
    """Test placing a word between two existing words"""
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Place "BOX" at (7, 5) and "JOES" at (7, 11)
    for i, char in enumerate("BOX"):
        state.board[7][5 + i] = char
    for i, char in enumerate("JOES"):
        state.board[7][11 + i] = char
    
    # Try to place "ERS" at (7, 8) which would create "BOXERSJOES"
    adjacent_words = state.find_adjacent_words_same_direction(7, 8, "ERS", "Across")
    
    print(f"Adjacent words found: {adjacent_words}")
    assert len(adjacent_words) > 0, "Should find adjacent word"
    assert adjacent_words[0][0] == "BOXERSJOES", f"Should form BOXERSJOES, got {adjacent_words[0][0]}"
    
    # Validate - should fail
    is_valid = state.validate_adjacent_words(adjacent_words)
    assert not is_valid, "BOXERSJOES should be invalid"
    
    print("✓ Adjacent word both sides test passed")


def test_valid_adjacent_word():
    """Test that valid adjacent words are accepted"""
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Place "BOX" on the board at (7, 5)
    for i, char in enumerate("BOX"):
        state.board[7][5 + i] = char
    
    # Try to place "ES" at (7, 8) which would create "BOXES"
    # This should be VALID because "BOXES" is a word
    adjacent_words = state.find_adjacent_words_same_direction(7, 8, "ES", "Across")
    
    print(f"Adjacent words found: {adjacent_words}")
    assert len(adjacent_words) > 0, "Should find adjacent word"
    assert adjacent_words[0][0] == "BOXES", f"Should form BOXES, got {adjacent_words[0][0]}"
    
    # Validate - should succeed
    is_valid = state.validate_adjacent_words(adjacent_words)
    assert is_valid, "BOXES should be valid"
    
    print("✓ Valid adjacent word test passed")


def test_no_adjacent_words():
    """Test that words with no adjacent tiles return empty list"""
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Place a word with space around it
    state.board[7][7] = 'C'
    state.board[7][8] = 'A'
    state.board[7][9] = 'T'
    
    # Try to place "DOG" at (7, 11) - no adjacent tiles
    adjacent_words = state.find_adjacent_words_same_direction(7, 11, "DOG", "Across")
    
    print(f"Adjacent words found: {adjacent_words}")
    assert len(adjacent_words) == 0, "Should find no adjacent words"
    
    # Validate - should succeed (no words to check)
    is_valid = state.validate_adjacent_words(adjacent_words)
    assert is_valid, "Empty list should be valid"
    
    print("✓ No adjacent words test passed")


def test_vertical_adjacent_words():
    """Test adjacent word validation in vertical direction"""
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Place "FEATHER" vertically at (3, 7)
    for i, char in enumerate("FEATHER"):
        state.board[3 + i][7] = char
    
    # Try to place "YA" vertically at (10, 7) which would create "FEATHERYA"
    # This should be INVALID
    adjacent_words = state.find_adjacent_words_same_direction(10, 7, "YA", "Down")
    
    print(f"Adjacent words found: {adjacent_words}")
    assert len(adjacent_words) > 0, "Should find adjacent word"
    assert adjacent_words[0][0] == "FEATHERYA", f"Should form FEATHERYA, got {adjacent_words[0][0]}"
    
    # Validate - should fail
    is_valid = state.validate_adjacent_words(adjacent_words)
    assert not is_valid, "FEATHERYA should be invalid"
    
    print("✓ Vertical adjacent words test passed")


def test_full_validation_rejects_invalid_adjacent():
    """Test that _validate_move rejects moves with invalid adjacent words"""
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Place "BOXERS" on the board
    for i, char in enumerate("BOXERS"):
        state.board[7][5 + i] = char
    
    # Set up rack with tiles for "JOES"
    state.racks[0] = ['J', 'O', 'E', 'S', 'A', 'B', 'C']
    
    # Try to validate placing "JOES" at (7, 11)
    is_valid, tiles_used = state._validate_move(7, 11, "JOES", "Across", state.racks[0])
    
    assert not is_valid, "Should reject move that creates invalid adjacent word BOXERSJOES"
    assert tiles_used is None, "Should return None for tiles_used"
    
    print("✓ Full validation rejects invalid adjacent test passed")


def test_full_validation_accepts_valid_adjacent():
    """Test that _validate_move accepts moves with valid adjacent words"""
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Place "BOX" on the board
    for i, char in enumerate("BOX"):
        state.board[7][5 + i] = char
    
    # Set up rack with tiles for "ES"
    state.racks[0] = ['E', 'S', 'A', 'B', 'C', 'D', 'F']
    
    # Try to validate placing "ES" at (7, 8) to form "BOXES"
    is_valid, tiles_used = state._validate_move(7, 8, "ES", "Across", state.racks[0])
    
    assert is_valid, "Should accept move that creates valid adjacent word BOXES"
    assert tiles_used == ['E', 'S'], f"Should use E and S, got {tiles_used}"
    
    print("✓ Full validation accepts valid adjacent test passed")


def test_edge_case_single_letter_adjacent():
    """Test adjacent validation with single letter placements"""
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Place "CAT" on the board
    state.board[7][7] = 'C'
    state.board[7][8] = 'A'
    state.board[7][9] = 'T'
    
    # Try to place "S" at (7, 10) to form "CATS"
    adjacent_words = state.find_adjacent_words_same_direction(7, 10, "S", "Across")
    
    print(f"Adjacent words found: {adjacent_words}")
    assert len(adjacent_words) > 0, "Should find adjacent word"
    assert adjacent_words[0][0] == "CATS", f"Should form CATS, got {adjacent_words[0][0]}"
    
    # Validate - should succeed
    is_valid = state.validate_adjacent_words(adjacent_words)
    assert is_valid, "CATS should be valid"
    
    print("✓ Single letter adjacent test passed")


if __name__ == "__main__":
    test_adjacent_word_before()
    test_adjacent_word_after()
    test_adjacent_word_both_sides()
    test_valid_adjacent_word()
    test_no_adjacent_words()
    test_vertical_adjacent_words()
    test_full_validation_rejects_invalid_adjacent()
    test_full_validation_accepts_valid_adjacent()
    test_edge_case_single_letter_adjacent()
    
    print("\n✅ All adjacent word validation tests passed!")
