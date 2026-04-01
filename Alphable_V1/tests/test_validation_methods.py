#!/usr/bin/env python3
"""
Test validation methods for Requirements 3.1, 3.2, 3.3, 3.4, 3.5
Tests the four validation methods implemented in task 9.
"""

import sys
sys.path.insert(0, '.')

import pyspiel
import scrabble

def test_board_connectivity_first_move():
    """Test that first move must cover center square (7,7)"""
    print("Test 1: First move center square validation")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # First move NOT covering center - should fail
    result = state.validate_board_connectivity(5, 5, "CAT", "Across")
    assert result == False, "First move not covering center should fail"
    print("  ✓ First move not covering center correctly rejected")
    
    # First move covering center - should pass
    result = state.validate_board_connectivity(7, 5, "CAT", "Across")
    assert result == True, "First move covering center should pass"
    print("  ✓ First move covering center correctly accepted")

def test_board_connectivity_subsequent_moves():
    """Test that subsequent moves must connect to existing tiles"""
    print("\nTest 2: Subsequent move connectivity validation")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Place a tile on the board
    state.board[7][7] = 'C'
    
    # Move connecting to existing tile - should pass
    result = state.validate_board_connectivity(7, 8, "AT", "Across")
    assert result == True, "Move connecting to existing tile should pass"
    print("  ✓ Connected move correctly accepted")
    
    # Move NOT connecting to existing tile - should fail
    result = state.validate_board_connectivity(0, 0, "DOG", "Across")
    assert result == False, "Move not connecting should fail"
    print("  ✓ Disconnected move correctly rejected")

def test_boundary_validation():
    """Test that moves must stay within board boundaries [0, 14]"""
    print("\nTest 3: Boundary validation")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Valid move within boundaries
    result = state.validate_boundaries(0, 0, "CAT", "Across")
    assert result == True, "Move within boundaries should pass"
    print("  ✓ Move within boundaries correctly accepted")
    
    # Move going off right edge
    result = state.validate_boundaries(0, 13, "CAT", "Across")
    assert result == False, "Move going off right edge should fail"
    print("  ✓ Move off right edge correctly rejected")
    
    # Move going off bottom edge
    result = state.validate_boundaries(13, 0, "CAT", "Down")
    assert result == False, "Move going off bottom edge should fail"
    print("  ✓ Move off bottom edge correctly rejected")
    
    # Move at exact boundary (should pass)
    result = state.validate_boundaries(0, 12, "CAT", "Across")
    assert result == True, "Move at exact boundary should pass"
    print("  ✓ Move at exact boundary correctly accepted")

def test_rack_availability_validation():
    """Test that player must have required tiles in rack"""
    print("\nTest 4: Rack availability validation")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    rack = ['C', 'A', 'T', 'D', 'O', 'G', 'S']
    
    # Word using tiles from rack - should pass
    result, tiles_used = state.validate_rack_availability("CAT", "Across", 7, 7, rack)
    assert result == True, "Word using available tiles should pass"
    assert tiles_used == ['C', 'A', 'T'], f"Expected ['C', 'A', 'T'], got {tiles_used}"
    print("  ✓ Word with available tiles correctly accepted")
    
    # Word using tiles NOT in rack - should fail
    result, tiles_used = state.validate_rack_availability("ZOO", "Across", 7, 7, rack)
    assert result == False, "Word using unavailable tiles should fail"
    print("  ✓ Word with unavailable tiles correctly rejected")
    
    # Word using blank as wildcard
    rack_with_blank = ['C', 'A', '?', 'D', 'O', 'G', 'S']
    result, tiles_used = state.validate_rack_availability("CAT", "Across", 7, 7, rack_with_blank)
    assert result == True, "Word using blank as wildcard should pass"
    assert '?' in tiles_used, "Blank should be used"
    print("  ✓ Blank tile as wildcard correctly handled")

def test_rack_availability_with_existing_tiles():
    """Test rack validation when word uses existing board tiles"""
    print("\nTest 5: Rack availability with existing tiles")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Place existing tiles on board
    state.board[7][7] = 'C'
    state.board[7][8] = 'A'
    
    rack = ['T', 'D', 'O', 'G', 'S', 'E', 'R']
    
    # Word "CAT" where C and A are already on board, only need T from rack
    result, tiles_used = state.validate_rack_availability("CAT", "Across", 7, 7, rack)
    assert result == True, "Word using existing tiles should pass"
    assert tiles_used == ['T'], f"Expected ['T'], got {tiles_used}"
    print("  ✓ Word using existing tiles correctly validated")

def test_tile_matching_validation():
    """Test that word must match existing board tiles"""
    print("\nTest 6: Tile matching validation")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Place existing tiles on board
    state.board[7][7] = 'C'
    state.board[7][8] = 'A'
    
    # Word matching existing tiles - should pass
    result = state.validate_tile_matching(7, 7, "CAT", "Across")
    assert result == True, "Word matching existing tiles should pass"
    print("  ✓ Word matching existing tiles correctly accepted")
    
    # Word NOT matching existing tiles - should fail
    result = state.validate_tile_matching(7, 7, "DOG", "Across")
    assert result == False, "Word not matching existing tiles should fail"
    print("  ✓ Word not matching existing tiles correctly rejected")
    
    # Partial match - should fail
    result = state.validate_tile_matching(7, 7, "COT", "Across")
    assert result == False, "Word with partial match should fail"
    print("  ✓ Word with partial match correctly rejected")

def test_integrated_validation():
    """Test that _validate_move uses all validation methods"""
    print("\nTest 7: Integrated validation")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    rack = ['C', 'A', 'T', 'D', 'O', 'G', 'S']
    
    # Valid first move covering center
    result, tiles_used = state._validate_move(7, 5, "CAT", "Across", rack)
    assert result == True, "Valid first move should pass all validations"
    print("  ✓ Valid move passed all validations")
    
    # Invalid move - off board
    result, tiles_used = state._validate_move(0, 13, "CAT", "Across", rack)
    assert result == False, "Move off board should fail validation"
    print("  ✓ Move off board failed validation")
    
    # Invalid move - not connecting (after first move)
    state.board[7][7] = 'C'
    result, tiles_used = state._validate_move(0, 0, "DOG", "Across", rack)
    assert result == False, "Disconnected move should fail validation"
    print("  ✓ Disconnected move failed validation")
    
    # Invalid move - missing tiles in rack
    result, tiles_used = state._validate_move(7, 8, "ZOO", "Across", rack)
    assert result == False, "Move with missing tiles should fail validation"
    print("  ✓ Move with missing tiles failed validation")

if __name__ == "__main__":
    print("Testing Validation Methods (Task 9)\n" + "="*60)
    
    try:
        test_board_connectivity_first_move()
        test_board_connectivity_subsequent_moves()
        test_boundary_validation()
        test_rack_availability_validation()
        test_rack_availability_with_existing_tiles()
        test_tile_matching_validation()
        test_integrated_validation()
        
        print("\n" + "="*60)
        print("✓ All validation method tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
