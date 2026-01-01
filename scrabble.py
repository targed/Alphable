import pyspiel
import copy
import numpy as np
import collections
from structure import Gaddag, MoveGenerator

# Game Configuration
_NUM_PLAYERS = 2
_BOARD_SIZE = 15
_SHARED_GADDAG = None
_GAME_TYPE = pyspiel.GameType(
    short_name="scrabble",
    long_name="Scrabble (North American)",
    dynamics=pyspiel.GameType.Dynamics.SEQUENTIAL,
    chance_mode=pyspiel.GameType.ChanceMode.EXPLICIT_STOCHASTIC, # For tile drawing
    information=pyspiel.GameType.Information.IMPERFECT_INFORMATION,
    utility=pyspiel.GameType.Utility.ZERO_SUM,
    reward_model=pyspiel.GameType.RewardModel.TERMINAL, # Or rewards per turn
    max_num_players=_NUM_PLAYERS,
    min_num_players=_NUM_PLAYERS,
    provides_information_state_string=True,
    provides_information_state_tensor=True,
    provides_observation_string=True,
    provides_observation_tensor=True,
    parameter_specification={}
)

_GAME_INFO = pyspiel.GameInfo(
    num_distinct_actions=100000,  # Large action space for Scrabble
    max_chance_outcomes=100,  # Drawing tiles from bag
    num_players=_NUM_PLAYERS,
    min_utility=-1000.0,  # Conservative estimate for score differences
    max_utility=1000.0,
    utility_sum=0.0,  # Zero-sum game
    max_game_length=500  # Rough upper bound on number of moves
)
# Standard Tile Values
TILE_VALUES = {
    'A': 1, 'B': 3, 'C': 3, 'D': 2, 'E': 1, 'F': 4, 'G': 2, 'H': 4, 'I': 1, 
    'J': 8, 'K': 5, 'L': 1, 'M': 3, 'N': 1, 'O': 1, 'P': 3, 'Q': 10, 'R': 1, 
    'S': 1, 'T': 1, 'U': 1, 'V': 4, 'W': 4, 'X': 8, 'Y': 4, 'Z': 10, '?': 0, '.': 0
}

# Standard Bag Distribution (Letter, Count)
BAG_DISTRIBUTION = [
    ('A', 9), ('B', 2), ('C', 2), ('D', 4), ('E', 12), ('F', 2), ('G', 3), 
    ('H', 2), ('I', 9), ('J', 1), ('K', 1), ('L', 4), ('M', 2), ('N', 6), 
    ('O', 8), ('P', 2), ('Q', 1), ('R', 6), ('S', 4), ('T', 6), ('U', 4), 
    ('V', 2), ('W', 2), ('X', 1), ('Y', 2), ('Z', 1), ('?', 2)
]

# Premium Squares: (Row, Col) -> Multiplier Type
# 1=DL, 2=TL, 3=DW, 4=TW
PREMIUMS = {}
# Initialize standard layout (Partial visualization)
# Triple Word (TW)
for r, c in [(0,0), (0,7), (0,14), (7,0), (7,14), (14,0), (14,7), (14,14)]:
    PREMIUMS[(r,c)] = ('W', 3)
# Double Word (DW)
for r in [1, 2, 3, 4, 10, 11, 12, 13]:
    PREMIUMS[(r, r)] = ('W', 2)
    PREMIUMS[(r, 14-r)] = ('W', 2)
PREMIUMS[(7,7)] = ('W', 2) # Center star
# Triple Letter (TL)
for r, c in [(1,5), (1,9), (5,1), (5,5), (5,9), (5,13), 
             (9,1), (9,5), (9,9), (9,13), (13,5), (13,9)]:
    PREMIUMS[(r,c)] = ('L', 3)
# Double Letter (DL) - Fill in the rest explicitly or procedurally
DL_COORDS = [
    (0,3), (0,11), (2,6), (2,8), (3,0), (3,7), (3,14), (6,2), (6,6), (6,8), (6,12),
    (7,3), (7,11), (8,2), (8,6), (8,8), (8,12), (11,0), (11,7), (11,14),
    (12,6), (12,8), (14,3), (14,11)
]
for r, c in DL_COORDS:
    PREMIUMS[(r,c)] = ('L', 2)

class ScrabbleGame(pyspiel.Game):
    def __init__(self, params=None):
        super().__init__(_GAME_TYPE, _GAME_INFO, params if params else {})
        
        # Load GADDAG only once per process
        global _SHARED_GADDAG
        if _SHARED_GADDAG is None:
            _SHARED_GADDAG = Gaddag.load("resources/NWL2023.txt")
            
        self.gaddag = _SHARED_GADDAG
        self.move_gen = MoveGenerator(self.gaddag)
        
    def num_distinct_actions(self):
        return 452

    def observation_tensor_shape(self):
        return [35, 15, 15]

    def new_initial_state(self):
        return ScrabbleState(self)

class ScrabbleState(pyspiel.State):
    def __init__(self, game):
        super().__init__(game)
        # Use lists of characters for the board (easier for GADDAG)
        self.board = [['.' for _ in range(15)] for _ in range(15)]
        self.scores = [0.0, 0.0]
        self._game_over = False
        self._current_player = 0
        self._current_move_map = [] # Stores valid moves for the current turn
        self.consecutive_passes = 0
        self.consecutive_zero_scores = 0  # Track consecutive zero-score turns
        self.turn_count = 0
        
        # NEW: Track moves that failed validation this turn
        self.banned_actions = set() 
        
        # NEW: Track which premium squares have been used
        self.used_premiums = set()  # Set of (row, col) tuples for used premium squares
        
        # Logging attributes
        self.move_log = []  # List of move attempt records
        self.termination_reason = None  # Reason for game termination
        self.enable_logging = True  # Can be disabled for performance
        
        # Initialize Bag
        self.bag = []
        for letter, count in BAG_DISTRIBUTION:
            self.bag.extend([letter] * count)
        np.random.shuffle(self.bag) # Shuffle immediately
        
        # Draw initial racks (7 tiles each)
        self.racks = [[], []]
        self._refill_rack(0)
        self._refill_rack(1)
        
    def clone(self):
        """
        Critical for MCTS: Return a deep copy of the state.
        Without this, simulating moves corrupts the parent state's board.
        """
        return copy.deepcopy(self)

    def _refill_rack(self, player_idx):
        needed = 7 - len(self.racks[player_idx])
        if needed > 0 and self.bag:
            draw = [self.bag.pop() for _ in range(min(needed, len(self.bag)))]
            self.racks[player_idx].extend(draw)
    
    def apply_penalty(self, player_idx, penalty):
        """Apply penalty to player score, ensuring non-negative result"""
        self.scores[player_idx] = max(0.0, self.scores[player_idx] - penalty)
    
    def adjust_final_scores(self):
        """Apply end-game adjustments per official Scrabble rules"""
        # Calculate unplayed tile values for each player
        unplayed_values = [0, 0]
        for player_idx in range(2):
            for tile in self.racks[player_idx]:
                unplayed_values[player_idx] += TILE_VALUES.get(tile, 0)
        
        # Check if either player went out (used all tiles)
        player_went_out = -1
        for player_idx in range(2):
            if len(self.racks[player_idx]) == 0 and len(self.bag) == 0:
                player_went_out = player_idx
                break
        
        if player_went_out >= 0:
            # Player who went out gets opponent's unplayed tiles added
            opponent = 1 - player_went_out
            self.scores[player_went_out] += unplayed_values[opponent]
            self.scores[opponent] -= unplayed_values[opponent]
        else:
            # Both players subtract their own unplayed tiles
            for player_idx in range(2):
                self.scores[player_idx] -= unplayed_values[player_idx]
        
        # Ensure both scores remain non-negative
        self.scores[0] = max(0.0, self.scores[0])
        self.scores[1] = max(0.0, self.scores[1])

    def log_move_attempt(self, action_id, move_details, success, failure_reason=None):
        """Log a move attempt with details"""
        if not self.enable_logging:
            return
        
        log_entry = {
            'turn': self.turn_count,
            'player': self._current_player,
            'action_id': action_id,
            'move_details': move_details,
            'success': success,
            'failure_reason': failure_reason,
            'banned_actions_count': len(self.banned_actions)
        }
        self.move_log.append(log_entry)
    
    def log_termination(self, reason):
        """Log game termination with reason"""
        if not self.enable_logging:
            return
        
        self.termination_reason = reason
        self.move_log.append({
            'turn': self.turn_count,
            'event': 'GAME_TERMINATED',
            'reason': reason,
            'final_scores': list(self.scores),
            'consecutive_passes': self.consecutive_passes,
            'consecutive_zero_scores': self.consecutive_zero_scores
        })
    
    def get_move_log_summary(self):
        """Get a summary of the move log"""
        if not self.move_log:
            return "No moves logged"
        
        lines = []
        lines.append(f"Move Log Summary ({len(self.move_log)} entries)")
        lines.append("=" * 60)
        
        for entry in self.move_log[-10:]:  # Last 10 entries
            if 'event' in entry:
                lines.append(f"Turn {entry['turn']}: {entry['event']} - {entry['reason']}")
            else:
                status = "SUCCESS" if entry['success'] else "FAILED"
                lines.append(f"Turn {entry['turn']}, P{entry['player']}: {status} - Action {entry['action_id']}")
                if not entry['success'] and entry['failure_reason']:
                    lines.append(f"  Reason: {entry['failure_reason']}")
        
        return "\n".join(lines)

    def current_player(self):
        return self._current_player
    
    def validate_board_connectivity(self, row, col, word, direction):
        """
        Validate that the move connects to existing tiles on the board.
        For the first move, verify it covers the center square (7,7).
        For subsequent moves, verify it connects to at least one existing tile.
        
        Returns True if connectivity is valid, False otherwise.
        """
        dr, dc = (0, 1) if direction == 'Across' else (1, 0)
        is_first_move = (self.board[7][7] == '.')
        is_connected = False
        
        curr_r, curr_c = row, col
        for char in word:
            board_char = self.board[curr_r][curr_c]
            
            if board_char != '.':
                # Word uses existing tile - automatically connected
                is_connected = True
            else:
                # Check neighbors for connectivity
                if not is_connected:
                    for nr, nc in [(curr_r+1, curr_c), (curr_r-1, curr_c), 
                                   (curr_r, curr_c+1), (curr_r, curr_c-1)]:
                        if 0 <= nr < 15 and 0 <= nc < 15 and self.board[nr][nc] != '.':
                            is_connected = True
                            break
            
            # First move check: must cover center square
            if is_first_move and curr_r == 7 and curr_c == 7:
                is_connected = True
                
            curr_r += dr
            curr_c += dc
        
        return is_connected
    
    def validate_boundaries(self, row, col, word, direction):
        """
        Validate that all tiles in the word are within board boundaries [0, 14].
        
        Returns True if all coordinates are valid, False otherwise.
        """
        dr, dc = (0, 1) if direction == 'Across' else (1, 0)
        end_r = row + dr * (len(word) - 1)
        end_c = col + dc * (len(word) - 1)
        
        return (0 <= row < 15 and 0 <= col < 15 and 
                0 <= end_r < 15 and 0 <= end_c < 15)
    
    def validate_rack_availability(self, word, direction, row, col, rack):
        """
        Validate that the player has all required tiles in their rack.
        Handles blank tiles as wildcards.
        
        Returns (True, tiles_used) if valid, (False, None) otherwise.
        """
        dr, dc = (0, 1) if direction == 'Across' else (1, 0)
        tiles_needed = []
        
        curr_r, curr_c = row, col
        for char in word:
            board_char = self.board[curr_r][curr_c]
            
            if board_char == '.':
                # Must use from rack
                tiles_needed.append(char)
                
            curr_r += dr
            curr_c += dc
        
        # Rack Counting (Handle Blanks)
        rack_counts = collections.Counter(rack)
        final_tiles_used = []
        
        for char in tiles_needed:
            if rack_counts[char] > 0:
                rack_counts[char] -= 1
                final_tiles_used.append(char)
            elif rack_counts['?'] > 0:
                rack_counts['?'] -= 1
                final_tiles_used.append('?')  # Use blank
            else:
                return False, None  # Missing tile
        
        return True, final_tiles_used
    
    def validate_tile_matching(self, row, col, word, direction):
        """
        Validate that the word matches existing board tiles at their positions.
        
        Returns True if all existing tiles match, False otherwise.
        """
        dr, dc = (0, 1) if direction == 'Across' else (1, 0)
        
        curr_r, curr_c = row, col
        for char in word:
            board_char = self.board[curr_r][curr_c]
            
            if board_char != '.':
                # Must match existing tile
                if board_char != char:
                    return False
                    
            curr_r += dr
            curr_c += dc
        
        return True
    
    def _validate_move(self, row, col, word, direction, rack):
        """
        Returns (True, tiles_used) if valid, (False, None) otherwise.
        Checks: Boundaries, Connectivity, Rack availability, Tile matching, Cross-words.
        """
        # 1. Boundary Check
        if not self.validate_boundaries(row, col, word, direction):
            return False, None

        # 2. Tile Matching Check
        if not self.validate_tile_matching(row, col, word, direction):
            return False, None

        # 3. Connectivity Check
        if not self.validate_board_connectivity(row, col, word, direction):
            return False, None

        # 4. Rack Availability Check
        is_valid, tiles_used = self.validate_rack_availability(word, direction, row, col, rack)
        if not is_valid:
            return False, None

        # 5. Cross-word validation
        cross_words = self.find_cross_words(row, col, word, direction)
        if not self.validate_cross_words(cross_words):
            return False, None
        
        # 6. Adjacent word validation (same direction)
        adjacent_words = self.find_adjacent_words_same_direction(row, col, word, direction)
        if not self.validate_adjacent_words(adjacent_words):
            return False, None

        return True, tiles_used
    
    def find_cross_words(self, row, col, word, direction):
        """
        Find all cross-words formed perpendicular to the main word.
        Returns list of (cross_word, start_row, start_col, cross_direction) tuples.
        """
        cross_words = []
        dr, dc = (0, 1) if direction == 'Across' else (1, 0)
        cross_dr, cross_dc = (1, 0) if direction == 'Across' else (0, 1)
        
        curr_r, curr_c = row, col
        
        for char in word:
            # Only check tiles that will be newly placed
            if self.board[curr_r][curr_c] == '.':
                # Check if there are adjacent tiles perpendicular to main direction
                has_adjacent = False
                
                # Check before
                if 0 <= curr_r - cross_dr < 15 and 0 <= curr_c - cross_dc < 15:
                    if self.board[curr_r - cross_dr][curr_c - cross_dc] != '.':
                        has_adjacent = True
                
                # Check after
                if 0 <= curr_r + cross_dr < 15 and 0 <= curr_c + cross_dc < 15:
                    if self.board[curr_r + cross_dr][curr_c + cross_dc] != '.':
                        has_adjacent = True
                
                if has_adjacent:
                    # Extract the full cross-word
                    # Scan backwards to find start
                    start_r, start_c = curr_r, curr_c
                    while 0 <= start_r - cross_dr < 15 and 0 <= start_c - cross_dc < 15:
                        if self.board[start_r - cross_dr][start_c - cross_dc] != '.':
                            start_r -= cross_dr
                            start_c -= cross_dc
                        else:
                            break
                    
                    # Scan forwards to build the word
                    cross_word = ""
                    scan_r, scan_c = start_r, start_c
                    while 0 <= scan_r < 15 and 0 <= scan_c < 15:
                        if (scan_r, scan_c) == (curr_r, curr_c):
                            # This is the tile we're placing
                            cross_word += char
                        else:
                            tile = self.board[scan_r][scan_c]
                            if tile == '.':
                                break
                            cross_word += tile
                        
                        scan_r += cross_dr
                        scan_c += cross_dc
                    
                    # Only add if it's more than 1 letter (a real word)
                    if len(cross_word) > 1:
                        cross_dir = 'Down' if direction == 'Across' else 'Across'
                        cross_words.append((cross_word, start_r, start_c, cross_dir))
            
            curr_r += dr
            curr_c += dc
        
        return cross_words
    
    def validate_cross_words(self, cross_words):
        """
        Validate all cross-words using GADDAG.
        Returns True only if all cross-words are valid.
        """
        if not cross_words:
            return True
        
        gaddag = self.get_game().gaddag
        for cross_word, _, _, _ in cross_words:
            # Use GADDAG's fast word check
            if not self._fast_word_check(cross_word, gaddag):
                return False
        
        return True
    
    def _fast_word_check(self, word, gaddag):
        """Check if word is in dictionary using GADDAG"""
        path = word[::-1] + '>'
        curr = gaddag.root
        for char in path:
            if char not in curr:
                return False
            curr = curr[char]
        return '$' in curr
    
    def find_adjacent_words_same_direction(self, row, col, word, direction):
        """
        Find words that would be formed by placing tiles adjacent to existing tiles
        in the SAME direction (parallel placement).
        
        This catches cases like placing "JOES" next to "BOXERS" which would create
        the invalid word "BOXERSJOES".
        
        Returns list of (combined_word, start_row, start_col, direction) tuples.
        """
        adjacent_words = []
        dr, dc = (0, 1) if direction == 'Across' else (1, 0)
        
        # First, check if there are tiles immediately before OR after
        before_r, before_c = row - dr, col - dc
        has_before = (0 <= before_r < 15 and 0 <= before_c < 15 and 
                     self.board[before_r][before_c] != '.')
        
        end_r = row + dr * len(word)
        end_c = col + dc * len(word)
        has_after = (0 <= end_r < 15 and 0 <= end_c < 15 and 
                    self.board[end_r][end_c] != '.')
        
        if not has_before and not has_after:
            # No adjacent tiles in same direction
            return []
        
        # Build the complete combined word
        combined_word = ""
        start_r, start_c = row, col
        
        # If there are tiles before, scan back to find the start
        if has_before:
            start_r, start_c = before_r, before_c
            while 0 <= start_r - dr < 15 and 0 <= start_c - dc < 15:
                if self.board[start_r - dr][start_c - dc] != '.':
                    start_r -= dr
                    start_c -= dc
                else:
                    break
            
            # Build word from start to the position where we're placing
            scan_r, scan_c = start_r, start_c
            while (scan_r, scan_c) != (row, col):
                combined_word += self.board[scan_r][scan_c]
                scan_r += dr
                scan_c += dc
        
        # Add the new word
        combined_word += word
        
        # If there are tiles after, add them
        if has_after:
            scan_r, scan_c = end_r, end_c
            while 0 <= scan_r < 15 and 0 <= scan_c < 15 and self.board[scan_r][scan_c] != '.':
                combined_word += self.board[scan_r][scan_c]
                scan_r += dr
                scan_c += dc
        
        adjacent_words.append((combined_word, start_r, start_c, direction))
        return adjacent_words
    
    def validate_adjacent_words(self, adjacent_words):
        """
        Validate all adjacent words (same direction) using GADDAG.
        Returns True only if all adjacent words are valid.
        """
        if not adjacent_words:
            return True
        
        gaddag = self.get_game().gaddag
        for adjacent_word, _, _, _ in adjacent_words:
            # Use GADDAG's fast word check
            if not self._fast_word_check(adjacent_word, gaddag):
                return False
        
        return True

    def _legal_actions(self, player):
        if self._game_over or player != self._current_player:
            return []
            
        rack = self.racks[player]
        moves = self.get_game().move_gen.generate(self.board, rack)
        
        valid_moves = []
        
        for m in moves:
            # OPTIMIZATION: We only run strict validation if the move isn't already banned.
            # However, we don't have the ID yet. So we generate, then ID, then check ban.
            
            # Basic geometry check (fast)
            r, c, word = m['row'], m['col'], m['word']
            dr, dc = (0, 1) if m['dir'] == 'Across' else (1, 0)
            end_r = r + dr * (len(word) - 1)
            end_c = c + dc * (len(word) - 1)
            if not (0 <= r < 15 and 0 <= c < 15 and 0 <= end_r < 15 and 0 <= end_c < 15):
                continue

            valid_moves.append(m)

        if not valid_moves:
            return [450] # Pass

        # Deterministic Sort
        valid_moves.sort(key=lambda x: (-len(x['word']), x['word']))

        best_moves_by_loc = {}
        for m in valid_moves:
            r, c, d_str = m['row'], m['col'], m['dir']
            d = 0 if d_str == 'Across' else 1
            action_id = (r * 15 + c) * 2 + d
            
            if action_id not in best_moves_by_loc:
                best_moves_by_loc[action_id] = m
        
        self._current_move_map = best_moves_by_loc
        
        legal = list(best_moves_by_loc.keys())
        if len(self.bag) >= 7:
            legal.append(451) 
            
        # NEW: Filter out banned actions
        final_legal = [a for a in legal if a not in self.banned_actions]
        
        # If we banned everything, forced Pass
        if not final_legal:
            return [450]
            
        return sorted(final_legal)
    
    def legal_actions_mask(self, player=None):
        """
        Returns a list of 0s and 1s representing valid moves.
        Length must match game.num_distinct_actions() exactly (452).
        """
        if player is None:
            player = self.current_player()
        
        # Get the list of legal integer IDs (e.g. [2, 5, 450])
        legal_ids = self.legal_actions(player)
        
        # Create a mask of zeros with the correct length
        num_actions = self.get_game().num_distinct_actions() # Should be 452
        mask = [0] * num_actions
        
        # Set 1 for valid actions
        for action_id in legal_ids:
            if 0 <= action_id < num_actions:
                mask[action_id] = 1
            
        return mask

    def _apply_action(self, action_id):
        # --- EARLY TERMINATION ---
        if self.turn_count > 20 and sum(self.scores) == 0:
            self._game_over = True
            self.log_termination("Mercy rule: turn > 20 with zero total score")
            return

        if self.turn_count > 100:
            self._game_over = True
            self.log_termination("Hard turn limit")
            return

        # --- PASS ---
        if action_id == 450:
            self.log_move_attempt(450, {'action': 'PASS'}, True)
            self.consecutive_passes += 1
            if self.consecutive_passes >= 4: 
                self._game_over = True
                self.log_termination("Four consecutive passes")
            
            # Reset counters/state for NEXT player
            self.turn_count += 1
            self._current_player = 1 - self._current_player
            self._current_move_map = {}
            self.banned_actions = set() 
            return

        # --- EXCHANGE ---
        if action_id == 451:
            if len(self.bag) >= 7:
                self.log_move_attempt(451, {'action': 'EXCHANGE'}, True)
                self.bag.extend(self.racks[self._current_player])
                np.random.shuffle(self.bag)
                self.racks[self._current_player] = []
                self._refill_rack(self._current_player)
                self.consecutive_passes += 1 # Exchanges count towards pass limit
            else:
                self.log_move_attempt(451, {'action': 'EXCHANGE'}, False, "Bag < 7")
                self.consecutive_passes += 1
            
            if self.consecutive_passes >= 4:
                self._game_over = True
                
            self.turn_count += 1
            self._current_player = 1 - self._current_player
            self._current_move_map = {}
            self.banned_actions = set()
            return

        # --- PLAY WORD ---
        # Generate map if missing
        if not self._current_move_map:
             self._legal_actions(self._current_player)

        # 1. Hallucination / Banned Move Check
        if action_id not in self._current_move_map:
            self.log_move_attempt(action_id, {'action': 'INVALID_ID'}, False, "Action not in map (or banned)")
            
            # NO PENALTY. Just ban and retry.
            self.banned_actions.add(action_id)
            
            # If we fail 3 times, we burn the turn (Pass)
            if len(self.banned_actions) >= 3:
                self.log_move_attempt(450, {'action': 'FORCED_PASS'}, True)
                # Manually execute pass logic without recursion to avoid stack weirdness
                self.consecutive_passes += 1
                if self.consecutive_passes >= 4: self._game_over = True
                self.turn_count += 1
                self._current_player = 1 - self._current_player
                self._current_move_map = {}
                self.banned_actions = set()
            return

        move = self._current_move_map[action_id]
        
        # 2. Strict Validation
        is_valid, tiles_used = self._validate_move(move['row'], move['col'], move['word'], move['dir'], self.racks[self._current_player])
        
        if not is_valid:
            self.log_move_attempt(action_id, move, False, "Validation Failed")
            
            # NO PENALTY.
            self.banned_actions.add(action_id)
            
            if len(self.banned_actions) >= 3:
                self.log_move_attempt(450, {'action': 'FORCED_PASS'}, True)
                self.consecutive_passes += 1
                if self.consecutive_passes >= 4: self._game_over = True
                self.turn_count += 1
                self._current_player = 1 - self._current_player
                self._current_move_map = {}
                self.banned_actions = set()
            return

        # 3. SUCCESS
        self.log_move_attempt(action_id, move, True)
        self.consecutive_passes = 0
        self.consecutive_zero_scores = 0
        
        score, _ = self._score_move(move['row'], move['col'], move['word'], move['dir'])
        self.scores[self._current_player] += score
        
        # Place tiles
        dr, dc = (0, 1) if move['dir'] == 'Across' else (1, 0)
        curr_r, curr_c = move['row'], move['col']
        for char in move['word']:
            self.board[curr_r][curr_c] = char
            curr_r += dr
            curr_c += dc
            
        # Update Rack
        real_rack = self.racks[self._current_player]
        for char in tiles_used:
            if char in real_rack: real_rack.remove(char)
            else: real_rack.remove('?')

        self._refill_rack(self._current_player)
        
        if not self.racks[self._current_player] and not self.bag:
            self._game_over = True
            self.adjust_final_scores()

        self.turn_count += 1
        self._current_player = 1 - self._current_player
        self._current_move_map = {}
        self.banned_actions = set()
    
    def _score_move(self, row, col, word, direction):
        total_score = 0
        word_multiplier = 1
        cross_word_scores = 0
        tiles_used = [] 
        
        dr, dc = (0, 1) if direction == 'Across' else (1, 0)
        curr_r, curr_c = row, col
        
        move_score = 0
        
        for char in word:
            # SAFETY CHECK: If we go off board, stop scoring to prevent crash
            if not (0 <= curr_r < 15 and 0 <= curr_c < 15):
                break 

            # Check if tile already exists
            if self.board[curr_r][curr_c] != '.':
                move_score += TILE_VALUES[char]
            else:
                # Placed tile
                tiles_used.append(char)
                val = TILE_VALUES[char]
                
                # Only apply premium if this square hasn't been used before
                if (curr_r, curr_c) not in self.used_premiums:
                    prem = PREMIUMS.get((curr_r, curr_c))
                    if prem:
                        ptype, pmult = prem
                        if ptype == 'L': val *= pmult
                        elif ptype == 'W': word_multiplier *= pmult
                        # Mark this premium square as used
                        self.used_premiums.add((curr_r, curr_c))
                
                move_score += val
                
                # Cross-Words
                cross_score = self._calc_cross_score(curr_r, curr_c, char, direction)
                cross_word_scores += cross_score

            curr_r += dr
            curr_c += dc
            
        total_score = (move_score * word_multiplier) + cross_word_scores
        
        if len(tiles_used) == 7:
            total_score += 50
            
        return total_score, tiles_used

    def _calc_cross_score(self, row, col, char, main_direction):
        # Calculate score of any word formed perpendicular to the main move
        # Returns 0 if no cross word is formed.
        cross_dr, cross_dc = (1, 0) if main_direction == 'Across' else (0, 1)
        
        # Check if neighbors exist
        if 0 <= row - cross_dr < 15 and 0 <= col - cross_dc < 15:
             if self.board[row-cross_dr][col-cross_dc] == '.':
                 if 0 <= row + cross_dr < 15 and 0 <= col + cross_dc < 15:
                     if self.board[row+cross_dr][col+cross_dc] == '.':
                         return 0 # No neighbors
        
        # Scan Back
        start_r, start_c = row, col
        while 0 <= start_r - cross_dr < 15 and 0 <= start_c - cross_dc < 15:
            if self.board[start_r - cross_dr][start_c - cross_dc] != '.':
                start_r -= cross_dr
                start_c -= cross_dc
            else:
                break
                
        # Scan Forward
        end_r, end_c = row, col
        while 0 <= end_r + cross_dr < 15 and 0 <= end_c + cross_dc < 15:
            if self.board[end_r + cross_dr][end_c + cross_dc] != '.':
                end_r += cross_dr
                end_c += cross_dc
            else:
                break
        
        # If start == end, it's just the single tile (not a word)
        if (start_r, start_c) == (end_r, end_c):
            return 0
            
        # Calculate Score for this cross word
        score = 0
        word_mult = 1
        
        curr_r, curr_c = start_r, start_c
        while True:
            # Is this the tile we just placed?
            if (curr_r, curr_c) == (row, col):
                val = TILE_VALUES[char]
                # Apply Premium only if not already used (It applies to BOTH words!)
                if (row, col) not in self.used_premiums:
                    prem = PREMIUMS.get((row, col))
                    if prem:
                        ptype, pmult = prem
                        if ptype == 'L': val *= pmult
                        elif ptype == 'W': word_mult *= pmult
                score += val
            else:
                # Existing tile
                existing_char = self.board[curr_r][curr_c]
                score += TILE_VALUES[existing_char]
                
            if (curr_r, curr_c) == (end_r, end_c):
                break
            curr_r += cross_dr
            curr_c += cross_dc
            
        return score * word_mult

    def _action_to_string(self, player, action):
        return f"Move {action}"

    def is_terminal(self):
        return self._game_over

    def returns(self):
        # Apply end-game adjustments if game is over
        if self._game_over:
            # EARLY TERMINATION PENALTY: Apply BEFORE final score adjustments
            # If more than half the tiles remain in the bag, both players lose points
            # This discourages exchange-heavy strategies that lead to stalemate
            if len(self.bag) > 50:
                self.scores[0] -= 20.0
                self.scores[1] -= 20.0
                self.scores[0] = max(0.0, self.scores[0])
                self.scores[1] = max(0.0, self.scores[1])
            
            # Then apply standard end-game tile adjustments
            self.adjust_final_scores()
        
        # Return actual scores
        return list(self.scores)

    def information_state_tensor(self, player):
        planes = np.zeros((35, 15, 15), dtype=np.float32)
        
        # 0-25: Board Letters
        for r in range(15):
            for c in range(15):
                char = self.board[r][c]
                if 'A' <= char <= 'Z':
                    planes[ord(char) - ord('A')][r][c] = 1.0

        # 26: Blanks (Simplified: ignored for now, assuming all uppercase)
        
        # 27-30: Bonuses
        for r in range(15):
            for c in range(15):
                prem = PREMIUMS.get((r, c))
                if prem:
                    t, v = prem
                    if t=='L' and v==2: planes[27][r][c] = 1.0
                    if t=='L' and v==3: planes[28][r][c] = 1.0
                    if t=='W' and v==2: planes[29][r][c] = 1.0
                    if t=='W' and v==3: planes[30][r][c] = 1.0

        # 31: Anchors
        # (Re-calculate anchors quickly)
        for r in range(15):
            for c in range(15):
                if self.board[r][c] == '.':
                    if (r>0 and self.board[r-1][c]!='.') or (r<14 and self.board[r+1][c]!='.') or \
                       (c>0 and self.board[r][c-1]!='.') or (c<14 and self.board[r][c+1]!='.'):
                        planes[31][r][c] = 1.0
        if self.board[7][7] == '.': planes[31][7][7] = 1.0

        # 32: Bag Percentage (Constant Plane)
        bag_val = len(self.bag) / 100.0
        planes[32].fill(bag_val)

        # 33: Score Ratio (Me / (Me+Opponent))
        s1, s2 = self.scores[player], self.scores[1-player]
        total = s1 + s2 + 1e-5
        planes[33].fill(s1 / total)

        # 34: My Rack (Projected onto diagonal? No, standard practice is a constant plane per letter)
        # This is tricky for variable racks. Let's just use channel 34 as "Rack Density" for now
        # to prevent shape errors, or leave empty.
        # Ideally, we add 26 more channels for the rack, but let's stick to 35 total for memory.
        
        return planes.flatten()
    
    def observation_tensor(self, player=None):
        """
        Required by AlphaZero. 
        Maps the specific player's view (Information State) to the observation.
        """
        # If player is not specified, default to the current player
        if player is None:
            player = self.current_player()
            
        return self.information_state_tensor(player)
    
    def __str__(self):
        # Create a comprehensive ASCII representation
        lines = []
        lines.append("=" * 70)
        lines.append(f"SCRABBLE GAME STATE - Turn {self.turn_count}")
        lines.append("=" * 70)
        
        # Current player and game status
        if self._game_over:
            lines.append(f"Status: GAME OVER")
            if self.termination_reason:
                lines.append(f"Reason: {self.termination_reason}")
        else:
            lines.append(f"Status: IN PROGRESS - Player {self._current_player}'s turn")
        
        lines.append("")
        
        # Scores
        lines.append(f"Scores: P0={self.scores[0]:.1f}  P1={self.scores[1]:.1f}")
        
        # Game state counters
        lines.append(f"Consecutive Passes: {self.consecutive_passes}")
        lines.append(f"Consecutive Zero Scores: {self.consecutive_zero_scores}")
        lines.append(f"Banned Actions: {len(self.banned_actions)}")
        
        lines.append("")
        
        # Bag and racks
        lines.append(f"Bag: {len(self.bag)} tiles remaining")
        lines.append(f"P0 Rack ({len(self.racks[0])} tiles): {' '.join(self.racks[0]) if self.racks[0] else 'empty'}")
        lines.append(f"P1 Rack ({len(self.racks[1])} tiles): {' '.join(self.racks[1]) if self.racks[1] else 'empty'}")
        
        lines.append("")
        lines.append("Board:")
        
        # Board with column headers
        lines.append("   " + " ".join([chr(ord('A') + i) for i in range(15)]))
        for r in range(15):
            row_str = f"{r:2} "
            for c in range(15):
                row_str += self.board[r][c] + " "
            lines.append(row_str)
        
        # Add move log summary if available
        if self.move_log:
            lines.append("")
            lines.append(self.get_move_log_summary())
        
        lines.append("=" * 70)
        return "\n".join(lines)

# Register the game
pyspiel.register_game(_GAME_TYPE, ScrabbleGame)

if __name__ == "__main__":
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    print("Board initialized.")
    print("Legal actions:", state.legal_actions())
    # Try applying action 2 (First real move)
    state.apply_action(2)
    print("Move played.")
    print(state.board)