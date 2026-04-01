#!/usr/bin/env python3
"""
Simple test to verify score floor constraints work correctly.
Tests that penalties don't cause negative scores.
"""

import sys
sys.path.insert(0, '.')

import pyspiel
import scrabble

def test_score_floor_basic():
    """Test that penalties don't cause negative scores"""
    print("Test 1: Basic penalty with low score")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Set a low score
    state.scores[0] = 5.0
    print(f"  Initial score: {state.scores[0]}")
    
    # Apply penalty that would make it negative
    state.apply_penalty(0, 10.0)
    print(f"  After 10.0 penalty: {state.scores[0]}")
    
    assert state.scores[0] == 0.0, f"Expected 0.0, got {state.scores[0]}"
    print("  ✓ Score correctly floored at 0.0")

def test_score_floor_multiple_penalties():
    """Test multiple penalties don't cause negative scores"""
    print("\nTest 2: Multiple penalties")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    state.scores[1] = 15.0
    print(f"  Initial score: {state.scores[1]}")
    
    # Apply multiple penalties
    state.apply_penalty(1, 10.0)
    print(f"  After 1st penalty: {state.scores[1]}")
    state.apply_penalty(1, 10.0)
    print(f"  After 2nd penalty: {state.scores[1]}")
    state.apply_penalty(1, 10.0)
    print(f"  After 3rd penalty: {state.scores[1]}")
    
    assert state.scores[1] == 0.0, f"Expected 0.0, got {state.scores[1]}"
    print("  ✓ Score correctly floored at 0.0 after multiple penalties")

def test_final_score_adjustment():
    """Test that final score adjustment maintains non-negative scores"""
    print("\nTest 3: Final score adjustment")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Set up end-game scenario with unplayed tiles
    state.scores[0] = 10.0
    state.scores[1] = 5.0
    state.racks[0] = ['A', 'B', 'C']  # 1+3+3 = 7 points
    state.racks[1] = ['D', 'E']  # 2+1 = 3 points
    state.bag = []  # Empty bag
    state._game_over = True
    
    print(f"  Initial scores: P0={state.scores[0]}, P1={state.scores[1]}")
    print(f"  Unplayed tiles: P0={state.racks[0]}, P1={state.racks[1]}")
    
    state.adjust_final_scores()
    
    print(f"  Final scores: P0={state.scores[0]}, P1={state.scores[1]}")
    
    assert state.scores[0] >= 0.0, f"P0 score is negative: {state.scores[0]}"
    assert state.scores[1] >= 0.0, f"P1 score is negative: {state.scores[1]}"
    print("  ✓ Both final scores are non-negative")

def test_out_bonus():
    """Test that player who goes out gets opponent's tiles added"""
    print("\nTest 4: Out bonus")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Player 0 goes out
    state.scores[0] = 50.0
    state.scores[1] = 40.0
    state.racks[0] = []  # Went out
    state.racks[1] = ['Q', 'Z']  # 10+10 = 20 points
    state.bag = []  # Empty bag
    state._game_over = True
    
    print(f"  Initial scores: P0={state.scores[0]}, P1={state.scores[1]}")
    print(f"  P0 went out, P1 has: {state.racks[1]}")
    
    state.adjust_final_scores()
    
    print(f"  Final scores: P0={state.scores[0]}, P1={state.scores[1]}")
    
    # P0 should get +20, P1 should get -20
    assert state.scores[0] == 70.0, f"Expected P0=70.0, got {state.scores[0]}"
    assert state.scores[1] == 20.0, f"Expected P1=20.0, got {state.scores[1]}"
    print("  ✓ Out bonus correctly applied")

if __name__ == "__main__":
    print("Testing Score Floor Constraints\n" + "="*50)
    
    try:
        test_score_floor_basic()
        test_score_floor_multiple_penalties()
        test_final_score_adjustment()
        test_out_bonus()
        
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
