"""
Test if engine can generate ACROSS moves through a VERTICAL word
"""
from structure import Gaddag, MoveGenerator

# Load dictionary
gaddag = Gaddag.load("resources/NWL2023.txt")
move_gen = MoveGenerator(gaddag)

# Create board with "PANDA" VERTICALLY at column 7, rows 5-9
board = [['.' for _ in range(15)] for _ in range(15)]
word = "PANDA"
start_row = 5
col = 7
for i, char in enumerate(word):
    board[start_row + i][col] = char

print("Board with 'PANDA' placed VERTICALLY at column 7, rows 5-9:")
print("  P at (5,7)")
print("  A at (6,7)")
print("  N at (7,7)")
print("  D at (8,7)")
print("  A at (9,7)")

print("\nBoard visualization (rows 4-11, cols 5-10):")
for r in range(4, 11):
    row_str = ' '.join(board[r][5:11])
    print(f"Row {r:2d}: {row_str}")

# Test rack
rack = ['A', 'N', 'D', 'E', 'R', 'S', 'T']
print(f"\nRack: {rack}")

# Generate moves
moves = move_gen.generate(board, rack)
print(f"\nTotal moves generated: {len(moves)}")

# Count by direction
across_moves = [m for m in moves if m['dir'] == 'Across']
down_moves = [m for m in moves if m['dir'] == 'Down']
print(f"  Across: {len(across_moves)}")
print(f"  Down: {len(down_moves)}")

print("\n" + "="*70)
print("ACROSS MOVES THAT GO THROUGH 'PANDA':")
print("="*70)

# PANDA is at column 7, rows 5-9
# P at (5,7), A at (6,7), N at (7,7), D at (8,7), A at (9,7)

across_through_moves = []
for move in across_moves:
    row, col = move['row'], move['col']
    word_len = len(move['word'])
    
    # Check if this move spans column 7 (where PANDA is)
    if col <= 7 <= col + word_len - 1:
        # This move includes column 7
        # Check which PANDA letter it intersects
        for panda_row in range(5, 10):
            if row == panda_row:
                panda_letter = ['P', 'A', 'N', 'D', 'A'][panda_row - 5]
                # What position in the new word is at column 7?
                pos_in_word = 7 - col
                if move['word'][pos_in_word] == panda_letter:
                    across_through_moves.append((move, panda_letter, panda_row))
                    break

print(f"Found {len(across_through_moves)} ACROSS moves going through PANDA")

# Show examples
for i, (move, letter, row_num) in enumerate(across_through_moves[:20]):
    print(f"{i+1:3d}. '{move['word']:12s}' at ({move['row']:2d},{move['col']:2d}) uses '{letter}' from PANDA row {row_num}")

# Specifically look for "AND" going across through letters
print("\n" + "="*70)
print("Looking for 'AND' going ACROSS:")
print("="*70)

and_across = [m for m in moves if m['word'] == 'AND' and m['dir'] == 'Across']
print(f"Found {len(and_across)} instances of 'AND' going ACROSS")

for move in and_across:
    row, col = move['row'], move['col']
    print(f"  AND at ({row},{col}) Across - spans cols {col} to {col+2}")
    
    # Check what it overlaps with
    for i in range(3):
        c = col + i
        if 0 <= c < 15 and board[row][c] != '.':
            print(f"    Position {i} ('{['A','N','D'][i]}'): uses existing '{board[row][c]}' at column {c}")

# Look for words using 'A' from position 6 (second letter of PANDA)
print("\n" + "="*70)
print("ACROSS moves using 'A' at row 6 (second letter of PANDA):")
print("="*70)
row_6_across = [m for m in moves if m['dir'] == 'Across' and m['row'] == 6]
through_row_6 = []
for move in row_6_across:
    col_start = move['col']
    if col_start <= 7 <= col_start + len(move['word']) - 1:
        pos = 7 - col_start
        if move['word'][pos] == 'A':
            through_row_6.append(move)

print(f"Found {len(through_row_6)} moves")
for i, move in enumerate(through_row_6[:10]):
    print(f"{i+1}. '{move['word']:12s}' at ({move['row']:2d},{move['col']:2d})")

# Also check: Can we extend the vertical word itself?
print("\n" + "="*70)
print("DOWN moves that extend or overlap with vertical PANDA:")
print("="*70)

extending_down = []
for move in down_moves:
    row, col = move['row'], move['col']
    word_len = len(move['word'])
    
    # Check if it's at column 7 and overlaps with rows 5-9
    if col == 7:
        move_rows = set(range(row, row + word_len))
        panda_rows = set(range(5, 10))
        if move_rows & panda_rows:  # If there's overlap
            extending_down.append(move)

print(f"Found {len(extending_down)} DOWN moves at column 7 that overlap PANDA")
for i, move in enumerate(extending_down[:10]):
    print(f"{i+1}. '{move['word']:12s}' at ({move['row']:2d},{move['col']:2d}) - rows {move['row']} to {move['row']+len(move['word'])-1}")
