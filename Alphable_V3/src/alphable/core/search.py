import json
import argparse
import random
import copy
import math
from collections import Counter
import torch
from alphable.core import inference
from alphable.core import simulator


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
        num_simulations=10,
        top_k_candidates=5,
        opp_reply_top_k=3,
        mode='bc_0ply',
        infer_batch_size=256,
    ):
        """
        Initializes the Monte Carlo Rack Sampling search engine.

        Args:
            inference_engine (AlphableInference): The Phase 1/2 NN and GADDAG wrapper.
            num_simulations (int): Number of opponent racks to sample per candidate move.
            top_k_candidates (int): Number of our own top moves to simulate deeply.
            opp_reply_top_k (int): Number of strongest opponent replies to average
                instead of taking a single worst-case max.
            mode (str): 'bc_0ply' for behavior-cloning argmax play, 'lookahead'
                for 1-ply opponent simulation (intended for RL value nets).
            infer_batch_size (int): Inference batch size to control GPU memory
                for positions with many legal moves.
        """
        self.engine = inference_engine
        self.num_simulations = num_simulations
        self.top_k_candidates = top_k_candidates
        self.opp_reply_top_k = opp_reply_top_k
        self.mode = mode
        self.infer_batch_size = infer_batch_size

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

    def find_best_move(self, board, rack, score_diff, bag_remaining):
        """
        1-Ply Lookahead with Opponent Rack Sampling.

        1. Generate all legal moves for our rack.
        2. Evaluate all immediate "After-States" using the Value Network.
        3. Pick the Top-K highest-valued moves as "Candidates".
        4. For each Candidate:
           a. Apply the move to get our new Board and Score.
           b. Sample N random opponent racks.
           c. For each opponent rack, generate their legal replies.
           d. Find the opponent's best reply using the Value Network (evaluating from their perspective).
           e. The "True Value" of our Candidate is the average Value of the board *after* the opponent's best reply.
        5. Return the Candidate with the highest True Value.
        """
        # Step 1: Generate all our legal moves
        my_moves = self.engine.move_gen.generate(board, rack)

        if not my_moves:
            return None, 0.0  # Pass or Exchange

        print(f"Generated {len(my_moves)} legal moves.")

        # Step 2: Evaluate 0-Ply Value (Immediate After-State)
        candidate_evals = []

        # We process our moves in batches to utilize the GPU efficiently
        batch_boards = []
        batch_states = []
        batch_moves = []

        for move in my_moves:
            new_board, points, new_rack = simulator.simulate_move(
                board, move, rack)
            new_score_diff = score_diff + points

            b_tensor = inference.board_to_tensor(new_board)
            s_tensor = inference.state_to_tensor(
                new_rack, new_score_diff, bag_remaining)

            batch_boards.append(b_tensor)
            batch_states.append(s_tensor)
            batch_moves.append((move, new_board, new_score_diff, new_rack, points))

        win_probs = self._batched_forward_values(
            list(zip(batch_boards, batch_states)))

        for i in range(len(my_moves)):
            pts = batch_moves[i][4]
            val = win_probs[i]
            equity = float(pts) + 25.0 * val
            candidate_evals.append({
                'move': batch_moves[i][0],
                'board': batch_moves[i][1],
                'score_diff': batch_moves[i][2],
                'rack': batch_moves[i][3],
                'points': pts,
                'value': val,
                'equity': equity,
            })

        # Step 3: Pick Top-K Candidates (ranked by total equity = points + 25.0 * value)
        candidate_evals.sort(key=lambda x: x['equity'], reverse=True)
        top_candidates = candidate_evals[:self.top_k_candidates]

        if self.mode == 'bc_0ply':
            top_to_print = min(3, len(top_candidates))
            for i in range(top_to_print):
                c = top_candidates[i]
                m = c['move']
                print(
                    f"0-Ply Candidate {i+1}: {m['word']} at {m['row']},{m['col']} | "
                    f"Points: {c['points']} | Val: {c['value']:.3f} | Equity: {c['equity']:.1f}"
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

            # Note: We must update the unseen distribution since we just played tiles from our rack
            # The tiles we played are now on the board, so they remain "seen".

            total_simulation_value = 0.0

            for sim in range(self.num_simulations):
                # 4b. Sample Opponent Rack
                opp_rack = sample_opponent_rack(unseen_tiles, sample_size=7)

                # 4c. Generate Opponent Replies
                opp_moves = self.engine.move_gen.generate(cand_board, opp_rack)

                if not opp_moves:
                    # Opponent passes. The value is just the value of our board state.
                    total_simulation_value += cand['value']
                    continue

                # 4d. Find Opponent's Best Reply
                opp_batch_boards = []
                opp_batch_states = []
                opp_move_points = []

                for opp_move in opp_moves:
                    opp_new_board, opp_points, opp_new_rack = simulator.simulate_move(
                        cand_board, opp_move, opp_rack)

                    # Opponent's perspective: Score diff is inverted.
                    opp_score_diff = -(cand_score_diff - opp_points)

                    b_tensor = inference.board_to_tensor(opp_new_board)
                    s_tensor = inference.state_to_tensor(
                        opp_new_rack, opp_score_diff, bag_remaining)

                    opp_batch_boards.append(b_tensor)
                    opp_batch_states.append(s_tensor)
                    opp_move_points.append(opp_points)

                # Evaluate from opponent's perspective. Higher equity is better for them.
                opp_vals = self._batched_forward_values(
                    list(zip(opp_batch_boards, opp_batch_states))
                )

                # Opponent total move equity: immediate points + 25.0 * after-state value
                opp_equities = [float(p) + 25.0 * v for p, v in zip(opp_move_points, opp_vals)]

                k = min(max(3, self.opp_reply_top_k), len(opp_equities))
                topk_equities = sorted(opp_equities, reverse=True)[:k]
                # Softmax temperature over top replies to avoid extreme single-outlier noise
                exp_weights = [math.exp((eq - topk_equities[0]) / 5.0) for eq in topk_equities]
                expected_opp_equity = sum(w * eq for w, eq in zip(exp_weights, topk_equities)) / sum(exp_weights)

                # 4e. Net simulation value from our perspective:
                # continuation value reflects the negative of opponent's expected equity
                sim_value = -expected_opp_equity / 25.0
                total_simulation_value += sim_value

            # Average the simulated values across all N random racks
            avg_expected_value = total_simulation_value / self.num_simulations
            cand_total_equity = float(cand['points']) + 25.0 * avg_expected_value
            print(f"Candidate {cand_idx+1}: {cand_move['word']} at {cand_move['row']},{cand_move['col']} | "
                  f"Points: {cand['points']} | 0-Ply Val: {cand['value']:.3f} | 1-Ply Sim Val: {avg_expected_value:.3f} | Total Equity: {cand_total_equity:.1f}")

            if cand_total_equity > best_expected_equity:
                best_expected_equity = cand_total_equity
                best_expected_value = avg_expected_value
                best_candidate = cand_move

        return best_candidate, best_expected_value


if __name__ == "__main__":
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
