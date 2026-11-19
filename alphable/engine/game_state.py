"""
Alphable V4 Game State Representation.

Encapsulates 15x15 Scrabble board state, player racks, scores, unseen tile tracking,
conversion to/from CGP (Compact Game Position), and tensor encoding for the V4
Value Network (32-channel board tensor + 64-dim state vector).
"""

from __future__ import annotations
import copy
from typing import List, Dict, Tuple, Optional, Any
from collections import Counter
import numpy as np
import torch

from alphable.engine.move import Move

# Standard Scrabble English tile distribution (100 tiles)
STANDARD_TILE_COUNTS: Dict[str, int] = {
    'A': 9, 'B': 2, 'C': 2, 'D': 4, 'E': 12, 'F': 2, 'G': 3, 'H': 2,
    'I': 9, 'J': 1, 'K': 1, 'L': 4, 'M': 2, 'N': 6, 'O': 8, 'P': 2,
    'Q': 1, 'R': 6, 'S': 4, 'T': 6, 'U': 4, 'V': 2, 'W': 2, 'X': 1,
    'Y': 2, 'Z': 1, '?': 2
}

STANDARD_TILE_VALUES: Dict[str, int] = {
    'A': 1, 'B': 3, 'C': 3, 'D': 2, 'E': 1, 'F': 4, 'G': 2, 'H': 4,
    'I': 1, 'J': 8, 'K': 5, 'L': 1, 'M': 3, 'N': 1, 'O': 1, 'P': 3,
    'Q': 10, 'R': 1, 'S': 1, 'T': 1, 'U': 1, 'V': 4, 'W': 4, 'X': 8,
    'Y': 4, 'Z': 10, '?': 0
}
TILE_VALUES = STANDARD_TILE_VALUES

VOWELS = set("AEIOUY")

# Premium square coordinates on 15x15 board
TW_SQUARES = {
    (0, 0), (0, 7), (0, 14),
    (7, 0), (7, 14),
    (14, 0), (14, 7), (14, 14)
}

DW_SQUARES = {
    (1, 1), (2, 2), (3, 3), (4, 4),
    (1, 13), (2, 12), (3, 11), (4, 10),
    (13, 1), (12, 2), (11, 3), (10, 4),
    (13, 13), (12, 12), (11, 11), (10, 10),
    (7, 7)
}

TL_SQUARES = {
    (1, 5), (1, 9),
    (5, 1), (5, 5), (5, 9), (5, 13),
    (9, 1), (9, 5), (9, 9), (9, 13),
    (13, 5), (13, 9)
}

DL_SQUARES = {
    (0, 3), (0, 11),
    (2, 6), (2, 8),
    (3, 0), (3, 7), (3, 14),
    (6, 2), (6, 6), (6, 8), (6, 12),
    (7, 3), (7, 11),
    (8, 2), (8, 6), (8, 8), (8, 12),
    (11, 0), (11, 7), (11, 14),
    (12, 6), (12, 8),
    (14, 3), (14, 11)
}


class GameState:
    """
    Scrabble game state representation.
    """
    def __init__(
        self,
        board: Optional[List[List[Optional[str]]]] = None,
        rack: Optional[List[str]] = None,
        opp_rack: Optional[List[str]] = None,
        score: int = 0,
        opp_score: int = 0,
        scoreless_turns: int = 0,
        bag_count: int = 86,
        unseen_counts: Optional[Dict[str, int]] = None,
        lexicon: str = "CSW24",
    ):
        # 15x15 board: None if empty, uppercase 'A'-'Z' for standard tile,
        # lowercase 'a'-'z' for designated blank tile
        if board is None:
            self.board = [[None for _ in range(15)] for _ in range(15)]
        else:
            self.board = [row[:] for row in board]

        self.rack = [r.upper() for r in rack] if rack else []
        self.opp_rack = [r.upper() for r in opp_rack] if opp_rack else []
        self.score = score
        self.opp_score = opp_score
        self.scoreless_turns = scoreless_turns
        self.bag_count = bag_count
        self.lexicon = lexicon

        if unseen_counts is not None:
            self.unseen_counts = copy.copy(unseen_counts)
        else:
            self.unseen_counts = self._compute_unseen_counts()

    def _compute_unseen_counts(self) -> Dict[str, int]:
        """Calculates unseen tiles from standard tile pool minus board and our rack."""
        counts = copy.copy(STANDARD_TILE_COUNTS)
        # Deduct board tiles
        for r in range(15):
            for c in range(15):
                tile = self.board[r][c]
                if tile is not None and tile != ".":
                    if tile.islower():
                        counts['?'] = max(0, counts.get('?', 0) - 1)
                    else:
                        counts[tile.upper()] = max(0, counts.get(tile.upper(), 0) - 1)

        # Deduct our rack tiles
        for r in self.rack:
            counts[r] = max(0, counts.get(r, 0) - 1)

        return counts

    def to_cgp(self) -> str:
        """
        Encodes the state into standard Compact Game Position (CGP) format:
        <board_fen> <rack1>/<rack2> <score1>/<score2> <scoreless_turns> -lex <lexicon>
        Example:
        15/15/15/15/15/15/15/7A7/15/15/15/15/15/15/15 AEINRST/ 0/0 0 -lex CSW24
        """
        row_strs = []
        for r in range(15):
            curr_str = []
            empty_count = 0
            for c in range(15):
                tile = self.board[r][c]
                if tile is None or tile == ".":
                    empty_count += 1
                else:
                    if empty_count > 0:
                        curr_str.append(str(empty_count))
                        empty_count = 0
                    curr_str.append(tile)
            if empty_count > 0:
                curr_str.append(str(empty_count))
            row_strs.append("".join(curr_str))

        board_cgp = "/".join(row_strs)
        rack1_str = "".join(self.rack)
        rack2_str = "".join(self.opp_rack)
        racks_cgp = f"{rack1_str}/{rack2_str}"
        scores_cgp = f"{self.score}/{self.opp_score}"

        return f"{board_cgp} {racks_cgp} {scores_cgp} {self.scoreless_turns} -lex {self.lexicon}"

    @classmethod
    def from_cgp(cls, cgp_str: str) -> GameState:
        """Parses a CGP string into a GameState object."""
        parts = cgp_str.strip().split()
        if len(parts) < 4:
            raise ValueError(f"Invalid CGP string: {cgp_str}")

        board_part = parts[0]
        racks_part = parts[1]
        scores_part = parts[2]
        scoreless_part = int(parts[3])

        lexicon = "CSW24"
        if len(parts) >= 6 and parts[4] in ("-lex", "-l"):
            lexicon = parts[5]

        # Parse board rows
        rows = board_part.split("/")
        if len(rows) != 15:
            raise ValueError(f"CGP board must have 15 rows, got {len(rows)}")

        board: List[List[Optional[str]]] = [[None for _ in range(15)] for _ in range(15)]
        for r_idx, row_str in enumerate(rows):
            col_idx = 0
            idx = 0
            while idx < len(row_str) and col_idx < 15:
                ch = row_str[idx]
                if ch.isdigit():
                    # Might be 2-digit number (e.g. '15')
                    num_str = ch
                    if idx + 1 < len(row_str) and row_str[idx + 1].isdigit():
                        idx += 1
                        num_str += row_str[idx]
                    count = int(num_str)
                    col_idx += count
                else:
                    board[r_idx][col_idx] = ch
                    col_idx += 1
                idx += 1

        # Parse racks
        rack1_str, rack2_str = racks_part.split("/", 1)
        rack = list(rack1_str)
        opp_rack = list(rack2_str) if rack2_str else []

        # Parse scores
        score1_str, score2_str = scores_part.split("/", 1)
        score1 = int(score1_str)
        score2 = int(score2_str)

        state = cls(
            board=board,
            rack=rack,
            opp_rack=opp_rack,
            score=score1,
            opp_score=score2,
            scoreless_turns=scoreless_part,
            lexicon=lexicon,
        )
        return state

    def to_board_tensor(self) -> torch.Tensor:
        """
        Generates 32-channel (32, 15, 15) board tensor:
        Channels 0-25: One-hot letter planes A-Z
        Channel 26: Designated blank tiles on board
        Channels 27-30: Open dynamic premium squares (DL, TL, DW, TW) - 1.0 if empty, 0.0 if covered
        Channel 31: Rack overlap plane (letters on our rack that appear on board)
        """
        tensor = np.zeros((32, 15, 15), dtype=np.float32)

        rack_letters = set(self.rack)

        for r in range(15):
            for c in range(15):
                tile = self.board[r][c]
                is_empty = tile is None or tile == "."

                # Dynamic premium squares: 1.0 if empty, 0.0 if covered
                if is_empty:
                    if (r, c) in DL_SQUARES:
                        tensor[27, r, c] = 1.0
                    if (r, c) in TL_SQUARES:
                        tensor[28, r, c] = 1.0
                    if (r, c) in DW_SQUARES:
                        tensor[29, r, c] = 1.0
                    if (r, c) in TW_SQUARES:
                        tensor[30, r, c] = 1.0
                else:
                    # Tile on board
                    if tile.islower():
                        # Blank tile representing a letter
                        letter_idx = ord(tile.upper()) - ord('A')
                        if 0 <= letter_idx < 26:
                            tensor[letter_idx, r, c] = 1.0
                        tensor[26, r, c] = 1.0  # Blank indicator
                    else:
                        letter_idx = ord(tile.upper()) - ord('A')
                        if 0 <= letter_idx < 26:
                            tensor[letter_idx, r, c] = 1.0

                    # Channel 31: Rack letter overlap (bingo anchor opportunities)
                    if tile.upper() in rack_letters:
                        tensor[31, r, c] = 1.0

        return torch.from_numpy(tensor)

    def to_state_vector(self, belief_confidence: float = 0.0) -> torch.Tensor:
        """
        Generates 64-dimensional game state feature vector:
        0-25: Counts of A-Z tiles in our rack
        26: Count of blank '?' tiles in our rack
        27: Normalized score differential (score - opp_score) / 500.0
        28: Normalized bag remaining count / 100.0
        29: Leave length / 7.0
        30: Vowel count / 7.0
        31: Consonant count / 7.0
        32: Has blank (1.0 or 0.0)
        33: Has 'S' (1.0 or 0.0)
        34: Duplicate letter penalty / 7.0
        35: Empty leave flag (1.0 if rack is empty)
        36-61: Unseen tile ratios for A-Z (unseen_count / standard_count)
        62: Unseen blank '?' ratio (unseen_count / 2.0)
        63: Bayesian rack inference confidence score [0.0, 1.0]
        """
        vec = np.zeros(64, dtype=np.float32)

        vowel_count = 0
        consonant_count = 0
        counts: Dict[str, int] = {}

        for char in self.rack:
            upper = char.upper()
            if upper == '?':
                vec[26] += 1.0
            else:
                idx = ord(upper) - ord('A')
                if 0 <= idx < 26:
                    vec[idx] += 1.0
                    counts[upper] = counts.get(upper, 0) + 1
                    if upper in VOWELS:
                        vowel_count += 1
                    else:
                        consonant_count += 1

        # Normalized score and bag
        score_diff = self.score - self.opp_score
        vec[27] = float(score_diff) / 500.0
        vec[28] = float(self.bag_count) / 100.0

        # Rack strategic metrics
        leave_len = len(self.rack)
        vec[29] = leave_len / 7.0
        vec[30] = vowel_count / 7.0
        vec[31] = consonant_count / 7.0
        vec[32] = 1.0 if vec[26] > 0 else 0.0
        vec[33] = 1.0 if vec[18] > 0 else 0.0  # S is index 18

        # Duplicate letter penalty
        dup_penalty = sum(max(0, count - 1) for count in counts.values())
        vec[34] = dup_penalty / 7.0
        vec[35] = 1.0 if leave_len == 0 else 0.0

        # Unseen bag tracking features
        for i, char in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
            std_cnt = STANDARD_TILE_COUNTS.get(char, 1)
            vec[36 + i] = self.unseen_counts.get(char, 0) / float(std_cnt)
        vec[62] = self.unseen_counts.get('?', 0) / 2.0

        # V4 Feature: Bayesian belief confidence score
        vec[63] = float(belief_confidence)

        return torch.from_numpy(vec)

    def apply_move(self, move: Move, drawn_tiles: Optional[List[str]] = None) -> GameState:
        """
        Returns a new GameState with move applied and next player on turn.
        """
        new_board = [row[:] for row in self.board]
        new_score = self.score
        new_scoreless = self.scoreless_turns
        remaining_rack = list(self.rack)

        if move.is_pass:
            new_scoreless += 1
        elif move.is_exchange:
            new_scoreless += 1
            # Deduct exchanged letters from rack
            for tile in move.word:
                if tile in remaining_rack:
                    remaining_rack.remove(tile)
        else:
            new_scoreless = 0
            new_score += move.score

            # Place tiles on board and remove played tiles from rack
            r = move.row
            c = move.col
            dir_str = move.direction
            tiles_to_place = move.word

            curr_r = r
            curr_c = c
            for ch in tiles_to_place:
                # If board cell is empty, place tile
                if new_board[curr_r][curr_c] is None:
                    new_board[curr_r][curr_c] = ch
                    # Deduct from rack
                    if ch.islower():
                        if '?' in remaining_rack:
                            remaining_rack.remove('?')
                    else:
                        if ch.upper() in remaining_rack:
                            remaining_rack.remove(ch.upper())

                if dir_str == "Across":
                    curr_c += 1
                else:
                    curr_r += 1

        # Add newly drawn tiles if provided
        if drawn_tiles:
            remaining_rack.extend([t.upper() for t in drawn_tiles])

        # Swap players: our score becomes opp_score for the next turn
        return GameState(
            board=new_board,
            rack=self.opp_rack,
            opp_rack=remaining_rack,
            score=self.opp_score,
            opp_score=new_score,
            scoreless_turns=new_scoreless,
            bag_count=max(0, self.bag_count - len(drawn_tiles or [])),
            lexicon=self.lexicon,
        )
