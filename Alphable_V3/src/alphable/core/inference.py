import os
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

STANDARD_TILE_COUNTS = {
    'A': 9, 'B': 2, 'C': 2, 'D': 4, 'E': 12, 'F': 2, 'G': 3, 'H': 2,
    'I': 9, 'J': 1, 'K': 1, 'L': 4, 'M': 2, 'N': 6, 'O': 8, 'P': 2,
    'Q': 1, 'R': 6, 'S': 4, 'T': 6, 'U': 4, 'V': 2, 'W': 2, 'X': 1,
    'Y': 2, 'Z': 1, '?': 2,
}


def state_to_tensor(rack, score_diff, bag_remaining, unseen_counts=None, state_vector_size=36):
    """
    Converts the game state into an enriched tensor of size state_vector_size (default 36 or 63).
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
      36-61 (when state_vector_size >= 63): Unseen A-Z ratios (unseen_count / standard_count)
      62 (when state_vector_size >= 63): Unseen blank '?' ratio (unseen_count / 2.0)
    """
    arr = np.zeros(state_vector_size, dtype=np.float32)

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

    # 36-62: Unseen tile distribution features (Bag tracking)
    if state_vector_size >= 63 and unseen_counts is not None:
        for i, char in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
            std_cnt = STANDARD_TILE_COUNTS.get(char, 1)
            arr[36 + i] = unseen_counts.get(char, 0) / float(std_cnt)
        arr[62] = unseen_counts.get('?', 0) / 2.0

    return torch.from_numpy(arr)


def resolve_path(path: str | None) -> str | None:
    """
    Resolves relative filepaths across different execution working directories
    (e.g., repository root Documents/Git/Alphable vs package root Alphable_V3),
    and handles common dictionary aliases (e.g., NWL23 vs NWL2023).
    """
    if not path:
        return path
    if os.path.exists(path):
        return path
    alt_v3 = os.path.join("Alphable_V3", path)
    if os.path.exists(alt_v3):
        return alt_v3
    alt_parent = os.path.join("..", path)
    if os.path.exists(alt_parent):
        return alt_parent

    # Check common lexicon aliases (NWL23 <-> NWL2023)
    if "NWL23" in path:
        alt_nwl = path.replace("NWL23", "NWL2023")
        res = resolve_path(alt_nwl)
        if res and os.path.exists(res):
            return res
    if "NWL2023" in path:
        alt_nwl = path.replace("NWL2023", "NWL23")
        res = resolve_path(alt_nwl)
        if res and os.path.exists(res):
            return res

    # Check if raw lexicon name was passed (e.g. "CSW24" or "NWL23")
    if not path.endswith(".txt") and "/" not in path and "\\" not in path:
        res_txt = os.path.join("resources", f"{path}.txt")
        res = resolve_path(res_txt)
        if res and os.path.exists(res):
            return res

    return path


class AlphableInference:
    def __init__(self, model_path=None, device='cpu', dict_path='resources/NWL2023.txt', value_weight=25.0, state_vector_size=36):
        self.device = torch.device(device)
        self.value_weight = float(value_weight)
        self.state_vector_size = state_vector_size
        self.model = AlphableValueNet(state_vector_size=state_vector_size).to(self.device)
        model_path = resolve_path(model_path)
        if model_path and os.path.exists(model_path):
            load_checkpoint_compatible(self.model, model_path, self.device)
        self.model.eval()

        # Load GADDAG (using NWL2023 or CSW24 which exist in the directory)
        dict_path = resolve_path(dict_path)
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
