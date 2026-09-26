"""
Empirical Rack Leave Valuation and Synergy Modeling for Alphable.

Based on tournament Scrabble empirical equity tables (Lipkin-Smith / Super-Leaves).
Evaluates the expected future scoring equity of tiles remaining in hand after a move,
accounting for high-value synergy tiles (?, S), bingo stems (TISANE, RETINA), duplicate penalties,
and vowel/consonant balance.
"""

from typing import List, Union, Dict, Set, Tuple

# Single tile equity values (baseline points added to expected equity)
BASE_TILE_EQUITY: Dict[str, float] = {
    "?": 26.5,   # Blank is the highest equity tile in Scrabble (+25 to +30 pts)
    "S": 8.2,    # Pluralizer and hook master (+8 to +10 pts)
    "Z": 2.5,    # High point tile that plays easily on DL/TL
    "X": 2.5,    # Plays easily on 2-letter words (AX, EX, OX, XI, XU)
    "R": 1.8,    # Premium bingo tile
    "E": 1.6,    # Core high-probability vowel
    "T": 1.6,    # Excellent bingo consonant
    "N": 1.4,    # High-flexibility connector (-ING, -TION)
    "H": 1.2,
    "D": 1.0,
    "A": 0.8,
    "C": 0.8,
    "L": 0.6,
    "M": 0.5,
    "P": 0.5,
    "I": 0.4,
    "O": -1.5,
    "G": -1.2,
    "B": -1.5,
    "K": -1.5,
    "F": -1.8,
    "Y": -1.5,
    "J": -2.5,
    "W": -3.5,
    "U": -4.0,
    "V": -5.5,   # Hard to dump, few 2-letter words
    "Q": -7.5,   # Massive liability without U
}

# Standard Scrabble tile face values (for unplayed tile deductions in endgame)
TILE_POINTS: Dict[str, int] = {
    "A": 1, "B": 3, "C": 3, "D": 2, "E": 1, "F": 4, "G": 2, "H": 4,
    "I": 1, "J": 8, "K": 5, "L": 1, "M": 3, "N": 1, "O": 1, "P": 3,
    "Q": 10, "R": 1, "S": 1, "T": 1, "U": 1, "V": 4, "W": 4, "X": 8,
    "Y": 4, "Z": 10, "?": 0,
}

# Duplicate penalties for redundant tiles
DUPLICATE_PENALTIES: Dict[str, float] = {
    "S": -6.2,   # Holding second S has severe diminishing returns (marginal value +2.0 vs +8.2)
    "I": -4.0,
    "U": -4.5,
    "O": -3.0,
    "A": -2.5,
    "E": -1.5,
    "V": -7.0,
    "W": -5.5,
    "B": -4.0,
    "F": -4.0,
    "G": -3.5,
    "D": -2.5,
    "L": -2.0,
    "M": -2.5,
    "P": -2.5,
    "T": -2.0,
    "R": -1.8,
    "N": -1.5,
}

VOWELS = set("AEIOU")

# Synergy bonuses for classic 2-tile bingo stems and tactical compounds
STEM_SYNERGIES: Dict[str, float] = {
    "?S": 5.0,
    "QU": 6.5,   # Neutralizes Q penalty
    "ES": 2.0,
    "ST": 1.8,
    "ER": 1.5,
    "IN": 1.5,
    "RS": 1.5,
    "ED": 1.5,
}

# Synergy bonuses for classic 3-tile and multi-tile bingo stems
MULTI_STEM_SYNERGIES: Dict[str, float] = {
    "RETIN": 4.5,
    "TISAN": 4.5,
    "STARE": 4.5,
    "SATIN": 4.5,
    "EST": 2.5,
    "ERS": 2.5,
    "RET": 2.5,
    "SAT": 2.5,
    "INE": 2.2,
    "TIN": 2.0,
    "ARE": 2.0,
    "ATE": 2.0,
    "ION": 2.0,
}

# Ordered stems by length (5 first, then 3, then 2) for non-overlapping evaluation
STEM_HIERARCHY: List[Tuple[str, float]] = [
    # 5-letter classic bingo stems
    ("RETIN", 4.5),
    ("TISAN", 4.5),
    ("STARE", 4.5),
    ("SATIN", 4.5),
    # 3-letter high-synergy stems
    ("EST", 2.5),
    ("ERS", 2.5),
    ("RET", 2.5),
    ("SAT", 2.5),
    ("INE", 2.2),
    ("TIN", 2.0),
    ("ARE", 2.0),
    ("ATE", 2.0),
    ("ION", 2.0),
    # 2-letter connectors (applied only if tiles not already covered by a 3+ stem)
    ("ES", 2.0),
    ("ST", 1.8),
    ("ER", 1.5),
    ("IN", 1.5),
    ("RS", 1.5),
    ("ED", 1.5),
]


def compute_leave_equity(rack: Union[List[str], str], bag_remaining: int = 100) -> float:
    """
    Computes the strategic expected equity (in Scrabble points) of a rack leave.

    Args:
        rack: List or string of tiles remaining in rack (e.g. ['A', 'E', 'R', 'T'] or "AERT").
        bag_remaining: Number of tiles left in the bag. When 0, leave equity equals the
                       negative face value of the tiles (pure endgame deduction).

    Returns:
        float: Expected leave equity in points (can be positive or negative).
    """
    if not rack:
        return 0.0

    # In Scrabble endgame (bag == 0), rack leave represents dead tiles that will be deducted
    # from the player at the end of the game (or awarded to the opponent if they go out).
    if bag_remaining == 0:
        total_unplayed_deduction = sum(TILE_POINTS.get(char.upper(), 0) for char in rack)
        return -float(total_unplayed_deduction)

    equity = 0.0
    vowel_count = 0
    consonant_count = 0
    blank_count = 0
    tile_counts: Dict[str, int] = {}

    for char in rack:
        upper = char.upper()
        if upper == "?":
            blank_count += 1
            equity += BASE_TILE_EQUITY.get("?", 26.5)
        else:
            tile_counts[upper] = tile_counts.get(upper, 0) + 1
            equity += BASE_TILE_EQUITY.get(upper, -1.0)
            if upper in VOWELS:
                vowel_count += 1
            else:
                consonant_count += 1

    # 1. Duplicate tile penalties (e.g. holding II, UUU, VV, ??)
    if blank_count > 1:
        # A single blank is worth +26.5; a second blank adds only +6.0 (total ~32.5)
        # to prevent equity hoarding and passing up real bingos.
        equity -= 20.5 * (blank_count - 1)

    for tile, count in tile_counts.items():
        if count > 1:
            pen = DUPLICATE_PENALTIES.get(tile, -2.5)
            # Escalating penalty for 3+ of same tile
            excess = count - 1
            equity += pen * excess * (1.2 ** (excess - 1))

    # 2. Vowel / Consonant balance penalty
    natural_tiles = vowel_count + consonant_count

    if natural_tiles > 1:
        if vowel_count == 0:
            # All consonants (e.g. BCDFR)
            equity -= 6.0 + 1.5 * natural_tiles
        elif consonant_count == 0:
            # All vowels (e.g. AEIOU)
            equity -= 7.0 + 2.0 * natural_tiles
        else:
            # Ideal vowel ratio is around 35% - 45% (e.g. 1V:2C or 2V:3C)
            v_ratio = vowel_count / natural_tiles
            if v_ratio > 0.65:
                equity -= (v_ratio - 0.65) * 15.0
            elif v_ratio < 0.25:
                equity -= (0.25 - v_ratio) * 15.0

    # 3. Tactical synergy pairs
    tiles_set = set(tile_counts.keys())
    if blank_count > 0 and "S" in tiles_set:
        equity += STEM_SYNERGIES.get("?S", 5.0)
    if "Q" in tiles_set and "U" in tiles_set:
        equity += STEM_SYNERGIES.get("QU", 6.5)

    # 4. Hierarchical, non-overlapping bingo stem synergies
    # Applies the strongest stem match first without stacking sub-stems on the same tiles
    used_stem_tiles: Set[str] = set()
    for stem, bonus in STEM_HIERARCHY:
        stem_set = set(stem)
        if stem_set.issubset(tiles_set) and not stem_set.intersection(used_stem_tiles):
            equity += bonus
            used_stem_tiles.update(stem_set)

    return round(equity, 2)
