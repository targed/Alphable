import json
import argparse
import random
import copy
import math
from collections import Counter
import torch
from alphable.core import inference
from alphable.core import simulator
from alphable.core.leave_eval import compute_leave_equity, BASE_TILE_EQUITY
from alphable.core.defense import compute_board_defense_adjustment
from alphable.core.endgame import ExactEndgameSolver


def get_unseen_distribution(board, my_rack):
    """
    Calculates the distribution of unseen tiles in the game.
    Total Bag = 100 tiles (standard distribution).
    Unseen = Total Bag - Tiles on Board - My Rack
    """
    # Standard Scrabble 100-tile distribution
    total_counts = {
        'A': 9, 'B': 2, 'C': 2, 'D': 4, 'E': 12, 'F': 2, 'G': 3, 'H': 2,
        'I': 9, 'J': 1, 'K': 1, 'L': 4, 'M': 2, 'N': 6, 'O': 8, 'P': 2,
        'Q': 1, 'R': 6, 'S': 4, 'T': 6, 'U': 4, 'V': 2, 'W': 2, 'X': 1,
        'Y': 2, 'Z': 1, '?': 2
    }

    unseen_counts = Counter(total_counts)

    # Subtract board tiles
    for r in range(15):
        for c in range(15):
            char = board[r][c]
            if char != '.':
                if char.islower():
                    unseen_counts['?'] -= 1
                else:
                    unseen_counts[char] -= 1

    # Subtract my rack
    for char in my_rack:
        unseen_counts[char] -= 1

    # Build list of unseen tiles
    unseen_tiles = []
    for char, count in unseen_counts.items():
        if count > 0:
            unseen_tiles.extend([char] * count)

    return unseen_tiles


def sample_opponent_rack(unseen_tiles, sample_size=7):
    """
    Randomly draws a rack of `sample_size` tiles from the unseen distribution.
    If there are fewer tiles available than `sample_size`, draws all of them.
    """
    if len(unseen_tiles) <= sample_size:
        return copy.deepcopy(unseen_tiles)
    return random.sample(unseen_tiles, sample_size)


class AlphableSearch:
    def __init__(
        self,
        inference_engine,
        num_simulations=16,
        top_k_candidates=10,
        opp_reply_top_k=3,
        opp_reply_prune_k=15,
        mode='bc_0ply',
        infer_batch_size=256,
        value_weight=60.0,
        enable_2ply=False,
        two_ply_threshold=8.0,
    ):
        """
        Initializes the Monte Carlo Rack Sampling search engine.

        Args:
            inference_engine (AlphableInference): The Phase 1/2 NN and GADDAG wrapper.
            num_simulations (int): Number of opponent racks to sample per candidate move.
            top_k_candidates (int): Number of our own top moves to simulate deeply.
            opp_reply_top_k (int): Number of strongest opponent replies to average.
            opp_reply_prune_k (int): Stage 1 fast pruning limit for opponent replies.
            mode (str): 'bc_0ply' for direct evaluation, 'lookahead' for 1-ply opponent simulation.
            infer_batch_size (int): Inference batch size to control GPU memory.
            value_weight (float): Equity weight multiplier applied to model value predictions.
            enable_2ply (bool): Whether to perform selective 2-ply counter-response on top 2 moves.
            two_ply_threshold (float): Point gap below which selective 2-ply is triggered.
        """
        self.engine = inference_engine
        self.num_simulations = num_simulations
        self.top_k_candidates = top_k_candidates
        self.opp_reply_top_k = opp_reply_top_k
        self.opp_reply_prune_k = opp_reply_prune_k
        self.mode = mode
        self.infer_batch_size = infer_batch_size
        self.value_weight = float(value_weight)
        self.enable_2ply = bool(enable_2ply)
        self.two_ply_threshold = float(two_ply_threshold)
        self.endgame_solver = ExactEndgameSolver(self.engine)

    def _batched_forward_values(self, board_state_pairs):
        values = []
        with torch.no_grad():
            for i in range(0, len(board_state_pairs), self.infer_batch_size):
                chunk = board_state_pairs[i:i + self.infer_batch_size]
                b_tensors = torch.stack(
                    [p[0] for p in chunk]).to(self.engine.device)
                s_tensors = torch.stack(
                    [p[1] for p in chunk]).to(self.engine.device)
                chunk_vals = self.engine.model(b_tensors, s_tensors).view(-1)
                values.extend(chunk_vals.detach().cpu().tolist())
        return values

    def _generate_exchange_candidates(self, board, rack, score_diff, bag_remaining):
        """
        Generates tactical tile exchange candidates when bag has >= 7 tiles and
        rack has severe structural flaws (all consonants, all vowels, or bad clunkers).
        """
        if bag_remaining < 7 or not rack:
            return []

        rack_str = "".join(rack).upper()
        vowels = [c for c in rack_str if c in "AEIOU"]
        consonants = [c for c in rack_str if c not in "AEIOU" and c != "?"]
        blanks = [c for c in rack_str if c == "?"]

        candidates = []

        # Flaw 1: All consonants (0 vowels and 0 blanks)
        if len(vowels) == 0 and len(blanks) == 0 and len(consonants) >= 5:
            sorted_cons = sorted(consonants, key=lambda c: BASE_TILE_EQUITY.get(c, -5.0), reverse=True)
            keep_count = min(2, len(sorted_cons) - 1)
            dump = sorted_cons[keep_count:]
            if len(dump) >= 3:
                candidates.append(dump)

        # Flaw 2: All vowels (0 consonants and 0 blanks)
        elif len(consonants) == 0 and len(blanks) == 0 and len(vowels) >= 5:
            sorted_vow = sorted(vowels, key=lambda c: BASE_TILE_EQUITY.get(c, -5.0), reverse=True)
            keep_count = min(2, len(sorted_vow) - 1)
            dump = sorted_vow[keep_count:]
            if len(dump) >= 3:
                candidates.append(dump)

        # Flaw 3: Severe clunker concentration (e.g. holding Q without U, multiple V's, W's)
        # or heavy duplicate penalties (e.g. III, UUU, VVV)
        counts = Counter(rack_str)
        heavy_duplicates = []
        for tile, cnt in counts.items():
            if cnt >= 3 and tile in "IUOVW":
                heavy_duplicates.extend([tile] * (cnt - 1))
            elif cnt >= 2 and tile in "UV":
                heavy_duplicates.extend([tile] * (cnt - 1))

        if "Q" in counts and "U" not in counts:
            heavy_duplicates.append("Q")

        if len(heavy_duplicates) >= 2:
            dump = heavy_duplicates[:5]
            if dump not in candidates and len(dump) >= 2:
                candidates.append(dump)

        exchange_moves = []
        for dump_tiles in candidates:
            kept_rack = list(rack)
            for d in dump_tiles:
                if d in kept_rack:
                    kept_rack.remove(d)

            leave_eq = compute_leave_equity(kept_rack)
            turn_loss_penalty = 12.0
            expected_exchange_equity = leave_eq - turn_loss_penalty

            move_dict = {
                "action": "EXCHANGE",
                "tiles_to_exchange": dump_tiles,
                "word": f"EXCHANGE({','.join(dump_tiles)})",
                "row": 7,
                "col": 7,
                "dir": "Across",
                "points": 0,
            }
            exchange_moves.append({
                "move": move_dict,
                "board": copy.deepcopy(board),
                "score_diff": score_diff,
                "rack": kept_rack,
                "points": 0,
                "value": 0.0,
                "leave_equity": leave_eq,
                "defense_adj": 0.0,
                "equity": expected_exchange_equity,
            })

        return exchange_moves

    def find_best_move(self, board, rack, score_diff, bag_remaining):
        """
        1-Ply Lookahead with Opponent Rack Sampling, Leave Valuation, and Two-Stage Pruning.

        1. Generate all legal moves for our rack and evaluate tactical exchange candidates.
        2. Evaluate all immediate "After-States" using Leave Equity, Defense Adjustments, and Value Network.
        3. Pick diverse Top-K moves as "Candidates" (Equity, Leave/Value, and Score).
        4. For each Candidate:
           a. Apply the move to get our new Board and Score.
           b. Sample N random opponent racks.
           c. Generate opponent replies and prune to Top-M via fast heuristic (Stage 1).
           d. Deep evaluate Top-M replies using Value Network (Stage 2).
           e. The "True Equity" evaluates net points, strategic advantage, defense, and leave.
        5. Return the Candidate with the highest expected equity.
        """
        # Step 0: Deterministic Exact Endgame when bag is empty
        if bag_remaining == 0:
            unseen_tiles = get_unseen_distribution(board, rack)
            if len(unseen_tiles) <= 7:
                best_endgame_move, best_margin = self.endgame_solver.solve(
                    board, rack, unseen_tiles, score_diff=score_diff, max_depth=4
                )
                norm_val = math.tanh(best_margin / 100.0)
                return best_endgame_move, norm_val

        # Step 1: Generate all our legal moves
        my_moves = self.engine.move_gen.generate(board, rack)

        # Step 1b: Generate candidate exchanges if bag allows
        exchange_candidates = self._generate_exchange_candidates(board, rack, score_diff, bag_remaining)

        if not my_moves and not exchange_candidates:
            return None, 0.0  # Pass

        if my_moves:
            print(f"Generated {len(my_moves)} legal moves.")
        if exchange_candidates:
            print(f"Generated {len(exchange_candidates)} exchange candidate(s).")

        # Step 2: Evaluate 0-Ply Value (Immediate After-State)
        candidate_evals = []

        batch_boards = []
        batch_states = []
        batch_moves = []

        state_vec_size = getattr(self.engine, 'state_vector_size', 36)
        if not isinstance(state_vec_size, int):
            state_vec_size = 36
        unseen_counts_map = Counter(get_unseen_distribution(board, rack)) if state_vec_size >= 63 else None

        for move in my_moves:
            new_board, points, new_rack = simulator.simulate_move(
                board, move, rack)
            new_score_diff = score_diff + points

            b_tensor = inference.board_to_tensor(new_board)
            s_tensor = inference.state_to_tensor(
                new_rack, new_score_diff, bag_remaining,
                unseen_counts=unseen_counts_map,
                state_vector_size=state_vec_size,
            )

            batch_boards.append(b_tensor)
            batch_states.append(s_tensor)
            batch_moves.append((move, new_board, new_score_diff, new_rack, points))

        win_probs = []
        if batch_boards:
            win_probs = self._batched_forward_values(
                list(zip(batch_boards, batch_states)))

        for i in range(len(my_moves)):
            move, n_board, n_sd, n_rack, pts = batch_moves[i]
            val = win_probs[i]
            leave_eq = compute_leave_equity(n_rack)
            def_adj = compute_board_defense_adjustment(board, n_board, move, score_diff)
            equity = float(pts) + leave_eq + def_adj + self.value_weight * val
            candidate_evals.append({
                'move': move,
                'board': n_board,
                'score_diff': n_sd,
                'rack': n_rack,
                'points': pts,
                'value': val,
                'leave_equity': leave_eq,
                'defense_adj': def_adj,
                'equity': equity,
            })

        for exc in exchange_candidates:
            candidate_evals.append(exc)

        # Step 3: Pick Top-K Candidates with Strategic Diversity
        selected_candidates = []
        seen_moves = set()

        def add_cand(c):
            m = c['move']
            key = (m.get('action', 'PLAY'), m['row'], m['col'], m['dir'], m['word'])
            if key not in seen_moves:
                seen_moves.add(key)
                selected_candidates.append(c)

        by_equity = sorted(candidate_evals, key=lambda x: x['equity'], reverse=True)
        by_value = sorted(candidate_evals, key=lambda x: x['value'] + x.get('leave_equity', 0.0) / max(1.0, self.value_weight), reverse=True)
        by_points = sorted(candidate_evals, key=lambda x: x['points'], reverse=True)

        # 1. Top candidates by total equity
        for c in by_equity[:min(4, len(by_equity))]:
            add_cand(c)
        # 2. Top 1 by pure strategic value / leave
        if by_value:
            add_cand(by_value[0])
        # 3. Top 1 by pure points (greedy play)
        if by_points:
            add_cand(by_points[0])
        # 4. Fill remaining slots up to top_k_candidates with highest remaining equity
        for c in by_equity[len(selected_candidates):]:
            if len(selected_candidates) >= self.top_k_candidates:
                break
            add_cand(c)

        top_candidates = selected_candidates[:self.top_k_candidates]

        if self.mode == 'bc_0ply':
            top_to_print = min(3, len(top_candidates))
            for i in range(top_to_print):
                c = top_candidates[i]
                m = c['move']
                print(
                    f"0-Ply Candidate {i+1}: {m['word']} at {m['row']},{m['col']} | "
                    f"Points: {c['points']} | Leave: {c.get('leave_equity', 0.0):+.1f} | Def: {c.get('defense_adj', 0.0):+.1f} | "
                    f"Val: {c['value']:.3f} | Equity: {c['equity']:.1f}"
                )

            best = top_candidates[0]
            return best['move'], best['value']

        print(
            f"Selected Top {len(top_candidates)} Candidates for Deep Simulation.")

        # Determine unseen tiles
        unseen_tiles = get_unseen_distribution(board, rack)

        best_candidate = None
        best_expected_equity = -float('inf')
        best_expected_value = -float('inf')

        # Step 4: Deep Simulation (1-Ply Lookahead with Sampling)
        for cand_idx, cand in enumerate(top_candidates):
            cand_move = cand['move']
            cand_board = cand['board']
            cand_score_diff = cand['score_diff']
            cand_points = cand['points']
            cand_val = cand['value']
            cand_leave = cand.get('leave_equity', 0.0)
            cand_def = cand.get('defense_adj', 0.0)

            total_simulation_equity = 0.0

            for sim in range(self.num_simulations):
                # 4b. Sample Opponent Rack
                opp_rack = sample_opponent_rack(unseen_tiles, sample_size=7)

                # 4c. Generate Opponent Replies
                opp_moves = self.engine.move_gen.generate(cand_board, opp_rack)

                if not opp_moves:
                    # Opponent passes.
                    sim_equity = float(cand_points) + cand_leave + cand_def + self.value_weight * cand_val
                    total_simulation_equity += sim_equity
                    continue

                # Stage 1: Fast Heuristic Pruning (points + leave equity)
                scored_opp = []
                for opp_m in opp_moves:
                    opp_nb, opp_pts, opp_nr = simulator.simulate_move(cand_board, opp_m, opp_rack)
                    opp_leave = compute_leave_equity(opp_nr)
                    h_score = float(opp_pts) + opp_leave
                    scored_opp.append((h_score, opp_m, opp_nb, opp_pts, opp_nr, opp_leave))

                scored_opp.sort(key=lambda x: x[0], reverse=True)
                top_opp = scored_opp[:self.opp_reply_prune_k]

                # Stage 2: Deep Evaluation on Top-M opponent replies
                opp_batch_boards = []
                opp_batch_states = []
                opp_move_points = []
                opp_leaves = []

                opp_unseen_map = Counter(unseen_tiles) if state_vec_size >= 63 else None
                for _, opp_m, opp_nb, opp_pts, opp_nr, opp_leave in top_opp:
                    opp_score_diff = -(cand_score_diff - opp_pts)
                    b_tensor = inference.board_to_tensor(opp_nb)
                    s_tensor = inference.state_to_tensor(
                        opp_nr, opp_score_diff, bag_remaining,
                        unseen_counts=opp_unseen_map,
                        state_vector_size=state_vec_size,
                    )

                    opp_batch_boards.append(b_tensor)
                    opp_batch_states.append(s_tensor)
                    opp_move_points.append(opp_pts)
                    opp_leaves.append(opp_leave)

                opp_vals = self._batched_forward_values(
                    list(zip(opp_batch_boards, opp_batch_states))
                )

                opp_equities = [
                    float(p) + l + self.value_weight * v
                    for p, l, v in zip(opp_move_points, opp_leaves, opp_vals)
                ]

                k = min(max(1, self.opp_reply_top_k), len(opp_equities))
                topk_indices = sorted(range(len(opp_equities)), key=lambda idx: opp_equities[idx], reverse=True)[:k]
                topk_equities = [opp_equities[idx] for idx in topk_indices]
                topk_points = [float(opp_move_points[idx]) for idx in topk_indices]
                topk_vals = [opp_vals[idx] for idx in topk_indices]

                exp_weights = [math.exp((eq - topk_equities[0]) / 5.0) for eq in topk_equities]
                sum_w = sum(exp_weights)
                expected_opp_points = sum(w * p for w, p in zip(exp_weights, topk_points)) / sum_w
                expected_opp_val = sum(w * v for w, v in zip(exp_weights, topk_vals)) / sum_w

                sim_points_diff = float(cand_points) - expected_opp_points
                sim_strategic_diff = cand_val - expected_opp_val
                sim_equity = (
                    sim_points_diff
                    + cand_leave
                    + cand_def
                    + self.value_weight * sim_strategic_diff
                )
                total_simulation_equity += sim_equity

            # Average simulated equity across all random racks
            cand_total_equity = total_simulation_equity / self.num_simulations
            cand_sim_val = (cand_total_equity - float(cand_points) - cand_leave - cand_def) / max(1.0, self.value_weight)
            print(
                f"Candidate {cand_idx+1}: {cand_move['word']} at {cand_move['row']},{cand_move['col']} | "
                f"Points: {cand_points} | Leave: {cand_leave:+.1f} | Def: {cand_def:+.1f} | "
                f"0-Ply Val: {cand_val:.3f} | 1-Ply Sim Equity: {cand_total_equity:.1f}"
            )

            cand['sim_equity'] = cand_total_equity
            cand['sim_val'] = cand_sim_val

        # Sort candidates by 1-ply simulated equity
        top_candidates.sort(key=lambda c: c.get('sim_equity', -float('inf')), reverse=True)

        # Step 5: Selective 2-Ply Lookahead on Top-2 Candidates if equity is close
        if self.enable_2ply and len(top_candidates) >= 2:
            gap = top_candidates[0]['sim_equity'] - top_candidates[1]['sim_equity']
            if gap <= self.two_ply_threshold:
                print(f"Selective 2-Ply Triggered: Candidate 1 and 2 equity gap is {gap:.1f} <= {self.two_ply_threshold:.1f} pts.")
                for cand in top_candidates[:2]:
                    needed_tiles = 7 - len(cand['rack'])
                    remaining_unseen = [t for t in unseen_tiles if t not in cand['rack']]
                    drawn_tiles = sample_opponent_rack(remaining_unseen, sample_size=needed_tiles)
                    replenished_rack = cand['rack'] + drawn_tiles
                    counter_moves = self.engine.move_gen.generate(cand['board'], replenished_rack)
                    if counter_moves:
                        best_counter_pts = -float('inf')
                        for cm in counter_moves[:10]:
                            _, c_pts, c_nr = simulator.simulate_move(cand['board'], cm, replenished_rack)
                            c_leave = compute_leave_equity(c_nr, bag_remaining=max(0, bag_remaining - 7))
                            c_score = float(c_pts) + c_leave
                            if c_score > best_counter_pts:
                                best_counter_pts = c_score
                        cand['two_ply_equity'] = cand['sim_equity'] + 0.3 * best_counter_pts
                    else:
                        cand['two_ply_equity'] = cand['sim_equity']

                top_candidates[:2] = sorted(
                    top_candidates[:2],
                    key=lambda c: c.get('two_ply_equity', c.get('sim_equity', -float('inf'))),
                    reverse=True
                )

        best_cand = top_candidates[0]
        return best_cand['move'], best_cand.get('sim_val', best_cand.get('value', 0.0))


def main():
    import os

    def board_from_compact(compact_board):
        board = []
        for r in range(15):
            start = r * 15
            board.append(list(compact_board[start:start + 15]))
        return board

    def load_real_eval_cases(samples_path, num_cases=5):
        if not os.path.exists(samples_path):
            return []

        with open(samples_path, 'r') as f:
            all_samples = [json.loads(line) for line in f if line.strip()]

        if not all_samples:
            return []

        candidates = []
        for s in all_samples:
            board = s.get('board', '')
            rack = s.get('rack', '')
            bag = int(s.get('bag', 0))
            if len(board) != 225:
                continue
            if '.' * 225 == board:
                continue
            if len(rack) == 0:
                continue
            # Prefer broadly midgame-like states.
            if 15 <= bag <= 70:
                candidates.append(s)

        if not candidates:
            candidates = all_samples

        step = max(1, len(candidates) // num_cases)
        picked = []
        for idx in range(0, len(candidates), step):
            picked.append(candidates[idx])
            if len(picked) >= num_cases:
                break

        cases = []
        for i, sample in enumerate(picked, start=1):
            cases.append({
                'label': f"Case {i + 1}: Real Sample Eval",
                'board': board_from_compact(sample['board']),
                'rack': list(sample['rack']),
                'score_diff': int(sample.get('score_diff', 0)),
                'bag_remaining': int(sample.get('bag', 0)),
            })
        return cases

    def run_case(searcher, board, rack, score_diff, bag_remaining, label):
        print(f"\n--- {label} ---")
        print(
            f"Rack: {''.join(rack)} | Score Diff: {score_diff} | Bag: {bag_remaining}")
        best_move, best_val = searcher.find_best_move(
            board,
            rack,
            score_diff=score_diff,
            bag_remaining=bag_remaining,
        )
        if best_move:
            print("Search Complete.")
            print(
                f"Chosen Move: {best_move['word']} at "
                f"({best_move['row']}, {best_move['col']}, {best_move['dir']})"
            )
            print(f"Expected Win Probability: {best_val:.3f}")
        else:
            print("No legal move found (pass/exchange state).")
        return best_val

    default_device = 'cuda' if torch.cuda.is_available() else 'cpu'

    parser = argparse.ArgumentParser(
        description='Run Alphable search diagnostics and evaluation.')
    parser.add_argument('--model', type=str, default='models/alphable_rl_best_val_model.pth',
                        help='Checkpoint path to load for search evaluation.')
    parser.add_argument('--mode', choices=['bc_0ply', 'lookahead'], default='lookahead',
                        help='Search mode: bc_0ply for BC argmax, lookahead for 1-ply simulation.')
    parser.add_argument('--dict', type=str, default='resources/NWL2023.txt',
                        help='Dictionary path for move generation.')
    parser.add_argument('--device', type=str, default=default_device,
                        help='Torch device for inference, e.g. cpu or cuda.')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed used for reproducible rack sampling.')
    parser.add_argument('--infer-batch-size', type=int, default=128,
                        help='Inference batch size for candidate scoring.')
    parser.add_argument('--smoke-sims', type=int, default=8,
                        help='Number of opponent rack simulations for smoke case (lookahead mode).')
    parser.add_argument('--eval-sims', type=int, default=32,
                        help='Number of opponent rack simulations for real eval cases (lookahead mode).')
    parser.add_argument('--top-k', type=int, default=3,
                        help='Top candidate moves kept before deep simulation or display.')
    parser.add_argument('--opp-reply-top-k', type=int, default=5,
                        help='Number of strongest opponent replies to average in lookahead mode.')
    parser.add_argument('--samples-path', type=str, default='data/supervised/samples.jsonl',
                        help='Source JSONL for real-board evaluation cases.')
    parser.add_argument('--num-real-cases', type=int, default=5,
                        help='Number of real-position evaluation cases. Use 0 to skip.')
    args = parser.parse_args()

    print("Testing Phase 3 MCTS Search...")

    model_path = args.model if os.path.exists(args.model) else None
    if model_path:
        print(f"Loading trained model from {model_path}...")
    else:
        print(
            f"Warning: Model not found at {args.model}. Falling back to untrained random weights.")

    eng = inference.AlphableInference(
        model_path=model_path, device=args.device, dict_path=args.dict)

    random.seed(args.seed)

    smoke_searcher = AlphableSearch(
        eng,
        num_simulations=args.smoke_sims,
        top_k_candidates=args.top_k,
        opp_reply_top_k=max(1, min(args.opp_reply_top_k, 2)),
        mode=args.mode,
        infer_batch_size=args.infer_batch_size,
    )
    eval_searcher = AlphableSearch(
        eng,
        num_simulations=args.eval_sims,
        top_k_candidates=args.top_k,
        opp_reply_top_k=args.opp_reply_top_k,
        mode=args.mode,
        infer_batch_size=args.infer_batch_size,
    )

    # Case 1: Smoke test from empty board
    smoke_board = simulator.create_empty_board()
    smoke_rack = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    smoke_val = run_case(
        smoke_searcher,
        smoke_board,
        smoke_rack,
        score_diff=0,
        bag_remaining=100,
        label="Case 1: Empty Board Smoke Test",
    )

    real_cases = []
    if args.num_real_cases > 0:
        real_cases = load_real_eval_cases(
            args.samples_path, num_cases=args.num_real_cases)
    if not real_cases:
        if args.num_real_cases > 0:
            print(
                f"\nNo real evaluation cases could be loaded from {args.samples_path}.")
        else:
            print("\nSkipping real-position evaluation (--num-real-cases=0).")
    else:
        print(
            f"\nRunning {len(real_cases)} real-position evaluation case(s) "
            f"in mode={args.mode} (top_k_candidates={args.top_k})..."
        )
        eval_vals = []
        for case in real_cases:
            best_val = run_case(
                eval_searcher,
                case['board'],
                case['rack'],
                score_diff=case['score_diff'],
                bag_remaining=case['bag_remaining'],
                label=case['label'],
            )
            eval_vals.append(best_val)

        if eval_vals:
            avg_val = sum(eval_vals) / len(eval_vals)
            min_val = min(eval_vals)
            max_val = max(eval_vals)
            print("\nEvaluation Summary:")
            print(f"Smoke best value: {smoke_val:.3f}")
            print(
                f"Real cases best value mean/min/max: "
                f"{avg_val:.3f} / {min_val:.3f} / {max_val:.3f}"
            )


if __name__ == "__main__":
    main()
