import re
import sys
import copy
from alphable.core import structure, simulator, inference
from alphable.core.search import AlphableSearch

def parse_pos(pos):
    match_down = re.match(r"^([A-O])(\d+)$", pos)
    if match_down:
        col = ord(match_down.group(1)) - ord('A')
        row = int(match_down.group(2)) - 1
        return row, col, 'Down'
    match_across = re.match(r"^(\d+)([A-O])$", pos)
    if match_across:
        row = int(match_across.group(1)) - 1
        col = ord(match_across.group(2)) - ord('A')
        return row, col, 'Across'
    return None, None, None

def main():
    print("Loading Gaddag...")
    gaddag = structure.Gaddag.load("resources/CSW24.txt")
    engine = inference.AlphableInference(
        model_path="models/alphable_v3_rl_gen4.pth",
        device="cuda",
        dict_path="resources/CSW24.txt",
        value_weight=25.0,
        state_vector_size=63
    )
    search = AlphableSearch(
        engine,
        num_simulations=10,
        top_k_candidates=5,
        mode="lookahead",
        enable_2ply=True,
        two_ply_threshold=8.0
    )

    board = simulator.create_empty_board()
    
    # Moves in dZHivErkZo up to turn 4:
    # 1. OURIE at 8D
    r, c, d = parse_pos("8D")
    board, _, _ = simulator.simulate_move(board, {"row": r, "col": c, "dir": d, "word": "OURIE"}, list("OURIE"))
    
    # 2. UME at 7F
    r, c, d = parse_pos("7F")
    board, _, _ = simulator.simulate_move(board, {"row": r, "col": c, "dir": d, "word": "UME"}, list("UME"))
    
    # 3. eTHANOL at C7 (blank e)
    r, c, d = parse_pos("C7")
    board, _, _ = simulator.simulate_move(board, {"row": r, "col": c, "dir": d, "word": "eTHANOL"}, list("?THANOL"))

    print("\nBoard after 3 moves:")
    for row in board:
        print(" ".join(row))

    rack = list("AEIINRT")
    score_diff = 19 - 94 # -75
    bag = 82

    print(f"\nGenerating moves for rack {rack}...")
    moves = engine.move_gen.generate(board, rack)
    print(f"Total legal moves generated: {len(moves)}")

    # Check for INERTIA
    inertia_moves = [m for m in moves if "INERTIA" in m["word"].upper()]
    print(f"INERTIA plays found in legal moves: {len(inertia_moves)}")
    for m in inertia_moves:
        print(f"  {m['word']} at ({m['row']},{m['col']}) {m['dir']}")

    # Let's see what find_best_move selects!
    best_move, best_val = search.find_best_move(board, rack, score_diff, bag)
    print(f"\nSearch chose best move: {best_move['word']} at ({best_move['row']},{best_move['col']}) {best_move['dir']}")

if __name__ == '__main__':
    main()
