"""
Check if the issue is in the generate() method
"""
from structure import Gaddag, MoveGenerator
import collections

gaddag = Gaddag.load("resources/NWL2023.txt")
move_gen = MoveGenerator(gaddag)

board = [['.' for _ in range(15)] for _ in range(15)]
board[7][7] = 'N'

rack = ['A', 'N', 'D', 'E', 'T', 'S']

# Manually execute the generate method step by step
moves = []
cross_checks = {}

rack_counter = collections.Counter(rack)
if ' ' in rack_counter:
    rack_counter['.'] += rack_counter[' ']
    del rack_counter[' ']

# 1. Generate ACROSS
move_gen._compute_cross_checks(board, cross_checks)
move_gen._find_moves(board, rack_counter, 'Across', moves, cross_checks)

across_count = len(moves)
print(f"After ACROSS generation: {across_count} moves")

# Check for duplicates in across moves
across_sigs = set()
across_dups = 0
for m in moves:
    sig = (m['row'], m['col'], m['dir'], m['word'])
    if sig in across_sigs:
        across_dups += 1
    across_sigs.add(sig)
print(f"  Unique signatures: {len(across_sigs)}")
print(f"  Duplicates: {across_dups}")

# 2. Generate DOWN
board_T = [list(x) for x in zip(*board)]
cross_checks_T = {}
move_gen._compute_cross_checks(board_T, cross_checks_T)

start_idx = len(moves)
move_gen._find_moves(board_T, rack_counter, 'Down', moves, cross_checks_T)

down_count_before_swap = len(moves) - start_idx
print(f"\nAfter DOWN generation (before swap): {down_count_before_swap} moves")

# Check for duplicates in down moves (before swap)
down_sigs_before = set()
down_dups_before = 0
for i in range(start_idx, len(moves)):
    m = moves[i]
    sig = (m['row'], m['col'], m['dir'], m['word'])
    if sig in down_sigs_before:
        down_dups_before += 1
    down_sigs_before.add(sig)
print(f"  Unique signatures: {len(down_sigs_before)}")
print(f"  Duplicates: {down_dups_before}")

# Fix coordinates for Down moves
for i in range(start_idx, len(moves)):
    m = moves[i]
    m['row'], m['col'] = m['col'], m['row']
    m['dir'] = 'Down'

# Check for duplicates in down moves (after swap)
down_sigs_after = set()
down_dups_after = 0
for i in range(start_idx, len(moves)):
    m = moves[i]
    sig = (m['row'], m['col'], m['dir'], m['word'])
    if sig in down_sigs_after:
        down_dups_after += 1
        print(f"  Duplicate found: {sig}")
    down_sigs_after.add(sig)
print(f"\nAfter coordinate swap:")
print(f"  Unique signatures: {len(down_sigs_after)}")
print(f"  Duplicates: {down_dups_after}")

# Check overall
total_sigs = set()
total_dups = 0
for m in moves:
    sig = (m['row'], m['col'], m['dir'], m['word'])
    if sig in total_sigs:
        total_dups += 1
    total_sigs.add(sig)

print(f"\nOverall:")
print(f"  Total moves: {len(moves)}")
print(f"  Unique signatures: {len(total_sigs)}")
print(f"  Duplicates: {total_dups}")
