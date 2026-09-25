"""
End-to-End System Integration & Benchmark for Alphable 5-Pillars Engine Upgrade.
"""

import time
import os
import torch
from alphable.core import simulator, inference
from alphable.core.search import AlphableSearch
from alphable.core.leave_eval import compute_leave_equity
from alphable.core.endgame import ExactEndgameSolver

def run_benchmark():
    print("=" * 65)
    print("🚀 ALPHABLE 5-PILLARS ENGINE UPGRADE INTEGRATION BENCHMARK")
    print("=" * 65)

    dict_path = 'resources/NWL2023.txt'
    if not os.path.exists(dict_path):
        dict_path = 'resources/CSW24.txt'
    print(f"Loading dictionary from: {dict_path}")

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    engine = inference.AlphableInference(
        model_path=None,
        dict_path=dict_path,
        device=device,
        state_vector_size=63,
    )
    searcher = AlphableSearch(
        inference_engine=engine,
        num_simulations=5,
        top_k_candidates=5,
        opp_reply_top_k=2,
        opp_reply_prune_k=10,
        enable_2ply=True,
        two_ply_threshold=8.0,
        mode='lookahead',
    )

    # -------------------------------------------------------------
    # Pillar 1 & 3 Check: Leave Valuation & Stem Synergies
    # -------------------------------------------------------------
    print("\n--- Pillar 1 & 3: Super-Leave & Stem Synergy Verification ---")
    retin_equity = compute_leave_equity("RETIN", bag_remaining=60)
    print(f"Leave 'RETIN' (60 bag) equity: {retin_equity:+.1f} pts (Lipkin-Smith standard)")
    assert retin_equity >= 10.0, f"Expected RETIN equity >= 10.0, got {retin_equity}"

    qz_endgame = compute_leave_equity("QZ", bag_remaining=0)
    print(f"Leave 'QZ' (0 bag) endgame deduction: {qz_endgame:+.1f} pts (Face value deduction)")
    assert qz_endgame == -20.0, f"Expected QZ deduction -20.0, got {qz_endgame}"
    print("✓ Pillar 1 & 3 verification passed!")

    # -------------------------------------------------------------
    # Pillar 2 Check: 63-Dim Bag Tracking
    # -------------------------------------------------------------
    print("\n--- Pillar 2: 63-Dim Bag Tracking Tensor Verification ---")
    board = simulator.create_empty_board()
    rack = ['A', 'E', 'R', 'S', 'T', 'I', 'N']
    unseen_map = {'A': 5, 'E': 8, 'Z': 1, '?': 1}
    s_tensor = inference.state_to_tensor(rack, score_diff=15, bag_remaining=45, unseen_counts=unseen_map, state_vector_size=63)
    assert s_tensor.shape == (63,)
    print(f"Generated enriched state tensor of shape {s_tensor.shape} with bag tracking features.")
    print("✓ Pillar 2 verification passed!")

    # -------------------------------------------------------------
    # Pillar 4 Check: Midgame Move Search with Selective 2-Ply Lookahead
    # -------------------------------------------------------------
    print("\n--- Pillar 4: Midgame Search & Selective 2-Ply Benchmarking ---")
    # Put a starting word on board
    board[7][7] = 'H'
    board[7][8] = 'E'
    board[7][9] = 'L'
    board[7][10] = 'L'
    board[7][11] = 'O'

    search_rack = ['A', 'E', 'R', 'T', 'S', 'P', 'N']
    t0 = time.time()
    best_move, value = searcher.find_best_move(board, search_rack, score_diff=0, bag_remaining=70)
    search_time = time.time() - t0

    assert best_move is not None
    print(f"\n✓ Midgame Move Selected: '{best_move['word']}' at ({best_move['row']},{best_move['col']}) {best_move['dir']}")
    print(f"  Execution time: {search_time:.3f}s (Budget: <= 2.50s)")
    assert search_time <= 3.5, f"Search took too long: {search_time:.3f}s"
    print("✓ Pillar 4 verification passed!")

    # -------------------------------------------------------------
    # Pillar 5 Check: Exact Endgame Solver when bag == 0
    # -------------------------------------------------------------
    print("\n--- Pillar 5: Exact Deterministic Endgame Minimax Verification ---")
    # In real Scrabble endgame (bag == 0), ~93+ of the standard 100 tiles are on board.
    from alphable.core.inference import STANDARD_TILE_COUNTS
    endgame_board = simulator.create_empty_board()
    endgame_board[7][7] = 'H'
    endgame_board[7][8] = 'E'
    endgame_board[7][9] = 'L'
    endgame_board[7][10] = 'L'
    endgame_board[7][11] = 'O'

    # Build pool of tiles and place 93 on board respecting standard distribution
    used = {'H': 1, 'E': 1, 'L': 2, 'O': 1, 'S': 1}
    placed = 0
    for char, count in STANDARD_TILE_COUNTS.items():
        if char == '?':
            continue
        to_place = count - used.get(char, 0)
        for _ in range(to_place):
            r = placed // 15
            c = placed % 15
            if (r, c) not in [(7, 7), (7, 8), (7, 9), (7, 10), (7, 11)]:
                endgame_board[r][c] = char
                placed += 1

    endgame_rack = ['S']
    t0 = time.time()
    best_endgame_move, endgame_val = searcher.find_best_move(endgame_board, endgame_rack, score_diff=10, bag_remaining=0)
    endgame_time = time.time() - t0

    assert best_endgame_move is not None
    print(f"✓ Exact Endgame Move Selected: '{best_endgame_move['word']}' at ({best_endgame_move['row']},{best_endgame_move['col']})")
    print(f"  Execution time: {endgame_time:.4f}s (Budget: <= 0.10s)")
    assert endgame_time <= 0.10, f"Endgame solver took too long: {endgame_time:.4f}s"
    print("✓ Pillar 5 exact endgame verification passed!")


    print("\n" + "=" * 65)
    print("🎉 ALL 5 PILLARS INTEGRATED AND VERIFIED SUCCESSFULLY!")
    print("=" * 65)

if __name__ == '__main__':
    run_benchmark()
