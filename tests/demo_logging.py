"""
Demonstration of the enhanced logging and state tracking features.
"""
import pyspiel
import scrabble

def demo_logging():
    """Demonstrate the logging features"""
    print("=" * 70)
    print("SCRABBLE ENGINE - LOGGING DEMONSTRATION")
    print("=" * 70)
    print()
    
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    # Enable logging
    state.enable_logging = True
    
    print("1. Initial State:")
    print(state)
    print()
    
    # Apply some actions
    print("2. Applying a pass action...")
    state.apply_action(450)
    print()
    
    print("3. Attempting an invalid action (hallucination)...")
    state.apply_action(999)
    print()
    
    print("4. Attempting another invalid action...")
    state.apply_action(998)
    print()
    
    print("5. One more invalid action (should force pass)...")
    state.apply_action(997)
    print()
    
    print("6. Current State:")
    print(state)
    print()
    
    print("7. Move Log Summary:")
    print(state.get_move_log_summary())
    print()
    
    # Force termination
    print("8. Forcing game termination with consecutive passes...")
    for i in range(3):
        state.apply_action(450)
    print()
    
    print("9. Final State:")
    print(state)
    print()
    
    print("=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    demo_logging()
