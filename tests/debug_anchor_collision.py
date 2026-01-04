"""
Check which anchors produce the same moves
"""
from structure import Gaddag, MoveGenerator
import collections

gaddag = Gaddag.load("resources/NWL2023.txt")
move_gen = MoveGenerator(gaddag)

# Transposed board for DOWN moves (since duplicates are in DOWN)
board_T = [['.' for _ in range(15)] for _ in range(15)]
board_T[7][7] = 'N'

print("Transposed board (for DOWN move generation):")
for r in range(5, 10):
    print(f"Row {r}: {' '.join(board_T[r][5:10])}")

rack = ['A', 'N', 'D', 'E', 'T', 'S']
rack_counter = collections.Counter(rack)

# Get anchors
anchors = move_gen._find_anchors(board_T)
print(f"\nAnchors: {len(anchors)}")
for r, c in sorted(anchors):
    if 5 <= r <= 9 and 5 <= c <= 9:
        print(f"  ({r},{c})")

# Generate moves from each anchor
cross_checks = {}
move_gen._compute_cross_checks(board_T, cross_checks)

# Test specifically for "AND" at (6,7)
# After transpose, this becomes "AND" Down at (7,6) in original coords
print("\nChecking which anchors generate 'AND' at (6,7) on transposed board:")

for r, c in anchors:
    if 5 <= r <= 9 and 5 <= c <= 9:
        moves_from_anchor = []
        move_gen._gen_row_moves(board_T, r, c, rack_counter, gaddag.root, 
                               moves_from_anchor, cross_checks)
        
        # Check for "AND" at (6,7)
        and_moves = [m for m in moves_from_anchor if m['word'] == 'AND' and 
                     m['row'] == 6 and m['col'] == 7]
        
        if and_moves:
            print(f"  Anchor ({r},{c}): YES - generates {len(and_moves)} instance(s)")

# Check if the issue is that multiple positions in row 7 can be anchors
print("\nAll anchors in row 7:")
row7_anchors = [(r, c) for r, c in anchors if r == 7]
print(f"  Found {len(row7_anchors)} anchors in row 7: {row7_anchors}")

# The 'N' is at (7,7), and we have anchors at (7,6) and (7,8)
# Both might be able to generate the same word
