"""
Test word extension in all directions

This tests whether the engine can:
1. Extend words to the right (CAN -> CANDY)
2. Extend words to the left (CAN -> TOUCAN)
3. Extend words on both sides (CAN -> JACANAS)
"""
from structure import Gaddag, MoveGenerator

gaddag = Gaddag.load("resources/NWL2023.txt")
move_gen = MoveGenerator(gaddag)

print("="*70)
print("TEST: WORD EXTENSION IN ALL DIRECTIONS")
print("="*70)

# Test with horizontal "CAN"
board_h = [['.' for _ in range(15)] for _ in range(15)]
for i, char in enumerate("CAN"):
    board_h[7][6+i] = char

print("\nBoard: CAN horizontal at row 7, cols 6-8")
print("  C(7,6) A(7,7) N(7,8)")

for r in range(5, 10):
    print(f"Row {r}: {' '.join(board_h[r][4:12])}")

# Rack with letters to make extensions
rack_h = ['D', 'Y', 'T', 'O', 'U', 'V', 'A', 'S']

moves_h = move_gen.generate(board_h, rack_h)
across_h = [m for m in moves_h if m['dir'] == 'Across' and m['row'] == 7]

print(f"\nGenerated {len(moves_h)} total moves, {len(across_h)} across row 7")

# Check for extensions
print("\n" + "="*70)
print("HORIZONTAL WORD EXTENSIONS:")
print("="*70)

# 1. Extend right: CAN -> CANDY
candy_moves = [m for m in across_h if m['word'] == 'CANDY' and m['col'] == 6]
print(f"\n1. Extend RIGHT (CAN -> CANDY):")
print(f"   Found: {len(candy_moves)} moves")
if candy_moves:
    for m in candy_moves:
        print(f"   ✓ CANDY at ({m['row']},{m['col']})")
else:
    print(f"   ✗ CANDY not found")

# 2. Extend left: CAN -> TOUCAN
toucan_moves = [m for m in across_h if m['word'] == 'TOUCAN']
print(f"\n2. Extend LEFT (CAN -> TOUCAN):")
print(f"   Found: {len(toucan_moves)} moves")
if toucan_moves:
    for m in toucan_moves:
        # Should start at col 4 (TOU at 4-6, then CAN at 6-8)
        print(f"   ✓ TOUCAN at ({m['row']},{m['col']})")
        if m['col'] == 4:
            print(f"      Correct: starts 2 positions before CAN")
        else:
            print(f"      WARNING: expected col 4, got col {m['col']}")
else:
    print(f"   ✗ TOUCAN not found")

# 3. Extend both: CAN -> VACANT
vacant_moves = [m for m in across_h if m['word'] == 'VACANT']
print(f"\n3. Extend BOTH (CAN -> VACANT):")
print(f"   Found: {len(vacant_moves)} moves")
if vacant_moves:
    for m in vacant_moves:
        # VA-CAN-T: should start at col 4 (VA at 4-5, CAN at 6-8, T at 9)
        print(f"   ✓ VACANT at ({m['row']},{m['col']})")
        if m['col'] == 4:
            print(f"      Correct: starts 2 positions before CAN")
        else:
            print(f"      WARNING: expected col 4, got col {m['col']}")
else:
    print(f"   ✗ VACANT not found")

# Also test with vertical word
print("\n\n" + "="*70)
print("VERTICAL WORD EXTENSIONS:")
print("="*70)

board_v = [['.' for _ in range(15)] for _ in range(15)]
for i, char in enumerate("CAN"):
    board_v[6+i][7] = char

print("\nBoard: CAN vertical at col 7, rows 6-8")
print("  C(6,7) A(7,7) N(8,7)")

for r in range(4, 11):
    print(f"Row {r}: {' '.join(board_v[r][5:10])}")

rack_v = ['D', 'Y', 'T', 'O', 'U', 'V', 'A', 'S']
moves_v = move_gen.generate(board_v, rack_v)
down_v = [m for m in moves_v if m['dir'] == 'Down' and m['col'] == 7]

print(f"\nGenerated {len(moves_v)} total moves, {len(down_v)} down col 7")

# 1. Extend down: CAN -> CANDY
candy_down = [m for m in down_v if m['word'] == 'CANDY' and m['row'] == 6]
print(f"\n1. Extend DOWN (CAN -> CANDY):")
print(f"   Found: {len(candy_down)} moves")
if candy_down:
    for m in candy_down:
        print(f"   ✓ CANDY at ({m['row']},{m['col']})")
else:
    print(f"   ✗ CANDY not found")

# 2. Extend up: CAN -> TOUCAN
toucan_down = [m for m in down_v if m['word'] == 'TOUCAN']
print(f"\n2. Extend UP (CAN -> TOUCAN):")
print(f"   Found: {len(toucan_down)} moves")
if toucan_down:
    for m in toucan_down:
        print(f"   ✓ TOUCAN at ({m['row']},{m['col']})")
        if m['row'] == 4:
            print(f"      Correct: starts 2 rows before CAN")
        else:
            print(f"      WARNING: expected row 4, got row {m['row']}")
else:
    print(f"   ✗ TOUCAN not found")

# 3. Extend both: CAN -> VACANT
vacant_down = [m for m in down_v if m['word'] == 'VACANT']
print(f"\n3. Extend BOTH (CAN -> VACANT):")
print(f"   Found: {len(vacant_down)} moves")
if vacant_down:
    for m in vacant_down:
        print(f"   ✓ VACANT at ({m['row']},{m['col']})")
        if m['row'] == 4:
            print(f"      Correct: starts 2 rows before CAN")
        else:
            print(f"      WARNING: expected row 4, got row {m['row']}")
else:
    print(f"   ✗ VACANT not found")

# Additional check: other extensions
print("\n" + "="*70)
print("OTHER POSSIBLE EXTENSIONS OF 'CAN':")
print("="*70)

# Find all words containing "CAN" as substring
can_extensions = [m for m in across_h if 'CAN' in m['word'] and len(m['word']) > 3]
can_extensions.sort(key=lambda x: len(x['word']))

print(f"\nFound {len(can_extensions)} horizontal words containing 'CAN':")
shown = set()
for m in can_extensions[:20]:
    if m['word'] not in shown:
        # Find where CAN appears in the word
        can_pos = m['word'].find('CAN')
        before = m['word'][:can_pos]
        after = m['word'][can_pos+3:]
        extension_type = []
        if before:
            extension_type.append(f"left:{before}")
        if after:
            extension_type.append(f"right:{after}")
        
        print(f"  {m['word']:15s} ({' + '.join(extension_type)})")
        shown.add(m['word'])

print("\n" + "="*70)
print("SUMMARY")
print("="*70)

results = {
    "Extend right (CANDY)": len(candy_moves) > 0,
    "Extend left (TOUCAN)": len(toucan_moves) > 0,
    "Extend both (VACANT)": len(vacant_moves) > 0,
    "Vertical extend down": len(candy_down) > 0,
    "Vertical extend up": len(toucan_down) > 0,
    "Vertical extend both": len(vacant_down) > 0,
}

for test, passed in results.items():
    status = "✓" if passed else "✗"
    print(f"{status} {test}")

if all(results.values()):
    print("\n✓ ALL TESTS PASSED: Engine supports word extension in all directions")
else:
    print("\n✗ SOME TESTS FAILED")
