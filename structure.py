import collections
import copy

# The GADDAG Delimiter
BREAK = '>'

class Gaddag:
    def __init__(self):
        self.root = {}
    
    def add_word(self, word):
        # Gordon's Algorithm: Create paths for every possible anchor point in the word
        # "CARE" -> C>ARE, A>RE + C, R>E + CA, E> + CAR
        for i in range(1, len(word) + 1):
            prefix = word[:i]
            suffix = word[i:]
            # The path starts with the LAST letter of the prefix, reversed
            # Then the BREAK, then the suffix
            path = prefix[::-1] + BREAK + suffix
            current = self.root
            for char in path:
                if char not in current:
                    current[char] = {}
                current = current[char]
            current['$'] = True # Terminal marker

    @staticmethod
    def load(filepath):
        g = Gaddag()
        print(f"Loading dictionary from {filepath}...")
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    word = line.strip().upper()
                    # Basic cleaning for NWL files that might have definitions
                    word = word.split(' ')[0] 
                    if len(word) > 1 and word.isalpha():
                        g.add_word(word)
        except FileNotFoundError:
            print(f"ERROR: Could not find dictionary file at {filepath}")
            raise
        print("Dictionary loaded.")
        return g

class MoveGenerator:
    def __init__(self, gaddag):
        self.gaddag = gaddag
        self.moves = [] 
        self.cross_checks = {} 

    def generate(self, board, rack_list):
        """
        Main entry point.
        board: 15x15 list of lists (or numpy array) where empty is '.'
        rack_list: list of chars, e.g. ['A', 'B', 'C', '?', ' ']
        """
        self.moves = []
        # Convert list rack to Counter for easy manipulation
        rack = collections.Counter(rack_list)
        if ' ' in rack: # Handle empty space representation if passed
            rack['.'] += rack[' ']
            del rack[' ']

        # 1. Generate ACROSS moves
        self._compute_cross_checks(board)
        self._find_moves(board, rack, direction='Across')
        
        # 2. Generate DOWN moves
        # Transpose board: board[row][col] -> board_T[col][row]
        board_T = [list(x) for x in zip(*board)]
        self._compute_cross_checks(board_T)
        
        start_idx = len(self.moves)
        self._find_moves(board_T, rack, direction='Down')
        
        # Fix coordinates for Down moves
        for i in range(start_idx, len(self.moves)):
            m = self.moves[i]
            # Swap row/col back to original space
            m['row'], m['col'] = m['col'], m['row']

        return self.moves

    def _compute_cross_checks(self, board):
        self.cross_checks = {}
        rows = 15
        cols = 15
        
        for r in range(rows):
            for c in range(cols):
                if board[r][c] != '.':
                    continue 
                
                # Check neighbors above and below
                if (r > 0 and board[r-1][c] != '.') or (r < 14 and board[r+1][c] != '.'):
                    valid_chars = set()
                    
                    # Scan Up
                    up_part = ""
                    curr = r - 1
                    while curr >= 0 and board[curr][c] != '.':
                        up_part = board[curr][c] + up_part
                        curr -= 1
                    
                    # Scan Down
                    down_part = ""
                    curr = r + 1
                    while curr < 15 and board[curr][c] != '.':
                        down_part += board[curr][c]
                        curr += 1
                    
                    # Try all candidates A-Z
                    for char_code in range(ord('A'), ord('Z')+1):
                        char = chr(char_code)
                        candidate = up_part + char + down_part
                        # Check if valid word (using GADDAG lookup for speed)
                        # We reverse it to check existence in GADDAG root logic
                        if self._fast_word_check(candidate):
                             valid_chars.add(char)
                    
                    self.cross_checks[(r,c)] = valid_chars

    def _fast_word_check(self, word):
        # To check if "CAT" is a word, check if "T>AC" exists in GADDAG 
        # (Reverse(Prefix) + BREAK + Suffix)
        # For a full word check, the prefix is the whole word.
        path = word[::-1] + BREAK
        curr = self.gaddag.root
        for char in path:
            if char not in curr:
                return False
            curr = curr[char]
        return '$' in curr

    def _find_moves(self, board, rack, direction):
        anchors = self._find_anchors(board)
        for r, c in anchors:
            self._gen_row_moves(board, r, c, rack, self.gaddag.root)

    def _find_anchors(self, board):
        anchors = []
        has_tile = False
        for r in range(15):
            for c in range(15):
                if board[r][c] != '.':
                    has_tile = True
                    continue
                if (r>0 and board[r-1][c]!='.') or (r<14 and board[r+1][c]!='.') or \
                   (c>0 and board[r][c-1]!='.') or (c<14 and board[r][c+1]!='.'):
                    anchors.append((r,c))
        if not has_tile:
            return [(7,7)] 
        return anchors

    def _gen_row_moves(self, board, row, col, rack, node):
        self._go_left(board, row, col, rack, node, anchor_col=col, word_part="")

    def _go_left(self, board, row, col, rack, node, anchor_col, word_part):
        # 1. Switch to Right?
        if '>' in node:
            prefix = word_part[::-1]
            self._go_right(board, row, anchor_col + 1, rack, node['>'], prefix)

        # 2. Continue Left
        if col >= 0:
            char_on_board = board[row][col]
            candidates = set()
            
            if char_on_board != '.':
                candidates.add(char_on_board)
            else:
                for tile in rack:
                    if rack[tile] > 0:
                        if tile == '?':
                            candidates.update("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                        else:
                            candidates.add(tile)
                
                if (row, col) in self.cross_checks:
                    candidates &= self.cross_checks[(row, col)]

            for char in candidates:
                if char in node:
                    new_rack = rack.copy()
                    if char_on_board == '.':
                        if rack.get(char, 0) > 0:
                            new_rack[char] -= 1
                        else:
                            new_rack['?'] -= 1
                    
                    self._go_left(board, row, col - 1, new_rack, node[char], anchor_col, 
                                  word_part + char)

    def _go_right(self, board, row, col, rack, node, current_word):
        # 1. Valid Word?
        if '$' in node:
             if col > 14 or board[row][col] == '.':
                 start_col = col - len(current_word)
                 self.moves.append({
                     'row': row, 
                     'col': start_col, 
                     'dir': 'Across',
                     'word': current_word
                 })

        # 2. Continue Right
        if col <= 14:
            char_on_board = board[row][col]
            candidates = set()
            if char_on_board != '.':
                candidates.add(char_on_board)
            else:
                for tile in rack:
                    if rack[tile] > 0:
                        if tile == '?':
                            candidates.update("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                        else:
                            candidates.add(tile)
                
                if (row, col) in self.cross_checks:
                    candidates &= self.cross_checks[(row, col)]

            for char in candidates:
                if char in node:
                    new_rack = rack.copy()
                    if char_on_board == '.':
                        if rack.get(char, 0) > 0:
                            new_rack[char] -= 1
                        else:
                            new_rack['?'] -= 1
                    
                    self._go_right(board, row, col + 1, new_rack, node[char], 
                                   current_word + char)