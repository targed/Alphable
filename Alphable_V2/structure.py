import collections
import copy

# The GADDAG Delimiter
BREAK = '>'


class Gaddag:
    def __init__(self):
        self.root = {}

    def add_word(self, word):
        for i in range(1, len(word) + 1):
            prefix = word[:i]
            suffix = word[i:]
            path = prefix[::-1] + BREAK + suffix
            current = self.root
            for char in path:
                if char not in current:
                    current[char] = {}
                current = current[char]
            current['$'] = True

    @staticmethod
    def load(filepath):
        g = Gaddag()
        print(f"Loading dictionary from {filepath}...")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # NWL/CSW files are formatted as: WORD definition...
                    # We only need the leading headword token.
                    word = line.split(None, 1)[0].upper().lstrip('\ufeff')
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
        # Stateless: No self.moves here

    def generate(self, board, rack_list):
        # Local storage for this generation run
        moves = []
        cross_checks = {}

        rack = collections.Counter(rack_list)
        if ' ' in rack:
            rack['.'] += rack[' ']
            del rack[' ']

        # 1. Generate ACROSS
        self._compute_cross_checks(board, cross_checks)
        self._find_moves(board, rack, 'Across', moves, cross_checks)

        # 2. Generate DOWN
        board_T = [list(x) for x in zip(*board)]
        cross_checks_T = {}
        self._compute_cross_checks(board_T, cross_checks_T)

        start_idx = len(moves)
        self._find_moves(board_T, rack, 'Down', moves, cross_checks_T)

        # Fix coordinates for Down moves
        for i in range(start_idx, len(moves)):
            m = moves[i]
            m['row'], m['col'] = m['col'], m['row']
            m['dir'] = 'Down'  # Fix direction label

        # Remove duplicates (some moves can be generated via multiple GADDAG paths)
        seen = set()
        unique_moves = []
        for m in moves:
            sig = (m['row'], m['col'], m['dir'], m['word'])
            if sig not in seen:
                seen.add(sig)
                unique_moves.append(m)

        return unique_moves

    def _compute_cross_checks(self, board, cross_checks):
        rows = 15
        cols = 15
        for r in range(rows):
            for c in range(cols):
                if board[r][c] != '.':
                    continue

                if (r > 0 and board[r - 1][c] != '.') or (r < 14 and board[r + 1][c] != '.'):
                    valid_chars = set()
                    up_part = ""
                    curr = r - 1
                    while curr >= 0 and board[curr][c] != '.':
                        up_part = board[curr][c] + up_part
                        curr -= 1

                    down_part = ""
                    curr = r + 1
                    while curr < 15 and board[curr][c] != '.':
                        down_part += board[curr][c]
                        curr += 1

                    for char_code in range(ord('A'), ord('Z') + 1):
                        char = chr(char_code)
                        candidate = up_part + char + down_part
                        if self._fast_word_check(candidate):
                            valid_chars.add(char)

                    cross_checks[(r, c)] = valid_chars

    def _fast_word_check(self, word):
        path = word[::-1] + BREAK
        curr = self.gaddag.root
        for char in path:
            if char not in curr:
                return False
            curr = curr[char]
        return '$' in curr

    def _find_moves(self, board, rack, direction, moves, cross_checks):
        anchors = self._find_anchors(board)
        for r, c in anchors:
            self._gen_row_moves(board, r, c, rack,
                                self.gaddag.root, moves, cross_checks)

    def _find_anchors(self, board):
        anchors = []
        has_tile = False
        for r in range(15):
            for c in range(15):
                if board[r][c] != '.':
                    has_tile = True
                    continue
                # Adjacent to existing tile (for overlapping/extending words)
                if (r > 0 and board[r - 1][c] != '.') or (r < 14 and board[r + 1][c] != '.') or \
                   (c > 0 and board[r][c - 1] != '.') or (c < 14 and board[r][c + 1] != '.'):
                    anchors.append((r, c))

        if not has_tile:
            return [(7, 7)]
        return anchors

    def _gen_row_moves(self, board, row, col, rack, node, moves, cross_checks):
        self._go_left(board, row, col, rack, node,
                      col, "", moves, cross_checks)

    def _go_left(self, board, row, col, rack, node, anchor_col, word_part, moves, cross_checks):
        if '>' in node:
            prefix = word_part[::-1]
            self._go_right(board, row, anchor_col + 1, rack,
                           node['>'], prefix, moves, cross_checks)

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

                if (row, col) in cross_checks:
                    candidates &= cross_checks[(row, col)]

            # Sort candidates to ensure deterministic recursion order
            for char in sorted(candidates):
                if char in node:
                    new_rack = rack.copy()
                    if char_on_board == '.':
                        if rack.get(char, 0) > 0:
                            new_rack[char] -= 1
                        else:
                            new_rack['?'] -= 1

                    self._go_left(
                        board,
                        row,
                        col - 1,
                        new_rack,
                        node[char],
                        anchor_col,
                        word_part + char,
                        moves,
                        cross_checks,
                    )

    def _go_right(self, board, row, col, rack, node, current_word, moves, cross_checks):
        if '$' in node:
            if col > 14 or board[row][col] == '.':
                start_col = col - len(current_word)

                # If there is a tile immediately to the left, this word illegally merges with it.
                if start_col > 0 and board[row][start_col - 1] != '.':
                    pass
                else:
                    moves.append(
                        {
                            'row': row,
                            'col': start_col,
                            'dir': 'Across',
                            'word': current_word,
                        }
                    )

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

                if (row, col) in cross_checks:
                    candidates &= cross_checks[(row, col)]

            for char in sorted(candidates):
                if char in node:
                    new_rack = rack.copy()
                    if char_on_board == '.':
                        if rack.get(char, 0) > 0:
                            new_rack[char] -= 1
                        else:
                            new_rack['?'] -= 1

                    self._go_right(
                        board,
                        row,
                        col + 1,
                        new_rack,
                        node[char],
                        current_word + char,
                        moves,
                        cross_checks,
                    )
