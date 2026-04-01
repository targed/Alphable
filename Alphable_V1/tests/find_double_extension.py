"""
Find a word that extends CAN on both sides
"""
from structure import Gaddag, MoveGenerator

gaddag = Gaddag.load("resources/NWL2023.txt")
move_gen = MoveGenerator(gaddag)

board = [['.' for _ in range(15)] for _ in range(15)]
for i, char in enumerate("CAN"):
    board[7][6+i] = char

# Use a larger rack with more letters
rack = list("ABDEGHIOSTUVWXYZ")
moves = move_gen.generate(board, rack)

across_7 = [m for m in moves if m['dir'] == 'Across' and m['row'] == 7]

# Find words that extend CAN on both sides
both_sides = []
for m in across_7:
    word = m['word']
    col = m['col']
    
    # CAN is at cols 6-8
    # If the word starts before 6 and ends after 8, it extends both sides
    word_end_col = col + len(word) - 1
    
    if col < 6 and word_end_col > 8 and 'CAN' in word:
        # Verify CAN is actually at positions 6-8
        can_start_in_word = 6 - col
        if can_start_in_word >= 0 and can_start_in_word + 3 <= len(word):
            if word[can_start_in_word:can_start_in_word+3] == 'CAN':
                both_sides.append(m)

print(f"Words that extend CAN on BOTH sides: {len(both_sides)}")
for m in both_sides[:10]:
    word = m['word']
    col = m['col']
    can_start = 6 - col
    before = word[:can_start]
    after = word[can_start+3:]
    print(f"  {word:15s} at col {col}: {before}-CAN-{after}")

if not both_sides:
    print("\nNo words found that extend on both sides!")
    print("\nLet me search the dictionary for any words with pattern *CAN*")
    print("where there are letters both before and after CAN...")
    
    # Try some common patterns
    test_words = ['SCANDAL', 'SCANT', 'VACANT', 'DECANT', 'RECANT', 
                  'CANTO', 'CANTOS', 'SCANTY', 'SCANTS']
    
    for test in test_words:
        # Check if in dictionary
        path = test[::-1] + ">"
        curr = gaddag.root
        valid = True
        for char in path:
            if char not in curr:
                valid = False
                break
            curr = curr[char]
        
        if valid and '$' in curr:
            can_pos = test.find('CAN')
            if can_pos > 0 and can_pos + 3 < len(test):
                before = test[:can_pos]
                after = test[can_pos+3:]
                print(f"  ✓ {test:15s} in dict: {before}-CAN-{after}")

# Let's try a different test with a word I know extends both ways
print("\n" + "="*70)
print("Testing with a known double-extension word: SCANT")
print("="*70)

board2 = [['.' for _ in range(15)] for _ in range(15)]
for i, char in enumerate("CAN"):
    board2[7][7+i] = char  # CAN at cols 7-9

print("\nBoard: CAN at cols 7-9")
for r in range(6, 9):
    print(f"Row {r}: {' '.join(board2[r][5:12])}")

rack2 = list("STYX")
moves2 = move_gen.generate(board2, rack2)
across_72 = [m for m in moves2 if m['dir'] == 'Across' and m['row'] == 7]

scant_moves = [m for m in across_72 if m['word'] == 'SCANT']
print(f"\nLooking for SCANT (S-CAN-T): {len(scant_moves)} found")
if scant_moves:
    for m in scant_moves:
        print(f"  ✓ SCANT at ({m['row']},{m['col']})")
        if m['col'] == 6:
            print(f"    Correct: starts at col 6 (one before CAN)")
else:
    print(f"  ✗ SCANT not found")
    
    # Check what words we DO find
    print(f"\nAll words found on row 7: {len(across_72)}")
    for m in across_72[:15]:
        print(f"  {m['word']:15s} at col {m['col']}")
