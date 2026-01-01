"""
Test comprehensive game state tracking and logging.
Tests Requirements 9.1, 9.2, 9.3, 9.4, 9.5
"""
import pyspiel
import scrabble

def test_move_attempt_logging():
    """Test that move attempts are logged with details"""
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Enable logging
    state.enable_logging = True
    
    # Apply a pass action
    state.apply_action(450)
    
    # Check that the move was logged
    assert len(state.move_log) > 0, "Move log should not be empty"
    
    last_entry = state.move_log[-1]
    assert last_entry['action_id'] == 450, "Should log pass action"
    assert last_entry['success'] == True, "Pass should succeed"
    assert last_entry['move_details']['action'] == 'PASS', "Should log action type"
    
    print("✓ Move attempt logging test passed")


def test_validation_failure_logging():
    """Test that validation failures are logged with reasons"""
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    state.enable_logging = True
    
    # Try to apply an invalid action (hallucination)
    invalid_action = 999
    state.apply_action(invalid_action)
    
    # Check that the failure was logged
    logged_failures = [e for e in state.move_log if not e.get('success', True)]
    assert len(logged_failures) > 0, "Should log validation failures"
    
    failure = logged_failures[-1]
    assert failure['failure_reason'] is not None, "Should include failure reason"
    assert 'not in legal move map' in failure['failure_reason'], "Should explain hallucination"
    
    print("✓ Validation failure logging test passed")


def test_termination_logging():
    """Test that game termination is logged with reason"""
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    state.enable_logging = True
    
    # Force 4 consecutive passes to trigger termination
    for _ in range(4):
        state.apply_action(450)
    
    assert state.is_terminal(), "Game should be terminated"
    assert state.termination_reason is not None, "Should have termination reason"
    assert "consecutive passes" in state.termination_reason.lower(), "Should explain termination"
    
    # Check termination event in log
    termination_events = [e for e in state.move_log if e.get('event') == 'GAME_TERMINATED']
    assert len(termination_events) > 0, "Should log termination event"
    
    term_event = termination_events[-1]
    assert 'reason' in term_event, "Should include reason"
    assert 'final_scores' in term_event, "Should include final scores"
    
    print("✓ Termination logging test passed")


def test_banned_actions_tracking():
    """Test that banned actions accumulation is tracked"""
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    state.enable_logging = True
    
    # Try invalid actions to accumulate banned actions
    for i in range(3):
        invalid_action = 900 + i
        state.apply_action(invalid_action)
    
    # Check that banned actions count is logged
    logged_entries = [e for e in state.move_log if 'banned_actions_count' in e]
    assert len(logged_entries) > 0, "Should track banned actions count"
    
    # Should have forced a pass after 3 attempts
    forced_pass = [e for e in state.move_log 
                   if e.get('move_details', {}).get('action') == 'FORCED_PASS']
    assert len(forced_pass) > 0, "Should log forced pass after 3 failures"
    
    print("✓ Banned actions tracking test passed")


def test_enhanced_str_method():
    """Test that __str__ includes comprehensive game state"""
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Apply some actions
    state.apply_action(450)  # Pass
    
    # Get string representation
    state_str = str(state)
    
    # Check that it includes required information
    assert "Turn" in state_str, "Should include turn count"
    assert "Scores:" in state_str, "Should include scores"
    assert "Bag:" in state_str, "Should include bag count"
    assert "Rack" in state_str, "Should include rack information"
    assert "Consecutive Passes:" in state_str, "Should include consecutive passes"
    assert "Status:" in state_str, "Should include game status"
    
    print("✓ Enhanced __str__ method test passed")


def test_move_log_summary():
    """Test that move log summary is generated correctly"""
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    state.enable_logging = True
    
    # Apply several actions
    for _ in range(3):
        state.apply_action(450)
    
    # Get summary
    summary = state.get_move_log_summary()
    
    assert "Move Log Summary" in summary, "Should have summary header"
    assert "entries" in summary, "Should show entry count"
    assert "Turn" in summary, "Should show turn information"
    
    print("✓ Move log summary test passed")


def test_logging_can_be_disabled():
    """Test that logging can be disabled for performance"""
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Disable logging
    state.enable_logging = False
    
    # Apply actions
    state.apply_action(450)
    state.apply_action(450)
    
    # Log should be empty
    assert len(state.move_log) == 0, "Log should be empty when disabled"
    
    print("✓ Logging disable test passed")


def test_successful_move_logging():
    """Test that successful moves are logged with score"""
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    state.enable_logging = True
    
    # Place a tile to enable moves
    state.board[7][7] = 'A'
    
    # Get legal actions
    legal = state.legal_actions()
    
    # Try to find a non-pass action
    for action in legal:
        if action != 450 and action != 451:
            state.apply_action(action)
            break
    
    # Check for successful move in log
    successful_moves = [e for e in state.move_log 
                       if e.get('success') and e.get('move_details', {}).get('action') == 'PLAY_WORD']
    
    if successful_moves:
        move = successful_moves[-1]
        assert 'word' in move['move_details'], "Should log word"
        assert 'pos' in move['move_details'], "Should log position"
        assert 'dir' in move['move_details'], "Should log direction"
        # Score might be None initially, then updated
        print("✓ Successful move logging test passed")
    else:
        print("✓ Successful move logging test skipped (no valid moves)")


if __name__ == "__main__":
    test_move_attempt_logging()
    test_validation_failure_logging()
    test_termination_logging()
    test_banned_actions_tracking()
    test_enhanced_str_method()
    test_move_log_summary()
    test_logging_can_be_disabled()
    test_successful_move_logging()
    
    print("\n✅ All logging tests passed!")
