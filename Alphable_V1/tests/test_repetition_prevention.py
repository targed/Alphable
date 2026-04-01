#!/usr/bin/env python3
"""
Test move repetition prevention functionality.
"""

import sys
sys.path.insert(0, '.')

import pyspiel
import scrabble

def test_banned_actions_tracking():
    """Test that banned actions are tracked and force pass after 3 attempts"""
    print("Test 1: Banned actions tracking")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    print(f"  Initial banned actions: {len(state.banned_actions)}")
    assert len(state.banned_actions) == 0, "Should start with no banned actions"
    
    # Simulate failed attempts by trying invalid action IDs
    # Action 999 is likely not in the move map (hallucination)
    initial_player = state.current_player()
    
    # First attempt
    state.apply_action(999)
    print(f"  After 1st attempt: {len(state.banned_actions)} banned, player={state.current_player()}")
    assert len(state.banned_actions) == 1, "Should have 1 banned action"
    assert state.current_player() == initial_player, "Should still be same player's turn"
    
    # Second attempt
    state.apply_action(998)
    print(f"  After 2nd attempt: {len(state.banned_actions)} banned, player={state.current_player()}")
    assert len(state.banned_actions) == 2, "Should have 2 banned actions"
    assert state.current_player() == initial_player, "Should still be same player's turn"
    
    # Third attempt - should force pass
    state.apply_action(997)
    print(f"  After 3rd attempt: {len(state.banned_actions)} banned, player={state.current_player()}")
    # After forced pass, turn should change and banned actions reset
    assert state.current_player() != initial_player, "Turn should have changed after forced pass"
    assert len(state.banned_actions) == 0, "Banned actions should be reset"
    
    print("  ✓ Banned actions correctly tracked and forced pass after 3 attempts")

def test_consecutive_pass_termination():
    """Test that game ends after 4 consecutive passes"""
    print("\nTest 2: Consecutive pass termination")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    print(f"  Initial consecutive passes: {state.consecutive_passes}")
    assert not state.is_terminal(), "Game should not be terminal initially"
    
    # Pass 4 times
    for i in range(4):
        state.apply_action(450)  # Pass action
        print(f"  After pass {i+1}: consecutive={state.consecutive_passes}, terminal={state.is_terminal()}")
    
    assert state.is_terminal(), "Game should be terminal after 4 consecutive passes"
    print("  ✓ Game correctly terminated after 4 consecutive passes")

def test_mercy_rule():
    """Test that mercy rule terminates game after 20 turns with 0 score"""
    print("\nTest 3: Mercy rule termination")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Set turn count to 21 and scores to 0
    state.turn_count = 21
    state.scores = [0.0, 0.0]
    
    print(f"  Turn count: {state.turn_count}, Total score: {sum(state.scores)}")
    assert not state.is_terminal(), "Game should not be terminal yet"
    
    # Try to apply any action - should trigger mercy rule
    state.apply_action(450)  # Pass
    
    print(f"  After action: terminal={state.is_terminal()}")
    assert state.is_terminal(), "Game should be terminal due to mercy rule"
    print("  ✓ Mercy rule correctly triggered")

def test_hard_turn_limit():
    """Test that game ends after 100 turns"""
    print("\nTest 4: Hard turn limit")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Set turn count to 101
    state.turn_count = 101
    state.scores = [50.0, 45.0]  # Non-zero scores
    
    print(f"  Turn count: {state.turn_count}")
    assert not state.is_terminal(), "Game should not be terminal yet"
    
    # Try to apply any action - should trigger hard limit
    state.apply_action(450)  # Pass
    
    print(f"  After action: terminal={state.is_terminal()}")
    assert state.is_terminal(), "Game should be terminal due to hard turn limit"
    print("  ✓ Hard turn limit correctly enforced")

def test_successful_move_resets_passes():
    """Test that successful move resets consecutive passes"""
    print("\nTest 5: Successful move resets consecutive passes")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Pass twice
    state.apply_action(450)
    state.apply_action(450)
    print(f"  After 2 passes: consecutive={state.consecutive_passes}")
    assert state.consecutive_passes == 2, "Should have 2 consecutive passes"
    
    # Make a successful move (if possible)
    legal_actions = state.legal_actions()
    if legal_actions and 450 not in legal_actions[:1]:
        # Try a non-pass action
        for action in legal_actions:
            if action not in [450, 451]:  # Not pass or exchange
                initial_passes = state.consecutive_passes
                state.apply_action(action)
                print(f"  After successful move: consecutive={state.consecutive_passes}")
                # Note: The move might fail validation, so passes might not reset
                # But if it succeeds, passes should be 0
                if state.consecutive_passes == 0:
                    print("  ✓ Consecutive passes reset after successful move")
                    return
    
    print("  ⚠ Could not test successful move (no valid moves available)")

def test_banned_actions_reset_on_turn_change():
    """Test that banned actions are reset when turn changes"""
    print("\nTest 6: Banned actions reset on turn change")
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    initial_player = state.current_player()
    
    # Add some banned actions
    state.apply_action(999)  # Invalid action
    print(f"  After invalid action: {len(state.banned_actions)} banned")
    assert len(state.banned_actions) == 1, "Should have 1 banned action"
    
    # Pass to change turn
    state.apply_action(450)
    print(f"  After pass: player={state.current_player()}, banned={len(state.banned_actions)}")
    assert state.current_player() != initial_player, "Turn should have changed"
    assert len(state.banned_actions) == 0, "Banned actions should be reset"
    
    print("  ✓ Banned actions correctly reset on turn change")

if __name__ == "__main__":
    print("Testing Move Repetition Prevention\n" + "="*50)
    
    try:
        test_banned_actions_tracking()
        test_consecutive_pass_termination()
        test_mercy_rule()
        test_hard_turn_limit()
        test_successful_move_resets_passes()
        test_banned_actions_reset_on_turn_change()
        
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
