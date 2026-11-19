"""
Alphable V4 Move Representation.

Supports Scrabble moves (placements, exchanges, passes) across:
- MAGPIE UCGI format (e.g., '8H TRAIN ST 24 35.20')
- Woogles platform API format
- Compact Game Position (CGP) format
- Alphable V3 legacy format for 1:1 parity verification
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple


@dataclass(frozen=True)
class Move:
    """
    Immutable Scrabble move representation.
    """
    row: Optional[int] = None           # 0-indexed (0..14), None for pass/exchange
    col: Optional[int] = None           # 0-indexed (0..14), None for pass/exchange
    direction: Optional[str] = None     # 'Across' (horizontal) or 'Down' (vertical)
    word: str = ""                      # Word played or tiles exchanged or 'pass'
    tiles_placed: str = ""              # Only tiles placed from rack (lowercase for blank)
    score: int = 0                      # Move score in points
    leave: str = ""                     # Rack leave after the move
    equity: float = 0.0                 # Static or search equity
    is_pass: bool = False
    is_exchange: bool = False

    @property
    def is_placement(self) -> bool:
        return not self.is_pass and not self.is_exchange

    @property
    def coord_str(self) -> str:
        """
        Returns standard Scrabble coordinate notation:
        Across: '8H' (row 8, col H)
        Down: 'H8' (col H, row 8)
        Pass: 'PASS'
        Exchange: 'EXCH'
        """
        if self.is_pass:
            return "PASS"
        if self.is_exchange:
            return "EXCH"
        if self.row is None or self.col is None:
            return ""
        row_str = str(self.row + 1)
        col_char = chr(ord('A') + self.col)
        if self.direction == "Across":
            return f"{row_str}{col_char}"
        else:
            return f"{col_char}{row_str}"

    def to_woogles_coord(self) -> str:
        """Returns standard Scrabble/Woogles coordinate notation (e.g. '8H' or 'H8')."""
        return self.coord_str

    @property
    def tiles_used(self) -> str:
        """Returns tiles placed from rack. If tiles_placed is empty, falls back to word."""
        return self.tiles_placed if self.tiles_placed else self.word

    def get_tiles_played(self, rack_len: int = 7) -> int:
        """
        Returns the number of tiles played from the rack.
        Accounts for:
        1. Pass: 0 tiles
        2. Exchange: number of exchanged tiles
        3. Placement with explicit tiles_placed: len(tiles_placed)
        4. Placement with leave: max(1, rack_len - len(leave))
        5. Placement fallback: min(rack_len, len(word))
        """
        if self.is_pass:
            return 0
        if self.is_exchange:
            return len(self.word)
        if self.tiles_placed:
            return len(self.tiles_placed)
        if self.leave is not None and len(self.leave) > 0:
            return max(1, rack_len - len(self.leave))
        return min(rack_len, len(self.word)) if self.word else 0

    def to_cgp_action(self) -> str:
        """Formats the move as an action string for CGP/MAGPIE."""
        if self.is_pass:
            return "pass"
        if self.is_exchange:
            return f"ex {self.word}"
        return f"{self.coord_str} {self.word}"

    def to_woogles(self) -> Dict[str, Any]:
        """Formats move for Woogles game protocol."""
        if self.is_pass:
            return {"action": "pass"}
        if self.is_exchange:
            return {"action": "exchange", "letters": self.word}
        return {
            "action": "play",
            "row": self.row,
            "col": self.col,
            "dir": self.direction,
            "word": self.word,
            "score": self.score,
        }

    @classmethod
    def make_pass(cls, score: int = 0, leave: str = "", equity: float = 0.0) -> Move:
        return cls(is_pass=True, score=score, leave=leave, equity=equity, word="pass")

    @classmethod
    def make_exchange(cls, tiles: str, score: int = 0, leave: str = "", equity: float = 0.0) -> Move:
        return cls(is_exchange=True, word=tiles.upper(), score=score, leave=leave, equity=equity)

    create_pass = make_pass
    create_exchange = make_exchange

    @classmethod
    def parse_coordinate(cls, coord: str) -> Tuple[int, int, str]:
        """
        Parses Scrabble coordinate like '8H' (Across) or 'H8' (Down).
        Returns (row, col, direction). Both 0-indexed (0..14).
        Enforces standard Scrabble coordinate bounds: row 1..15, col A..O.
        Raises ValueError if coordinate is invalid or out of bounds.
        """
        coord = coord.strip().upper()
        if not coord:
            raise ValueError("Empty coordinate string")

        if coord[0].isdigit():
            # Across: e.g. 8H or 15A
            match = re.match(r"^(\d+)([A-O])$", coord)
            if not match:
                raise ValueError(f"Invalid across coordinate: {coord}")
            row_num = int(match.group(1))
            if not (1 <= row_num <= 15):
                raise ValueError(f"Row number out of bounds (1-15): {row_num} in coordinate '{coord}'")
            row = row_num - 1
            col = ord(match.group(2)) - ord('A')
            return row, col, "Across"
        else:
            # Down: e.g. H8 or A15
            match = re.match(r"^([A-O])(\d+)$", coord)
            if not match:
                raise ValueError(f"Invalid down coordinate: {coord}")
            row_num = int(match.group(2))
            if not (1 <= row_num <= 15):
                raise ValueError(f"Row number out of bounds (1-15): {row_num} in coordinate '{coord}'")
            col = ord(match.group(1)) - ord('A')
            row = row_num - 1
            return row, col, "Down"

    @classmethod
    def from_ucgi_line(cls, line: str, tiles_placed: str = "") -> Optional[Move]:
        """
        Parses a single line of MAGPIE machine-readable / UCGI move output.
        Handles:
          "1:   8D QUARTZY    126 126.00"   (Bingo, empty leave)
          "8:   8D QUARTZ  Y  68  67.55"    (With leave 'Y')
          "10:  8D QUART   YZ 48  56.95"   (With leave 'YZ')
          "1:   pass AEINRST 0 -10.00"
          "2:   (exch AEI) BCD 0 -4.50"
        """
        clean = line.strip()
        if not clean or clean.startswith("Showing") or clean.startswith("Move") or clean.startswith("---"):
            return None

        # Strip index prefix if present, e.g. "1: "
        if ":" in clean:
            prefix, remainder = clean.split(":", 1)
            if prefix.strip().isdigit():
                clean = remainder.strip()

        parts = clean.split()
        if not parts:
            return None

        # Pass move: pass [leave] score equity
        if parts[0].lower() in ("pass", "(pass)"):
            leave = parts[1] if len(parts) > 3 else ""
            score = int(parts[-2]) if len(parts) >= 2 and parts[-2].lstrip("-").isdigit() else 0
            equity = float(parts[-1]) if len(parts) >= 2 else 0.0
            return cls.make_pass(score=score, leave=leave, equity=equity)

        # Exchange move: (exch TILES) [leave] score equity
        if parts[0].lower().startswith("(exch") or parts[0].lower() == "exch":
            tiles = ""
            leave = ""
            score = 0
            equity = 0.0
            if len(parts) >= 2:
                tiles = parts[1].rstrip(")") if not parts[0].endswith(")") else parts[0].lstrip("(").replace("exch", "").strip()
            if len(parts) >= 4:
                try:
                    score = int(parts[-2])
                    equity = float(parts[-1])
                    if len(parts) >= 5:
                        leave = parts[2]
                except ValueError:
                    pass
            return cls.make_exchange(tiles=tiles, score=score, leave=leave, equity=equity)

        # Placement move
        # Format: COORD WORD [LEAVE] SCORE EQUITY
        if len(parts) >= 4:
            coord = parts[0]
            try:
                row, col, direction = cls.parse_coordinate(coord)
            except ValueError:
                return None

            word = parts[1].replace("(", "").replace(")", "")

            try:
                equity = float(parts[-1])
                score = int(parts[-2])
            except ValueError:
                return None

            # Leave is optional in middle
            leave = parts[2] if len(parts) >= 5 else ""

            return cls(
                row=row,
                col=col,
                direction=direction,
                word=word,
                tiles_placed=tiles_placed,
                score=score,
                leave=leave,
                equity=equity,
            )

        return None
