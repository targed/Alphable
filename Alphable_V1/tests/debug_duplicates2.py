"""
Find remaining source of duplicates
"""
from structure import Gaddag, MoveGenerator
from collections import defaultdict

gaddag = Gaddag.load("resources/NWL2023.txt")
move_gen = MoveGenerator(gaddag)

board = [['.' for _ in range(15)] for _ in range(15)]
board[7][7] = 'N'

rack = ['A', 'N', 'D', 'E', 'T', 'S']
moves = move_gen.generate(board, rack)

# Group moves by signature
move_groups = defaultdict(list)
for i, move in enumerate(moves):
    sig = (move['row'], move['col'], move['dir'], move['word'])
    move_groups[sig].append(i)

# Find duplicates
duplicates = {sig: indices for sig, indices in move_groups.items() if len(indices) > 1}

print(f"Total moves: {len(moves)}")
print(f"Unique moves: {len(move_groups)}")
print(f"Duplicate signatures: {len(duplicates)}")

# Show some examples
print("\nFirst 10 duplicate signatures:")
for i, (sig, indices) in enumerate(list(duplicates.items())[:10]):
    row, col, direction, word = sig
    print(f"{i+1}. '{word}' at ({row},{col}) {direction} - {len(indices)} copies")

# Check if they're split between Across and Down
across_count = sum(1 for sig in duplicates.keys() if sig[2] == 'Across')
down_count = sum(1 for sig in duplicates.keys() if sig[2] == 'Down')
print(f"\nDuplicates by direction:")
print(f"  Across: {across_count}")
print(f"  Down: {down_count}")

# Check one specific case
if duplicates:
    sig, indices = list(duplicates.items())[0]
    row, col, direction, word = sig
    print(f"\nDetailed check for '{word}' at ({row},{col}) {direction}:")
    print(f"  Appears at indices: {indices}")
    
    # Are the move objects actually identical?
    first_move = moves[indices[0]]
    for idx in indices[1:]:
        if moves[idx] == first_move:
            print(f"  Index {idx}: IDENTICAL to first")
        else:
            print(f"  Index {idx}: DIFFERENT - {moves[idx]}")
