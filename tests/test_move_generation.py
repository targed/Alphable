"""
Test to see what kinds of moves are being generated
"""
from structure import Gaddag, MoveGenerator

# Load dictionary
gaddag = Gaddag.load("resources/NWL2023.txt")
move_gen = MoveGenerator(gaddag)

# Create a simple board with "PANDA" horizontally at row 7
board = [['.' for _ in range(15)] for _ in range(15)]
word = "PANDA"
start_col = 5
for i, char in enumerate(word):
    board[7][start_col + i] = char

# Print board
print("Board:")
for r in range(15):
    print(' '.join(board[r]))

# Test rack with letters A, N, D
rack = ['A', 'N', 'D', 'E', 'R', 'S', 'T']

# Generate moves
moves = move_gen.generate(board, rack)

print(f"\nGenerated {len(moves)} moves")
print("\nLooking for moves that go THROUGH 'PANDA':")
print("=" * 60)

# Filter for moves that use existing letters
through_moves = []
for move in moves:
    row, col = move['row'], move['col']
    direction = move['dir']
    word = move['word']
    
    # Check if this move goes through existing tiles
    dr, dc = (0, 1) if direction == 'Across' else (1, 0)
    curr_r, curr_c = row, col
    uses_existing = False
    
    for char in word:
        if 0 <= curr_r < 15 and 0 <= curr_c < 15:
            if board[curr_r][curr_c] != '.':
                uses_existing = True
                break
        curr_r += dr
        curr_c += dc
    
    if uses_existing:
        through_moves.append(move)

print(f"Found {len(through_moves)} moves that go through existing tiles")

# Show some examples
for i, move in enumerate(through_moves[:20]):
    print(f"{i+1}. {move['word']:15s} at ({move['row']:2d},{move['col']:2d}) {move['dir']:6s}")

print("\n\nLooking specifically for 'AND' using letters from 'PANDA':")
print("=" * 60)
and_moves = [m for m in moves if m['word'] == 'AND']
for move in and_moves:
    print(f"  {move['word']} at ({move['row']},{move['col']}) {move['dir']}")
    
    # Check what it uses
    row, col = move['row'], move['col']
    direction = move['dir']
    dr, dc = (0, 1) if direction == 'Across' else (1, 0)
    
    for i, char in enumerate(move['word']):
        r = row + i * dr
        c = col + i * dc
        if board[r][c] != '.':
            print(f"    Uses existing '{board[r][c]}' at position {i}")

print("\n\nAll moves (first 30):")
print("=" * 60)
for i, move in enumerate(moves[:30]):
    print(f"{i+1}. {move['word']:15s} at ({move['row']:2d},{move['col']:2d}) {move['dir']:6s}")
