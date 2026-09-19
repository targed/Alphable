import torch
import numpy as np
from alphable.core import structure
from alphable.core import simulator
from alphable.core.alphable_net import AlphableValueNet, load_checkpoint_compatible

VOWELS = set('AEIOU')

STATIC_PREMIUM_MASK = np.zeros((4, 15, 15), dtype=np.float32)
for (r, c), prem in simulator.PREMIUM_SQUARES.items():
    if prem == 'DL':
        STATIC_PREMIUM_MASK[0, r, c] = 1.0
    elif prem == 'TL':
        STATIC_PREMIUM_MASK[1, r, c] = 1.0
    elif prem == 'DW':
        STATIC_PREMIUM_MASK[2, r, c] = 1.0
    elif prem == 'TW':
        STATIC_PREMIUM_MASK[3, r, c] = 1.0


def board_to_tensor(board):
    """
    Converts a 15x15 board state into a [31, 15, 15] tensor.
    Channels:
      0-25: A-Z letters (one-hot)
      26: Blanks
      27: Open Double Letter (DL)
      28: Open Triple Letter (TL)
      29: Open Double Word (DW)
      30: Open Triple Word (TW)
    """
    arr = np.zeros((31, 15, 15), dtype=np.float32)
    # Bulk initialize open premium squares
    arr[27:31] = STATIC_PREMIUM_MASK

    for r in range(15):
        row = board[r]
        for c in range(15):
            char = row[c]
            if char != '.':
                # Premium is covered / deactivated once occupied
                arr[27:31, r, c] = 0.0
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
    Converts the game state into an enriched [36] tensor.
    Elements:
      0-25: Counts of A-Z tiles in rack
      26: Count of blank tiles in rack
      27: Score differential (normalized to roughly [-1, 1])
      28: Bag remaining (normalized to [0, 1])
      29: Leave size / 7.0
      30: Vowel count / 7.0
      31: Consonant count / 7.0
      32: Has blank (1.0 or 0.0)
      33: Has S (1.0 or 0.0)
      34: Duplicate letter penalty / 7.0
      35: Empty leave flag (1.0 if bingo/out else 0.0)
    """
    arr = np.zeros(36, dtype=np.float32)

    vowel_count = 0
    consonant_count = 0
    has_blank = 0.0
    has_s = 0.0
    counts = {}

    for char in rack:
        upper = char.upper()
        if upper == '?':
            arr[26] += 1.0
            has_blank = 1.0
        else:
            idx = ord(upper) - 65
            if 0 <= idx < 26:
                arr[idx] += 1.0
                counts[upper] = counts.get(upper, 0) + 1
                if upper in VOWELS:
                    vowel_count += 1
                else:
                    consonant_count += 1
                if upper == 'S':
                    has_s = 1.0

    # Basic state normalization
    arr[27] = score_diff / 500.0
    arr[28] = bag_remaining / 100.0

    # Strategic leave metrics
    leave_len = len(rack)
    arr[29] = leave_len / 7.0
    arr[30] = vowel_count / 7.0
    arr[31] = consonant_count / 7.0
    arr[32] = has_blank
    arr[33] = has_s

    # Duplicate letter penalty (e.g. holding multiple I's or U's or V's)
    dup_penalty = sum(max(0, count - 1) for count in counts.values())
    arr[34] = dup_penalty / 7.0
    arr[35] = 1.0 if leave_len == 0 else 0.0

    return torch.from_numpy(arr)

class AlphableInference:
    def __init__(self, model_path=None, device='cpu', dict_path='resources/NWL2023.txt', value_weight=60.0):
        self.device = torch.device(device)
        self.value_weight = float(value_weight)
        self.model = AlphableValueNet().to(self.device)
        if model_path:
            load_checkpoint_compatible(self.model, model_path, self.device)
        self.model.eval()

        # Load GADDAG (using NWL2023 or CSW24 which exist in the directory)
        self.gaddag = structure.Gaddag.load(dict_path)
        self.move_gen = structure.MoveGenerator(self.gaddag)

    def find_best_move(self, current_board, rack, current_score_diff, bag_remaining):
        """
        Generates legal moves, simulates after-states, and selects the move with highest equity.

        Args:
            current_board: 15x15 list of lists
            rack: list of chars (e.g., ['A', 'B', '?', 'E', 'Z'])
            current_score_diff: Int (My Score - Opponent Score)
            bag_remaining: Int

        Returns:
            best_move: Dict representing the best move
            best_value: Float (Predicted Win Probability / Value)
        """
        # 1. Generate Legal Moves
        moves = self.move_gen.generate(current_board, rack)

        if not moves:
            return None, 0.0 # No legal moves (Pass or Exchange)

        # 2. Simulate After-States
        batch_boards = []
        batch_states = []
        move_points = []

        for move in moves:
            new_board, points, new_rack = simulator.simulate_move(current_board, move, rack)

            # The new score diff is updated assuming we just scored `points`
            new_score_diff = current_score_diff + points

            board_tensor = board_to_tensor(new_board)
            state_tensor = state_to_tensor(new_rack, new_score_diff, bag_remaining)

            batch_boards.append(board_tensor)
            batch_states.append(state_tensor)
            move_points.append(points)

        # Stack into batches: [B, 31, 15, 15] and [B, 36]
        batch_boards_tensor = torch.stack(batch_boards).to(self.device)
        batch_states_tensor = torch.stack(batch_states).to(self.device)

        # 3. Neural Network Forward Pass
        with torch.no_grad():
            # Output is [B]
            win_probs = self.model(batch_boards_tensor, batch_states_tensor).view(-1)

        # 4. Rank by Equity = Points + value_weight * Value
        equities = torch.tensor(move_points, dtype=torch.float32, device=self.device) + self.value_weight * win_probs
        best_idx = torch.argmax(equities).item()
        best_move = moves[best_idx]
        best_value = win_probs[best_idx].item()

        return best_move, best_value
