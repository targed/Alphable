"""
Additional edge case tests for move generation
"""
from structure import Gaddag, MoveGenerator

gaddag = Gaddag.load("resources/NWL2023.txt")
move_gen = MoveGenerator(gaddag)

print("="*70)
print("TEST 1: Multiple horizontal words, can we play vertical through them?")
print("="*70)

# Create board with two horizontal words
board1 = [['.' for _ in range(15)] for _ in range(15)]
# CAT at row 5, cols 6-8
for i, char in enumerate("CAT"):
    board1[5][6+i] = char
# DOG at row 8, cols 6-8
for i, char in enumerate("DOG"):
    board1[8][6+i] = char

print("\nBoard:")
for r in range(4, 10):
    print(f"Row {r:2d}: {' '.join(board1[r][5:10])}")

rack = ['A', 'N', 'D', 'E', 'R', 'S', 'T', 'O', 'U']
moves1 = move_gen.generate(board1, rack)
down_moves1 = [m for m in moves1 if m['dir'] == 'Down']

# Look for words going down through column 6 (which has C and D)
col_6_down = [m for m in down_moves1 if m['col'] == 6]
# Filter for ones that use both C and D
through_both = []
for move in col_6_down:
    row_start = move['row']
    word = move['word']
    # Check if it spans both row 5 and row 8
    if row_start <= 5 and row_start + len(word) - 1 >= 8:
        # Check if it uses C at position (5 - row_start) and D at position (8 - row_start)
        c_pos = 5 - row_start
        d_pos = 8 - row_start
        if 0 <= c_pos < len(word) and 0 <= d_pos < len(word):
            if word[c_pos] == 'C' and word[d_pos] == 'D':
                through_both.append(move)

print(f"\nDown moves through BOTH words (using C and D): {len(through_both)}")
for m in through_both[:5]:
    print(f"  {m['word']:15s} at ({m['row']},{m['col']})")

print("\n" + "="*70)
print("TEST 2: Corner/edge positions")
print("="*70)

# Word at top edge
board2 = [['.' for _ in range(15)] for _ in range(15)]
for i, char in enumerate("STAR"):
    board2[0][5+i] = char

rack2 = ['A', 'T', 'E', 'R', 'S', 'N', 'D']
moves2 = move_gen.generate(board2, rack2)
down_moves2 = [m for m in moves2 if m['dir'] == 'Down']

# Can we play down through STAR starting from row 0?
col_5_down = [m for m in down_moves2 if m['col'] == 5 and m['row'] == 0]
print(f"\nDown moves starting at (0,5) going through 'S': {len(col_5_down)}")
for m in col_5_down[:5]:
    print(f"  {m['word']:15s}")

print("\n" + "="*70)
print("TEST 3: Single letter in middle, play both directions through it")
print("="*70)

board3 = [['.' for _ in range(15)] for _ in range(15)]
board3[7][7] = 'N'

rack3 = ['A', 'N', 'D', 'E', 'T', 'S']
moves3 = move_gen.generate(board3, rack3)

# Find ANTS going across (using the N)
ants_across = [m for m in moves3 if m['word'] == 'ANTS' and m['dir'] == 'Across']
# Find ANTS going down (using the N)
ants_down = [m for m in moves3 if m['word'] == 'ANTS' and m['dir'] == 'Down']

print(f"\nCan play 'ANTS' across using the 'N': {len(ants_across) > 0}")
if ants_across:
    for m in ants_across[:3]:
        print(f"  at ({m['row']},{m['col']})")

print(f"\nCan play 'ANTS' down using the 'N': {len(ants_down) > 0}")
if ants_down:
    for m in ants_down[:3]:
        print(f"  at ({m['row']},{m['col']})")

print("\n" + "="*70)
print("TEST 4: Verify no duplicate moves")
print("="*70)

# Check for duplicates in move list
move_signatures = set()
duplicates = []
for move in moves3:
    sig = (move['row'], move['col'], move['dir'], move['word'])
    if sig in move_signatures:
        duplicates.append(move)
    move_signatures.add(sig)

print(f"Total moves: {len(moves3)}")
print(f"Unique signatures: {len(move_signatures)}")
print(f"Duplicates found: {len(duplicates)}")
if duplicates:
    print("First few duplicates:")
    for m in duplicates[:5]:
        print(f"  {m}")

print("\n" + "="*70)
print("TEST 5: Cross-checks work in both directions")
print("="*70)

# Create a T-shape: CAT horizontal, T at center also starts TEN vertical
board5 = [['.' for _ in range(15)] for _ in range(15)]
# CAT at row 7, cols 6-8
for i, char in enumerate("CAT"):
    board5[7][6+i] = char
# EN going down from row 8, col 8 (sharing the T)
board5[8][8] = 'E'
board5[9][8] = 'N'

print("\nBoard with CAT (horizontal) and TEN (vertical) sharing 'T':")
for r in range(6, 11):
    print(f"Row {r:2d}: {' '.join(board5[r][5:11])}")

rack5 = ['S', 'D', 'R', 'A', 'O', 'U', 'I']
moves5 = move_gen.generate(board5, rack5)

# Try to extend CAT to CATS (should work)
cats_moves = [m for m in moves5 if m['word'] == 'CATS']
print(f"\nCan extend CAT to CATS: {len(cats_moves) > 0}")

# Try to extend TEN to TENS (should work)
tens_moves = [m for m in moves5 if m['word'] == 'TENS']
print(f"Can extend TEN to TENS: {len(tens_moves) > 0}")

# Try to play a word across row 8 using the E
row8_across = [m for m in moves5 if m['dir'] == 'Across' and m['row'] == 8 and 
               m['col'] <= 8 < m['col'] + len(m['word'])]
print(f"\nAcross moves on row 8 through the 'E': {len(row8_across)}")
for m in row8_across[:5]:
    print(f"  {m['word']:15s} at ({m['row']},{m['col']})")
