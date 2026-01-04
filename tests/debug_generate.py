"""
Debug - count moves before and after transpose
"""
from structure import Gaddag, MoveGenerator
import collections

# Load dictionary
gaddag = Gaddag.load("resources/NWL2023.txt")
move_gen = MoveGenerator(gaddag)

# Simple board with 'A' at center
board = [['.' for _ in range(15)] for _ in range(15)]
board[7][7] = 'A'

rack = ['N', 'D', 'E', 'R', 'S', 'T', 'X']
rack_counter = collections.Counter(rack)

# Generate ACROSS moves
across_moves = []
cross_checks = {}
move_gen._compute_cross_checks(board, cross_checks)
move_gen._find_moves(board, rack_counter, 'Across', across_moves, cross_checks)
print(f"ACROSS moves generated: {len(across_moves)}")
print("First 5 ACROSS moves:")
for m in across_moves[:5]:
    print(f"  {m}")

# Generate DOWN moves
board_T = [list(x) for x in zip(*board)]
down_moves = []
cross_checks_T = {}
move_gen._compute_cross_checks(board_T, cross_checks_T)
move_gen._find_moves(board_T, rack_counter, 'Down', down_moves, cross_checks_T)
print(f"\nDOWN moves generated (before coord swap): {len(down_moves)}")
print("First 5 DOWN moves (before swap):")
for m in down_moves[:5]:
    print(f"  {m}")

# Swap coordinates
for m in down_moves:
    m['row'], m['col'] = m['col'], m['row']
    
print(f"\nFirst 5 DOWN moves (after swap):")
for m in down_moves[:5]:
    print(f"  {m}")
    
# Check 'dir' field
print(f"\nDirection fields:")
print(f"  ACROSS moves have dir='{across_moves[0]['dir'] if across_moves else 'N/A'}'")
print(f"  DOWN moves have dir='{down_moves[0]['dir'] if down_moves else 'N/A'}'")

# Use full generate method
all_moves = move_gen.generate(board, rack)
across_count = len([m for m in all_moves if m['dir'] == 'Across'])
down_count = len([m for m in all_moves if m['dir'] == 'Down'])
print(f"\nUsing full generate() method:")
print(f"  Total: {len(all_moves)}")
print(f"  Across: {across_count}")
print(f"  Down: {down_count}")
