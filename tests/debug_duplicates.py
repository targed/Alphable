"""
Investigate duplicate moves
"""
from structure import Gaddag, MoveGenerator

gaddag = Gaddag.load("resources/NWL2023.txt")
move_gen = MoveGenerator(gaddag)

# Simple board
board = [['.' for _ in range(15)] for _ in range(15)]
board[7][7] = 'N'

rack = ['A', 'N', 'D', 'E', 'T', 'S']
moves = move_gen.generate(board, rack)

# Group moves by signature
from collections import defaultdict
move_groups = defaultdict(list)
for i, move in enumerate(moves):
    sig = (move['row'], move['col'], move['dir'], move['word'])
    move_groups[sig].append(i)

# Find duplicates
duplicates = {sig: indices for sig, indices in move_groups.items() if len(indices) > 1}

print(f"Total moves: {len(moves)}")
print(f"Duplicate signatures: {len(duplicates)}")
print(f"\nExamining duplicates for 'AN' at (7,6) Across:")

an_sig = (7, 6, 'Across', 'AN')
if an_sig in duplicates:
    indices = duplicates[an_sig]
    print(f"  Found {len(indices)} copies at indices: {indices}")
    print(f"  These are the actual move objects:")
    for idx in indices:
        print(f"    Index {idx}: {moves[idx]}")

# Check where these come from
print("\n" + "="*70)
print("Checking which anchors generate 'AN' at (7,6) Across")
print("="*70)

# Manually test with different anchors
import collections
rack_counter = collections.Counter(rack)

# Get anchors
anchors = move_gen._find_anchors(board)
print(f"\nAnchors found: {len(anchors)}")
print("Anchors around (7,6-8):")
for r, c in sorted(anchors):
    if 5 <= r <= 9 and 4 <= c <= 10:
        print(f"  ({r},{c}) - board[{r}][{c}] = '{board[r][c]}'")

# Generate from each anchor separately
cross_checks = {}
move_gen._compute_cross_checks(board, cross_checks)

for anchor_r, anchor_c in [(6, 7), (7, 6), (7, 7), (7, 8), (8, 7)]:
    if (anchor_r, anchor_c) in anchors:
        test_moves = []
        move_gen._gen_row_moves(board, anchor_r, anchor_c, rack_counter, 
                               gaddag.root, test_moves, cross_checks)
        
        # Check if 'AN' at (7,6) is in this set
        an_in_set = any(m['row'] == 7 and m['col'] == 6 and m['word'] == 'AN' 
                       for m in test_moves)
        print(f"\nAnchor ({anchor_r},{anchor_c}): {len(test_moves)} moves, " +
              f"includes AN@(7,6): {an_in_set}")
