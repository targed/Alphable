"""
Check if anchors list contains duplicates
"""
from structure import Gaddag, MoveGenerator

gaddag = Gaddag.load("resources/NWL2023.txt")
move_gen = MoveGenerator(gaddag)

board_T = [['.' for _ in range(15)] for _ in range(15)]
board_T[7][7] = 'N'

anchors = move_gen._find_anchors(board_T)

print(f"Anchors list length: {len(anchors)}")
print(f"Unique anchors: {len(set(anchors))}")

if len(anchors) != len(set(anchors)):
    print("\nDUPLICATE ANCHORS FOUND!")
    from collections import Counter
    anchor_counts = Counter(anchors)
    for anchor, count in anchor_counts.items():
        if count > 1:
            print(f"  {anchor}: appears {count} times")
else:
    print("No duplicate anchors")

print(f"\nAll anchors:")
for a in sorted(anchors):
    print(f"  {a}")
