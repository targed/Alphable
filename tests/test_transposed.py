"""
Directly test move generation on transposed board
"""
from structure import Gaddag, MoveGenerator

# Load dictionary
gaddag = Gaddag.load("resources/NWL2023.txt")
move_gen = MoveGenerator(gaddag)

# Create transposed board with just 'A' at (7,7)
board_T = [['.' for _ in range(15)] for _ in range(15)]
board_T[7][7] = 'A'

print("Transposed board with 'A' at (7,7):")
for r in range(5, 10):
    print(f"Row {r}: {' '.join(board_T[r][5:10])}")

# Same rack
rack = ['N', 'D', 'E', 'R', 'S', 'T', 'X']

# Generate moves on the transposed board (these will be labeled 'Across' but are really 'Down')
cross_checks = {}
move_gen._compute_cross_checks(board_T, cross_checks)
anchors = move_gen._find_anchors(board_T)

print(f"\nAnchors found: {len(anchors)}")
print("Anchors around (7,7):")
for r, c in sorted(anchors):
    if 5 <= r <= 9 and 5 <= c <= 9:
        print(f"  ({r},{c}) - board_T[{r}][{c}] = '{board_T[r][c]}'")

# Generate moves
moves = []
import collections
rack_counter = collections.Counter(rack)

for r, c in anchors:
    move_gen._gen_row_moves(board_T, r, c, rack_counter, gaddag.root, moves, cross_checks)

print(f"\nTotal moves generated: {len(moves)}")

# Look for moves on row 7
row_7_moves = [m for m in moves if m['row'] == 7]
print(f"\nMoves on row 7: {len(row_7_moves)}")
for m in row_7_moves[:20]:
    print(f"  {m['word']:15s} at ({m['row']},{m['col']}) - spans cols {m['col']} to {m['col']+len(m['word'])-1}")
