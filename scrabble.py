import pyspiel
import numpy as np
from structure import Gaddag, MoveGenerator

# Game Configuration
_NUM_PLAYERS = 2
_BOARD_SIZE = 15
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
      super().__init__(_GAME_TYPE, params if params else {})
      # Load once. In a real app, use a singleton to avoid reloading per game.
      self.gaddag = Gaddag.load("NWL2023.txt") 
      self.move_gen = MoveGenerator(self.gaddag)

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
        
        # Initialize Bag
        self.bag = []
        for letter, count in BAG_DISTRIBUTION:
            self.bag.extend([letter] * count)
        np.random.shuffle(self.bag) # Shuffle immediately
        
        # Draw initial racks (7 tiles each)
        self.racks = [[], []]
        self._refill_rack(0)
        self._refill_rack(1)

    def _refill_rack(self, player_idx):
        needed = 7 - len(self.racks[player_idx])
        if needed > 0 and self.bag:
            draw = [self.bag.pop() for _ in range(min(needed, len(self.bag)))]
            self.racks[player_idx].extend(draw)

    def current_player(self):
        return self._current_player

    def _legal_actions(self, player):
        if self._game_over or player != self._current_player:
            return []
        
        # 1. Get moves from GADDAG
        # Note: self.board must be a 15x15 array of chars. 
        # If initialized as zeros in __init__, convert to '.' chars first.
        rack = self.racks[player]
        moves = self.move_gen.generate(self.board, rack)
        
        if not moves:
            # If no moves, Pass is the only option (Action ID 0)
            # You might want to reserve ID 0 for PASS and 1 for EXCHANGE
            return [0] 

        # 2. Store mapping
        # OpenSpiel needs integers. We just return indices.
        # Ideally, we should hash these moves to a global action space (Section 3.2 of report)
        # But for this stage, a dynamic mapping per state is acceptable.
        self._current_move_map = moves
        
        # Shift indices by 2 to leave room for PASS (0) and EXCHANGE (1)
        return [i + 2 for i in range(len(moves))]

    def _apply_action(self, action_id):
        # Action 0: PASS
        if action_id == 0:
            self.consecutive_passes += 1
            if self.consecutive_passes >= 6:
                self._game_over = True
            self._current_player = 1 - self._current_player
            return

        # Action 1: EXCHANGE (Simplified: Swap all tiles)
        if action_id == 1:
            self.consecutive_passes = 0
            if len(self.bag) >= 7:
                self.bag.extend(self.racks[self._current_player])
                np.random.shuffle(self.bag)
                self.racks[self._current_player] = []
                self._refill_rack(self._current_player)
                self._current_player = 1 - self._current_player
            return

        # Action 2+: PLAY WORD
        self.consecutive_passes = 0
        # Retrieve move from the map generated in _legal_actions
        # NOTE: This assumes _legal_actions was called right before. 
        # In pure OpenSpiel, we might need to regenerate if map is empty.
        if not self._current_move_map:
             self._legal_actions(self._current_player)

        move_index = action_id - 2
        move = self._current_move_map[move_index]
        
        row, col = move['row'], move['col']
        word = move['word']
        direction = move['dir'] # 'Across' or 'Down'
        
        # 1. Calculate Score & Determine Tiles Used
        score, tiles_used = self._score_move(row, col, word, direction)
        self.scores[self._current_player] += score
        
        # 2. Place Tiles on Board
        dr, dc = (0, 1) if direction == 'Across' else (1, 0)
        curr_r, curr_c = row, col
        for char in word:
            self.board[curr_r][curr_c] = char
            curr_r += dr
            curr_c += dc
            
        # 3. Remove used tiles from Rack
        # Note: We must handle blanks '?' correctly.
        # If word has 'A' but rack has '?', we remove '?'.
        player_rack = self.racks[self._current_player]
        for char in tiles_used:
            if char in player_rack:
                player_rack.remove(char)
            elif '?' in player_rack:
                player_rack.remove('?')
            else:
                raise ValueError(f"Cannot play {word} with rack {player_rack}")

        # 4. Refill Rack & Switch
        self._refill_rack(self._current_player)
        
        # Check Endgame (Empty rack and empty bag)
        if not self.racks[self._current_player] and not self.bag:
            self._game_over = True
            # TODO: Add bonus (2x opponent's remaining tiles) to score
            
        self._current_player = 1 - self._current_player

    def _score_move(self, row, col, word, direction):
        total_score = 0
        word_multiplier = 1
        cross_word_scores = 0
        tiles_used = [] # List of chars actually placed from rack
        
        dr, dc = (0, 1) if direction == 'Across' else (1, 0)
        curr_r, curr_c = row, col
        
        move_score = 0
        
        for char in word:
            # Check if tile already exists
            if self.board[curr_r][curr_c] != '.':
                # Existing tile: just add its face value, no premium bonuses
                move_score += TILE_VALUES[char]
            else:
                # Placed tile: Apply premiums
                tiles_used.append(char)
                val = TILE_VALUES[char]
                
                # Check for Premium Squares
                prem = PREMIUMS.get((curr_r, curr_c))
                if prem:
                    ptype, pmult = prem
                    if ptype == 'L': # Double/Triple Letter
                        val *= pmult
                    elif ptype == 'W': # Double/Triple Word
                        word_multiplier *= pmult
                
                move_score += val
                
                # Check Cross-Words (words formed perpendicular to placement)
                # This is complex. We need to check neighbors. 
                # For brevity: We will assume valid cross-words were checked by GADDAG.
                # We just need to sum them.
                # A cross word exists if neighbors exist perpendicular to dir.
                cross_score = self._calc_cross_score(curr_r, curr_c, char, direction)
                cross_word_scores += cross_score

            curr_r += dr
            curr_c += dc
            
        total_score = (move_score * word_multiplier) + cross_word_scores
        
        # BINGO BONUS (50 pts for using all 7 tiles)
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
                # Apply Premium (It applies to BOTH words!)
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
        
        # TODO: Logic to place tiles on self.board
        print(f"Playing {word} at {row},{col} {direction}")

    def _action_to_string(self, player, action):
        return f"Move {action}"

    def is_terminal(self):
        return self._game_over

    def returns(self):
        # Return scores [player_1_score, player_2_score]
        return [0.0, 0.0]

    def information_state_tensor(self, player):
        # TODO: Implement the 15x15x32 tensor
        return np.zeros((32, 15, 15), dtype=np.float32).flatten()

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