"""
Debug why JACANAS doesn't work
"""
from structure import Gaddag, MoveGenerator

gaddag = Gaddag.load("resources/NWL2023.txt")

# Check if JACANAS is in the dictionary
print("Checking dictionary for JACANAS...")
path = "SANACAJ"[::-1] + ">"
curr = gaddag.root
valid = True
for char in path:
    if char not in curr:
        print(f"  Failed at character '{char}'")
        valid = False
        break
    curr = curr[char]

if valid and '$' in curr:
    print("  ✓ JACANAS is in the dictionary")
else:
    print("  ✗ JACANAS is NOT in the dictionary")

# Try JACANA (singular)
print("\nChecking dictionary for JACANA...")
path2 = "ANACAJ"[::-1] + ">"
curr2 = gaddag.root
valid2 = True
for char in path2:
    if char not in curr2:
        print(f"  Failed at character '{char}'")
        valid2 = False
        break
    curr2 = curr2[char]

if valid2 and '$' in curr2:
    print("  ✓ JACANA is in the dictionary")
else:
    print("  ✗ JACANA is NOT in the dictionary")

# Check what words start with JA and contain CAN
print("\nSearching for words that match *JA*CAN*...")
move_gen = MoveGenerator(gaddag)

board = [['.' for _ in range(15)] for _ in range(15)]
for i, char in enumerate("CAN"):
    board[7][6+i] = char

# Rack with all letters
rack = list("JASDYOTU")
moves = move_gen.generate(board, rack)

across_7 = [m for m in moves if m['dir'] == 'Across' and m['row'] == 7]

# Find words that start with J
j_words = [m for m in across_7 if m['word'].startswith('J') and 'CAN' in m['word']]
print(f"Found {len(j_words)} words starting with J and containing CAN:")
for m in j_words[:10]:
    print(f"  {m['word']:15s} at ({m['row']},{m['col']})")

# Find any 7-letter words containing CAN
seven_letter = [m for m in across_7 if len(m['word']) == 7 and 'CAN' in m['word']]
print(f"\nFound {len(seven_letter)} 7-letter words containing CAN:")
for m in seven_letter[:10]:
    can_pos = m['word'].find('CAN')
    before = m['word'][:can_pos]
    after = m['word'][can_pos+3:]
    print(f"  {m['word']:15s} ({before}-CAN-{after})")

# Check if the issue is that we need to use existing tiles
print("\n" + "="*70)
print("Understanding the extension mechanism...")
print("="*70)
print("\nFor JACANAS (JA-CAN-AS):")
print("  - Existing on board: CAN at cols 6-8")
print("  - Need to place: J at col 4, A at col 5, A at col 9, S at col 10")
print("  - Total word spans: cols 4-10 (7 letters)")

# Manually check if this move is being generated
jacanas_any = [m for m in moves if m['word'] == 'JACANAS']
print(f"\nSearching ALL moves for JACANAS: {len(jacanas_any)} found")
if jacanas_any:
    for m in jacanas_any:
        print(f"  {m['word']} at ({m['row']},{m['col']}) {m['dir']}")
