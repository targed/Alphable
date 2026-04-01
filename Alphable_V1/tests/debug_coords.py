"""
More detailed debugging - trace through what should happen for "AND" through 'A'
"""
from structure import Gaddag, MoveGenerator
import collections

# Load dictionary
gaddag = Gaddag.load("resources/NWL2023.txt")

# Create board with "PANDA" at row 7, cols 5-9
board = [['.' for _ in range(15)] for _ in range(15)]
word = "PANDA"
start_col = 5
for i, char in enumerate(word):
    board[7][start_col + i] = char

print("Original board - PANDA at row 7, cols 5-9:")
print("  P at (7,5)")
print("  A at (7,6)")  
print("  N at (7,7)")
print("  D at (7,8)")
print("  A at (7,9)")

# When we transpose for DOWN moves:
# - Original (row, col) becomes (col, row) in transposed
# - So 'A' at (7,6) becomes (6,7) in transposed board

board_T = [list(x) for x in zip(*board)]

print("\nTransposed board - column 6 becomes row 6:")
print(f"Row 6: {' '.join(board_T[6])}")
print(f"  Position 7 in this row: '{board_T[6][7]}'")

# To play "AND" down through 'A' at original (7,6):
# We want the word to start at (5,6) or (6,6) and go to (7,6) or beyond
# In the transposed board, this becomes:
# Start at (6,5) or (6,6) going across

print("\nFor 'AND' going DOWN using 'A' at original position (7,6):")
print("  In transposed coords, 'A' is at (6,7)")
print("  We need to generate a move in row 6 that includes position 7")
print("  Possible starts: col 5, 6, or 7")

# Check if we have anchors at (6, anything <= 7)
move_gen = MoveGenerator(gaddag)
anchors = move_gen._find_anchors(board_T)
print(f"\nAnchors in row 6 of transposed board:")
row_6_anchors = [(r, c) for r, c in anchors if r == 6]
print(f"  Found {len(row_6_anchors)} anchors in row 6")
for r, c in sorted(row_6_anchors):
    print(f"    Anchor at (6, {c})")

# The issue: We need an anchor at (6, 5), (6, 6), or (6, 7)
# to start a word that will include the 'A' at (6, 7)

if (6, 7) in anchors:
    print("\n  ✓ We have anchor at (6,7) - the 'A' position itself")
else:
    print("\n  ✗ NO anchor at (6,7) - the 'A' position itself!")
    print("     This is the problem!")
    
# Check what happens - board_T[6][7] should be 'A'
print(f"\nboard_T[6][7] = '{board_T[6][7]}'")
print("This square is NOT empty, so it won't be an anchor!")
print("\nThe algorithm skips tiles that already have letters when finding anchors.")
print("We need anchors BEFORE the existing tile to start words that go through it.")
