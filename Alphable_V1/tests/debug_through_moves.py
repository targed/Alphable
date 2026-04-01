"""
Debug the move generation to see why through-moves aren't working
"""
from structure import Gaddag, MoveGenerator

# Load dictionary
gaddag = Gaddag.load("resources/NWL2023.txt")

# Manually check if "AND" is in the dictionary
print("Testing GADDAG lookups:")
print(f"  'AND' in dictionary: {gaddag.root.get('D', {}).get('N', {}).get('A', {}).get('>', {}).get('$', False)}")

# Create a simple board with "PANDA" horizontally at row 7
board = [['.' for _ in range(15)] for _ in range(15)]
word = "PANDA"
start_col = 5
for i, char in enumerate(word):
    board[7][start_col + i] = char

print("\nBoard (showing rows 5-9):")
for r in range(5, 10):
    row_str = ' '.join(board[r])
    print(f"Row {r}: {row_str}")

# Transpose to check DOWN generation
board_T = [list(x) for x in zip(*board)]
print("\nTransposed board (what DOWN move generator sees) - showing rows 5-9:")
for r in range(5, 10):
    row_str = ' '.join(board_T[r])
    print(f"Col {r}: {row_str}")

# Check anchors
move_gen = MoveGenerator(gaddag)
anchors = move_gen._find_anchors(board_T)
print(f"\nAnchors found on transposed board: {len(anchors)}")
print("Anchors in columns 5-9 (where PANDA letters are):")
for r, c in sorted(anchors):
    if 5 <= r <= 9:
        print(f"  ({r},{c})")

# Check specifically column 6 (which has 'A' from PANDA)
col_6_anchors = [(r, c) for r, c in anchors if r == 6]
print(f"\nAnchors in column 6: {len(col_6_anchors)}")
if col_6_anchors:
    print("  Examples:", col_6_anchors[:10])
