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
    model = model_lib.Model.build_model("resnet", [35,15,15], 452, 64, 3, weight_decay=1e-4, learning_rate=0.001, path="data/scrabble_az_checkpoints")
    checkpoint_path = f"./data/scrabble_az_checkpoints/checkpoint-{checkpoint_num}"
    model.load_checkpoint(checkpoint_path)
    
    az_eval = az_evaluator.AlphaZeroEvaluator(game, model)
    # Give it good thinking time against you
    bot = mcts.MCTSBot(game, 2.0, 400, evaluator=az_eval) 
    
    state = game.new_initial_state()
    
    print("\n--- HUMAN vs ALPHAZERO ---")
    
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
                        r, c, w, d = int(parts[0]), int(parts[1]), parts[2], parts[3]
                        # We need to find the action ID for this move.
                        # This is tricky because IDs are generated internally.
                        # HACK: We iterate legal actions to find the match.
                        legal = state.legal_actions()
                        
                        # Ensure map is populated
                        if not hasattr(state, "_current_move_map") or not state._current_move_map:
                            state._legal_actions(0)
                            
                        found = False
                        for aid in legal:
                            if aid >= 450: continue
                            m = state._current_move_map[aid]
                            if m['row'] == r and m['col'] == c and m['word'] == w:
                                action = aid
                                found = True
                                valid = True
                                break
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