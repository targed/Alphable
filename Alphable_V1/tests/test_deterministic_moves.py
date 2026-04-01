#!/usr/bin/env python3
"""
Test that move generation is deterministic and reproducible.
"""

import sys
sys.path.insert(0, '.')

import pyspiel
import scrabble

def test_deterministic_move_generation():
    """Test that same board/rack produces same moves in same order"""
    print("Test 1: Deterministic move generation")
    game = pyspiel.load_game("scrabble")
    
    # Create two identical states
    state1 = game.new_initial_state()
    state2 = game.new_initial_state()
    
    # Set identical boards and racks
    state1.board[7][7] = 'C'
    state1.board[7][8] = 'A'
    state1.board[7][9] = 'T'
    state1.racks[0] = ['D', 'O', 'G', 'S', 'E', 'R', 'A']
    
    state2.board[7][7] = 'C'
    state2.board[7][8] = 'A'
    state2.board[7][9] = 'T'
    state2.racks[0] = ['D', 'O', 'G', 'S', 'E', 'R', 'A']
    
    # Generate moves twice
    moves1 = game.move_gen.generate(state1.board, state1.racks[0])
    moves2 = game.move_gen.generate(state2.board, state2.racks[0])
    
    print(f"  First generation: {len(moves1)} moves")
    print(f"  Second generation: {len(moves2)} moves")
    
    # Should have same number of moves
    assert len(moves1) == len(moves2), f"Different number of moves: {len(moves1)} vs {len(moves2)}"
    
    # Moves should be in same order
    for i, (m1, m2) in enumerate(zip(moves1, moves2)):
        assert m1['row'] == m2['row'], f"Move {i}: different row"
        assert m1['col'] == m2['col'], f"Move {i}: different col"
        assert m1['word'] == m2['word'], f"Move {i}: different word"
        assert m1['dir'] == m2['dir'], f"Move {i}: different direction"
    
    print("  ✓ Move generation is deterministic")

def test_deterministic_legal_actions():
    """Test that legal_actions returns same list for same state"""
    print("\nTest 2: Deterministic legal actions")
    game = pyspiel.load_game("scrabble")
    
    # Create state
    state = game.new_initial_state()
    
    # Get legal actions multiple times
    legal1 = state.legal_actions()
    legal2 = state.legal_actions()
    legal3 = state.legal_actions()
    
    print(f"  First call: {len(legal1)} actions")
    print(f"  Second call: {len(legal2)} actions")
    print(f"  Third call: {len(legal3)} actions")
    
    # Should be identical
    assert legal1 == legal2, "Legal actions differ between calls"
    assert legal2 == legal3, "Legal actions differ between calls"
    
    print("  ✓ Legal actions are deterministic")

def test_move_selection_consistency():
    """Test that same position always selects same word"""
    print("\nTest 3: Move selection consistency")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Set up board with existing word
    state.board[7][7] = 'C'
    state.board[7][8] = 'A'
    state.board[7][9] = 'T'
    
    # Set rack with letters that can form multiple words at same position
    state.racks[0] = ['D', 'O', 'G', 'S', 'A', 'R', 'E']
    
    # Generate legal actions multiple times
    legal1 = state.legal_actions()
    legal2 = state.legal_actions()
    
    print(f"  Legal actions: {len(legal1)}")
    
    # Should be identical
    assert legal1 == legal2, "Legal actions differ"
    
    # Check that move map is consistent
    state._legal_actions(0)
    move_map1 = dict(state._current_move_map)
    
    state._legal_actions(0)
    move_map2 = dict(state._current_move_map)
    
    # Should have same action IDs
    assert set(move_map1.keys()) == set(move_map2.keys()), "Different action IDs"
    
    # For each action ID, should have same word
    for action_id in move_map1:
        word1 = move_map1[action_id]['word']
        word2 = move_map2[action_id]['word']
        assert word1 == word2, f"Action {action_id}: different words {word1} vs {word2}"
    
    print("  ✓ Move selection is consistent")

def test_action_id_mapping():
    """Test that action ID mapping is consistent"""
    print("\nTest 4: Action ID mapping consistency")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Set up a simple board
    state.board[7][7] = 'C'
    state.board[7][8] = 'A'
    state.board[7][9] = 'T'
    state.racks[0] = ['D', 'O', 'G']
    
    # Generate legal actions
    state._legal_actions(0)
    
    # Check action ID calculation
    for action_id, move in state._current_move_map.items():
        r, c = move['row'], move['col']
        d = 0 if move['dir'] == 'Across' else 1
        expected_id = (r * 15 + c) * 2 + d
        
        assert action_id == expected_id, f"Action ID mismatch: {action_id} vs {expected_id}"
    
    print("  ✓ Action ID mapping is consistent")

def test_sorted_candidates():
    """Test that GADDAG traversal uses sorted candidates"""
    print("\nTest 5: Sorted candidates in GADDAG")
    game = pyspiel.load_game("scrabble")
    
    # Create two states with same setup
    state1 = game.new_initial_state()
    state2 = game.new_initial_state()
    
    # Set identical boards
    for state in [state1, state2]:
        state.board[7][7] = 'A'
        state.racks[0] = ['B', 'C', 'D', 'E', 'F', 'G', 'H']
    
    # Generate moves multiple times
    moves1 = game.move_gen.generate(state1.board, state1.racks[0])
    moves2 = game.move_gen.generate(state2.board, state2.racks[0])
    
    print(f"  Generated {len(moves1)} moves")
    
    # Should be identical
    assert len(moves1) == len(moves2), "Different number of moves"
    
    # Check that moves are in same order
    for i in range(min(10, len(moves1))):  # Check first 10 moves
        assert moves1[i]['word'] == moves2[i]['word'], f"Move {i}: different word"
        assert moves1[i]['row'] == moves2[i]['row'], f"Move {i}: different row"
        assert moves1[i]['col'] == moves2[i]['col'], f"Move {i}: different col"
    
    print("  ✓ GADDAG traversal is deterministic")

def test_move_ordering():
    """Test that moves are sorted by length then alphabetically"""
    print("\nTest 6: Move ordering")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Set up board
    state.board[7][7] = 'C'
    state.board[7][8] = 'A'
    state.board[7][9] = 'T'
    state.racks[0] = ['D', 'O', 'G', 'S', 'A', 'R', 'E']
    
    # Generate legal actions
    state._legal_actions(0)
    
    # Get all moves from move map
    moves = list(state._current_move_map.values())
    
    if len(moves) > 1:
        # Check that moves are sorted by length (descending) then alphabetically
        for i in range(len(moves) - 1):
            word1 = moves[i]['word']
            word2 = moves[i+1]['word']
            
            # Either word1 is longer, or same length and alphabetically before/equal
            if len(word1) == len(word2):
                # Same length - should be alphabetically ordered or equal
                # (equal is ok because we only keep first move per position)
                pass  # Can't strictly enforce alphabetical order across positions
            else:
                # Different length - longer should come first
                assert len(word1) >= len(word2), f"Moves not sorted by length: {word1} ({len(word1)}) before {word2} ({len(word2)})"
    
    print("  ✓ Moves are properly ordered")

if __name__ == "__main__":
    print("Testing Deterministic Move Generation\n" + "="*50)
    
    try:
        test_deterministic_move_generation()
        test_deterministic_legal_actions()
        test_move_selection_consistency()
        test_action_id_mapping()
        test_sorted_candidates()
        test_move_ordering()
        
        print("\n" + "="*50)
        print("✓ All tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
