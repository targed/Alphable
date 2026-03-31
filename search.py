import random
import copy
from collections import Counter
import torch
import inference
import simulator

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
    def __init__(self, inference_engine, num_simulations=10, top_k_candidates=5):
        """
        Initializes the Monte Carlo Rack Sampling search engine.

        Args:
            inference_engine (AlphableInference): The Phase 1/2 NN and GADDAG wrapper.
            num_simulations (int): Number of opponent racks to sample per candidate move.
            top_k_candidates (int): Number of our own top moves to simulate deeply.
        """
        self.engine = inference_engine
        self.num_simulations = num_simulations
        self.top_k_candidates = top_k_candidates

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
            return None, 0.0 # Pass or Exchange

        print(f"Generated {len(my_moves)} legal moves.")

        # Step 2: Evaluate 0-Ply Value (Immediate After-State)
        candidate_evals = []

        # We process our moves in batches to utilize the GPU efficiently
        batch_boards = []
        batch_states = []
        batch_moves = []

        for move in my_moves:
            new_board, points, new_rack = simulator.simulate_move(board, move, rack)
            new_score_diff = score_diff + points

            b_tensor = inference.board_to_tensor(new_board)
            s_tensor = inference.state_to_tensor(new_rack, new_score_diff, bag_remaining)

            batch_boards.append(b_tensor)
            batch_states.append(s_tensor)
            batch_moves.append((move, new_board, new_score_diff, new_rack))

        # Run inference
        b_tensors = torch.stack(batch_boards).to(self.engine.device)
        s_tensors = torch.stack(batch_states).to(self.engine.device)

        with torch.no_grad():
            win_probs = self.engine.model(b_tensors, s_tensors)

        for i in range(len(my_moves)):
            candidate_evals.append({
                'move': batch_moves[i][0],
                'board': batch_moves[i][1],
                'score_diff': batch_moves[i][2],
                'rack': batch_moves[i][3],
                'value': win_probs[i].item()
            })

        # Step 3: Pick Top-K Candidates
        candidate_evals.sort(key=lambda x: x['value'], reverse=True)
        top_candidates = candidate_evals[:self.top_k_candidates]

        print(f"Selected Top {len(top_candidates)} Candidates for Deep Simulation.")

        # Determine unseen tiles
        unseen_tiles = get_unseen_distribution(board, rack)

        best_candidate = None
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

                for opp_move in opp_moves:
                    opp_new_board, opp_points, opp_new_rack = simulator.simulate_move(cand_board, opp_move, opp_rack)

                    # Opponent's perspective: Score diff is inverted.
                    opp_score_diff = -(cand_score_diff - opp_points)

                    b_tensor = inference.board_to_tensor(opp_new_board)
                    s_tensor = inference.state_to_tensor(opp_new_rack, opp_score_diff, bag_remaining)

                    opp_batch_boards.append(b_tensor)
                    opp_batch_states.append(s_tensor)

                opp_b_tensors = torch.stack(opp_batch_boards).to(self.engine.device)
                opp_s_tensors = torch.stack(opp_batch_states).to(self.engine.device)

                with torch.no_grad():
                    # Evaluate from Opponent's perspective. Higher is better for them.
                    opp_win_probs = self.engine.model(opp_b_tensors, opp_s_tensors)

                best_opp_val = torch.max(opp_win_probs).item()

                # 4e. The true value for US is the inverse of the Opponent's best value.
                # Since the network outputs [-1, 1], an opponent win prob of 0.8 means our win prob is -0.8.
                our_true_val = -best_opp_val
                total_simulation_value += our_true_val

            # Average the simulated values across all N random racks
            avg_expected_value = total_simulation_value / self.num_simulations
            print(f"Candidate {cand_idx+1}: {cand_move['word']} at {cand_move['row']},{cand_move['col']} | "
                  f"0-Ply Val: {cand['value']:.3f} | 1-Ply Sim Val: {avg_expected_value:.3f}")

            if avg_expected_value > best_expected_value:
                best_expected_value = avg_expected_value
                best_candidate = cand_move

        return best_candidate, best_expected_value

if __name__ == "__main__":
    # Test script for Phase 3
    print("Testing Phase 3 MCTS Search...")
    eng = inference.AlphableInference(model_path=None) # Uses untrained random weights for testing

    # Create dummy board and rack
    test_board = simulator.create_empty_board()
    test_rack = ['A', 'B', 'C', 'D', 'E', 'F', 'G']

    searcher = AlphableSearch(eng, num_simulations=3, top_k_candidates=2)
    best_move, best_val = searcher.find_best_move(test_board, test_rack, score_diff=0, bag_remaining=100)

    if best_move:
        print(f"\nPhase 3 Search Complete.")
        print(f"Chosen Move: {best_move['word']} at ({best_move['row']}, {best_move['col']}, {best_move['dir']})")
        print(f"Expected Win Probability: {best_val:.3f}")
