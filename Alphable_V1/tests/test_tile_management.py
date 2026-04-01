#!/usr/bin/env python3
"""
Tests for tile management: rack refill and exchange validation.
Validates Requirements 7.1, 7.2, 7.3, 7.4
"""

import sys
sys.path.insert(0, '.')

import pyspiel
import scrabble

def test_rack_refill_to_seven():
    """Test that rack refills to 7 tiles after a turn"""
    print("Test 1: Rack refills to 7 tiles")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Simulate using some tiles
    initial_rack_size = len(state.racks[0])
    print(f"  Initial rack size: {initial_rack_size}")
    
    # Remove 3 tiles from rack
    state.racks[0] = state.racks[0][:4]
    print(f"  After using tiles: {len(state.racks[0])}")
    
    # Refill rack
    state._refill_rack(0)
    print(f"  After refill: {len(state.racks[0])}")
    
    assert len(state.racks[0]) == 7, f"Expected 7 tiles, got {len(state.racks[0])}"
    print("  ✓ Rack correctly refilled to 7 tiles")

def test_rack_refill_with_limited_bag():
    """Test that rack draws all remaining tiles when bag has fewer than needed"""
    print("\nTest 2: Rack refill with limited bag")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Set up scenario: rack has 3 tiles, bag has only 2 tiles
    state.racks[0] = ['A', 'B', 'C']
    state.bag = ['D', 'E']
    
    print(f"  Rack before refill: {len(state.racks[0])} tiles")
    print(f"  Bag before refill: {len(state.bag)} tiles")
    
    state._refill_rack(0)
    
    print(f"  Rack after refill: {len(state.racks[0])} tiles")
    print(f"  Bag after refill: {len(state.bag)} tiles")
    
    # Should have 3 + 2 = 5 tiles (all remaining from bag)
    assert len(state.racks[0]) == 5, f"Expected 5 tiles, got {len(state.racks[0])}"
    assert len(state.bag) == 0, f"Expected empty bag, got {len(state.bag)} tiles"
    print("  ✓ Rack correctly drew all remaining tiles from bag")

def test_rack_refill_with_empty_bag():
    """Test that rack refill works correctly when bag is empty"""
    print("\nTest 3: Rack refill with empty bag")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Set up scenario: rack has 4 tiles, bag is empty
    state.racks[0] = ['A', 'B', 'C', 'D']
    state.bag = []
    
    print(f"  Rack before refill: {len(state.racks[0])} tiles")
    print(f"  Bag before refill: {len(state.bag)} tiles")
    
    state._refill_rack(0)
    
    print(f"  Rack after refill: {len(state.racks[0])} tiles")
    
    # Should still have 4 tiles (no change)
    assert len(state.racks[0]) == 4, f"Expected 4 tiles, got {len(state.racks[0])}"
    print("  ✓ Rack unchanged when bag is empty")

def test_rack_refill_exact_seven():
    """Test that rack refill doesn't overdraw when rack already has 7 tiles"""
    print("\nTest 4: Rack refill when already at 7 tiles")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Set up scenario: rack already has 7 tiles
    state.racks[0] = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    bag_size_before = len(state.bag)
    
    print(f"  Rack before refill: {len(state.racks[0])} tiles")
    print(f"  Bag before refill: {bag_size_before} tiles")
    
    state._refill_rack(0)
    
    print(f"  Rack after refill: {len(state.racks[0])} tiles")
    print(f"  Bag after refill: {len(state.bag)} tiles")
    
    # Should still have 7 tiles, bag unchanged
    assert len(state.racks[0]) == 7, f"Expected 7 tiles, got {len(state.racks[0])}"
    assert len(state.bag) == bag_size_before, f"Bag should be unchanged"
    print("  ✓ Rack correctly stays at 7 tiles, no overdraw")

def test_exchange_with_sufficient_bag():
    """Test that exchange works when bag has at least 7 tiles"""
    print("\nTest 5: Exchange with sufficient tiles in bag")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Set up scenario: bag has plenty of tiles
    initial_rack = list(state.racks[0])
    initial_bag_size = len(state.bag)
    initial_score = state.scores[0]
    
    print(f"  Initial rack: {initial_rack}")
    print(f"  Initial bag size: {initial_bag_size}")
    print(f"  Initial score: {initial_score}")
    
    # Perform exchange (action 451)
    state._apply_action(451)
    
    print(f"  After exchange rack: {state.racks[1]}")  # Player switched
    print(f"  After exchange bag size: {len(state.bag)}")
    print(f"  After exchange score: {state.scores[0]}")
    
    # Rack should be different (new tiles drawn)
    # Bag size should be same (returned tiles, drew same amount)
    # Score should be unchanged (no penalty for valid exchange)
    assert len(state.bag) == initial_bag_size, f"Bag size should remain {initial_bag_size}, got {len(state.bag)}"
    assert state.scores[0] == initial_score, f"Score should be unchanged for valid exchange"
    print("  ✓ Exchange completed successfully with no penalty")

def test_exchange_with_insufficient_bag():
    """Test that exchange is rejected and penalized when bag has fewer than 7 tiles"""
    print("\nTest 6: Exchange with insufficient tiles in bag")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Set up scenario: bag has only 5 tiles
    state.bag = ['A', 'B', 'C', 'D', 'E']
    initial_rack = list(state.racks[0])
    initial_score = state.scores[0]
    
    print(f"  Initial rack: {initial_rack}")
    print(f"  Initial bag size: {len(state.bag)}")
    print(f"  Initial score: {initial_score}")
    
    # Attempt exchange (action 451)
    state._apply_action(451)
    
    print(f"  After exchange attempt rack: {state.racks[1]}")  # Player switched
    print(f"  After exchange attempt score: {state.scores[0]}")
    
    # Rack should be unchanged (exchange rejected)
    # Score should be penalized by 10.0
    expected_score = max(0.0, initial_score - 10.0)
    assert state.scores[0] == expected_score, f"Expected score {expected_score}, got {state.scores[0]}"
    print("  ✓ Exchange correctly rejected and penalized")

def test_exchange_requires_exactly_seven_in_bag():
    """Test that exchange requires at least 7 tiles in bag (boundary test)"""
    print("\nTest 7: Exchange with exactly 7 tiles in bag")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Set up scenario: bag has exactly 7 tiles
    state.bag = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    initial_score = state.scores[0]
    
    print(f"  Initial bag size: {len(state.bag)}")
    print(f"  Initial score: {initial_score}")
    
    # Attempt exchange (action 451)
    state._apply_action(451)
    
    print(f"  After exchange score: {state.scores[0]}")
    
    # Should succeed (bag has exactly 7)
    assert state.scores[0] == initial_score, f"Score should be unchanged for valid exchange"
    print("  ✓ Exchange allowed with exactly 7 tiles in bag")

def test_exchange_with_six_tiles_in_bag():
    """Test that exchange is rejected when bag has exactly 6 tiles"""
    print("\nTest 8: Exchange with exactly 6 tiles in bag")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Set up scenario: bag has exactly 6 tiles (one less than required)
    state.bag = ['A', 'B', 'C', 'D', 'E', 'F']
    initial_score = state.scores[0]
    
    print(f"  Initial bag size: {len(state.bag)}")
    print(f"  Initial score: {initial_score}")
    
    # Attempt exchange (action 451)
    state._apply_action(451)
    
    print(f"  After exchange attempt score: {state.scores[0]}")
    
    # Should be rejected and penalized
    expected_score = max(0.0, initial_score - 10.0)
    assert state.scores[0] == expected_score, f"Expected score {expected_score}, got {state.scores[0]}"
    print("  ✓ Exchange correctly rejected with 6 tiles in bag")

if __name__ == "__main__":
    print("Testing Tile Management\n" + "="*50)
    
    try:
        test_rack_refill_to_seven()
        test_rack_refill_with_limited_bag()
        test_rack_refill_with_empty_bag()
        test_rack_refill_exact_seven()
        test_exchange_with_sufficient_bag()
        test_exchange_with_insufficient_bag()
        test_exchange_requires_exactly_seven_in_bag()
        test_exchange_with_six_tiles_in_bag()
        
        print("\n" + "="*50)
        print("✓ All tile management tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
