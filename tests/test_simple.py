"""
Test with a simpler scenario - single letter on board
"""
from structure import Gaddag, MoveGenerator

# Load dictionary
gaddag = Gaddag.load("resources/NWL2023.txt")
move_gen = MoveGenerator(gaddag)

# Create board with just 'A' at center
board = [['.' for _ in range(15)] for _ in range(15)]
board[7][7] = 'A'

print("Simple board with just 'A' at (7,7):")
for r in range(5, 10):
    print(f"Row {r}: {' '.join(board[r][5:10])}")

# Rack with N and D
rack = ['N', 'D', 'E', 'R', 'S', 'T', 'X']

moves = move_gen.generate(board, rack)
print(f"\nTotal moves: {len(moves)}")

# Look for 'AND' going across (should use the A)
and_across = [m for m in moves if 'AND' in m['word'] and m['dir'] == 'Across']
print(f"\nMoves containing 'AND' going ACROSS: {len(and_across)}")
for m in and_across[:10]:
    print(f"  {m['word']:15s} at ({m['row']},{m['col']})")

# Look for 'AND' going down
and_down = [m for m in moves if 'AND' in m['word'] and m['dir'] == 'Down']
print(f"\nMoves containing 'AND' going DOWN: {len(and_down)}")
for m in and_down[:10]:
    print(f"  {m['word']:15s} at ({m['row']},{m['col']})")

# Check if we can extend FROM the A
extends_a = [m for m in moves if m['row'] == 7 and m['col'] <= 7 and m['col'] + len(m['word']) > 7 and m['dir'] == 'Across']
print(f"\nMoves on row 7 that include position 7 (the 'A'): {len(extends_a)}")
for m in extends_a[:15]:
    print(f"  {m['word']:15s} at ({m['row']},{m['col']})")
