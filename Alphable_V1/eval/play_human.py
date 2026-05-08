import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"
import pyspiel
from open_spiel.python.algorithms.alpha_zero import model as model_lib
from open_spiel.python.algorithms.alpha_zero import evaluator as az_evaluator
from open_spiel.python.algorithms import mcts
import scrabble

def play(checkpoint_num):
    game = pyspiel.load_game("scrabble")
    # Load your latest checkpoint
    model = model_lib.Model.build_model("resnet", [35,15,15], 452, 64, 3, weight_decay=1e-4, learning_rate=0.001, path="../data/scrabble_az_checkpoints")
    checkpoint_path = f"../data/scrabble_az_checkpoints/checkpoint-{checkpoint_num}"
    model.load_checkpoint(checkpoint_path)
    
    az_eval = az_evaluator.AlphaZeroEvaluator(game, model)
    # Give it good thinking time against you
    bot = mcts.MCTSBot(game, 2.0, 400, evaluator=az_eval) 
    
    state = game.new_initial_state()
    
    print("\n--- HUMAN vs Alphable ---")
    
    while not state.is_terminal():
        print(f"\n{state}")
        
        if state.current_player() == 0:
            # Human Turn
            print(f"YOUR RACK: {state.racks[0]}")
            print("Enter move (Row Col Word Dir) e.g., '7 7 HELLO Across'")
            print("Or 'p' to pass, 'e' to exchange")
            
            valid = False
            while not valid:
                inp = input(">> ").strip().upper()
                if inp == 'P':
                    action = 450
                    valid = True
                elif inp == 'E':
                    action = 451
                    valid = True
                else:
                    try:
                        parts = inp.split()
                        r, c, w, d_str = int(parts[0]), int(parts[1]), parts[2], parts[3]
                        
                        # Direct Action ID calculation
                        d = 0 if d_str.capitalize() == 'Across' else 1
                        aid = (r * 15 + c) * 2 + d

                        # Ensure map is populated
                        if not hasattr(state, "_current_move_map") or not state._current_move_map:
                            state.legal_actions() # This populates _current_move_map
                            
                        found = False
                        if aid in state._current_move_map:
                            m = state._current_move_map[aid]
                            if m['word'] == w:
                                action = aid
                                found = True
                                valid = True

                        if not found: print("Invalid move (not found in generator)")
                    except:
                        print("Format error. Use: Row Col Word Direction")
        else:
            # Bot Turn
            print("Bot is thinking...")
            action = bot.step(state)
            
        state.apply_action(action)

    print(f"Game Over: {state.scores}")

if __name__ == "__main__":
    play(1080)