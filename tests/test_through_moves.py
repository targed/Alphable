"""
Test specifically for moves going THROUGH existing words
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

print("Board with 'PANDA' at row 7, columns 5-9:")
for r in range(4, 11):
    print(f"Row {r:2d}: " + ' '.join(board[r]))

# Test rack
rack = ['A', 'N', 'D', 'E', 'R', 'S', 'T']
print(f"\nRack: {rack}")

# Generate moves
moves = move_gen.generate(board, rack)
print(f"\nTotal moves generated: {len(moves)}")

# Look specifically for DOWN moves that use letters from PANDA
print("\n" + "="*70)
print("DOWN MOVES THAT GO THROUGH 'PANDA':")
print("="*70)

# PANDA is at row 7, cols 5-9
# P at (7,5), A at (7,6), N at (7,7), D at (7,8), A at (7,9)

down_through_moves = []
for move in moves:
    if move['dir'] == 'Down':
        row, col = move['row'], move['col']
        word = move['word']
        
        # Check if this move intersects with PANDA at row 7
        # Move goes from (row, col) to (row + len(word) - 1, col)
        
        if row <= 7 <= row + len(word) - 1:
            # This move spans row 7
            if 5 <= col <= 9:  # And it's in a PANDA column
                panda_letter = ['P', 'A', 'N', 'D', 'A'][col - 5]
                # What position in the new word is at row 7?
                pos_in_word = 7 - row
                if word[pos_in_word] == panda_letter:
                    down_through_moves.append((move, panda_letter, col))

print(f"Found {len(down_through_moves)} DOWN moves going through PANDA")

# Show examples
for i, (move, letter, col_num) in enumerate(down_through_moves[:20]):
    col_letter = chr(ord('A') + col_num)
    print(f"{i+1:3d}. '{move['word']:12s}' at ({move['row']:2d},{move['col']:2d}) uses '{letter}' from PANDA col {col_letter}")

# Specifically look for "AND" going down through letters
print("\n" + "="*70)
print("Looking for 'AND' going DOWN:")
print("="*70)

and_down = [m for m in moves if m['word'] == 'AND' and m['dir'] == 'Down']
print(f"Found {len(and_down)} instances of 'AND' going DOWN")

for move in and_down:
    row, col = move['row'], move['col']
    print(f"  AND at ({row},{col}) Down - spans rows {row} to {row+2}")
    
    # Check what it overlaps with
    for i in range(3):
        r = row + i
        if 0 <= r < 15 and board[r][col] != '.':
            print(f"    Position {i} ('{['A','N','D'][i]}'): uses existing '{board[r][col]}' at row {r}")

# Look for words using 'A' from position 6 (second letter of PANDA)
print("\n" + "="*70)
print("DOWN moves using 'A' at column 6 (second letter of PANDA):")
print("="*70)
col_6_down = [m for m in moves if m['dir'] == 'Down' and m['col'] == 6]
through_col_6 = []
for move in col_6_down:
    row = move['row']
    if row <= 7 <= row + len(move['word']) - 1:
        pos = 7 - row
        if move['word'][pos] == 'A':
            through_col_6.append(move)

print(f"Found {len(through_col_6)} moves")
for i, move in enumerate(through_col_6[:10]):
    print(f"{i+1}. '{move['word']:12s}' at ({move['row']:2d},{move['col']:2d})")
