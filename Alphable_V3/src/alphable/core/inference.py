import torch
import numpy as np
from alphable.core import structure
from alphable.core import simulator
from alphable.core.alphable_net import AlphableValueNet

def board_to_tensor(board):
    """
    Converts a 15x15 board state into a [31, 15, 15] tensor.
    Channels:
      0-25: A-Z letters (one-hot)
      26: Blanks
      27: Double Letter (DL)
      28: Triple Letter (TL)
      29: Double Word (DW)
      30: Triple Word (TW)
    """
    arr = np.zeros((31, 15, 15), dtype=np.float32)

    # Static Premium Squares Channels
    for (r, c), prem in simulator.PREMIUM_SQUARES.items():
        if prem == 'DL':
            arr[27, r, c] = 1.0
        elif prem == 'TL':
            arr[28, r, c] = 1.0
        elif prem == 'DW':
            arr[29, r, c] = 1.0
        elif prem == 'TW':
            arr[30, r, c] = 1.0

    for r in range(15):
        for c in range(15):
            char = board[r][c]
            if char != '.':
                if char.islower():
                    # It's a blank tile representing a letter
                    arr[26, r, c] = 1.0
                    idx = ord(char.upper()) - 65
                    arr[idx, r, c] = 1.0
                else:
                    # Regular letter tile
                    idx = ord(char) - 65
                    arr[idx, r, c] = 1.0

    return torch.from_numpy(arr)

def state_to_tensor(rack, score_diff, bag_remaining):
    """
    Converts the game state into a [29] tensor.
    Elements:
      0-25: Counts of A-Z tiles in rack
      26: Count of blank tiles in rack
      27: Score differential (normalized somewhat)
      28: Bag remaining (normalized)
    """
    arr = np.zeros(29, dtype=np.float32)

    # Rack counts
    for char in rack:
        if char == '?':
            arr[26] += 1.0
        else:
            idx = ord(char) - 65
            arr[idx] += 1.0

    # Normalize score diff (e.g. max diff roughly 500, scale to roughly [-1, 1])
    arr[27] = score_diff / 500.0

    # Normalize bag remaining (total tiles = 100)
    arr[28] = bag_remaining / 100.0

    return torch.from_numpy(arr)

class AlphableInference:
    def __init__(self, model_path=None, device='cpu', dict_path='resources/NWL2023.txt'):
        self.device = torch.device(device)
        self.model = AlphableValueNet().to(self.device)
        if model_path:
            self.model.load_state_dict(torch.load(model_path, map_location=self.device, weights_only=True))
        self.model.eval()

        # Load GADDAG (using NWL2023 or CSW24 which exist in the directory)
        self.gaddag = structure.Gaddag.load(dict_path)
        self.move_gen = structure.MoveGenerator(self.gaddag)

    def find_best_move(self, current_board, rack, current_score_diff, bag_remaining):
        """
        Generates legal moves, simulates after-states, and selects the one with the highest win probability.

        Args:
            current_board: 15x15 list of lists
            rack: list of chars (e.g., ['A', 'B', '?', 'E', 'Z'])
            current_score_diff: Int (My Score - Opponent Score)
            bag_remaining: Int

        Returns:
            best_move: Dict representing the best move
            best_value: Float (Predicted Win Probability)
        """
        # 1. Generate Legal Moves
        moves = self.move_gen.generate(current_board, rack)

        if not moves:
            return None, 0.0 # No legal moves (Pass or Exchange)

        # 2. Simulate After-States
        batch_boards = []
        batch_states = []

        for move in moves:
            new_board, points, new_rack = simulator.simulate_move(current_board, move, rack)

            # The new score diff is updated assuming we just scored `points`
            new_score_diff = current_score_diff + points

            board_tensor = board_to_tensor(new_board)
            state_tensor = state_to_tensor(new_rack, new_score_diff, bag_remaining)

            batch_boards.append(board_tensor)
            batch_states.append(state_tensor)

        # Stack into batches: [B, 31, 15, 15] and [B, 29]
        batch_boards_tensor = torch.stack(batch_boards).to(self.device)
        batch_states_tensor = torch.stack(batch_states).to(self.device)

        # 3. Neural Network Forward Pass
        with torch.no_grad():
            # Output is [B, 1]
            win_probs = self.model(batch_boards_tensor, batch_states_tensor)

        # 4. Find max value
        best_idx = torch.argmax(win_probs).item()
        best_move = moves[best_idx]
        best_value = win_probs[best_idx].item()

        return best_move, best_value
