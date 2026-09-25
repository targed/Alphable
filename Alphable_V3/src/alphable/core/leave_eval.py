"""
Empirical Rack Leave Valuation and Synergy Modeling for Alphable.

Based on tournament Scrabble empirical equity tables (Lipkin-Smith / Super-Leaves).
Evaluates the expected future scoring equity of tiles remaining in hand after a move,
accounting for high-value synergy tiles (?, S), bingo stems (TISANE), duplicate penalties,
and vowel/consonant balance.
"""

from typing import List, Union, Dict

# Single tile equity values (baseline points added to expected equity)
BASE_TILE_EQUITY: Dict[str, float] = {
    "?": 26.5,   # Blank is the highest equity tile in Scrabble (+25 to +30 pts)
    "S": 8.2,    # Pluralizer and hook master (+8 to +10 pts)
    "Z": 3.2,    # High point tile that plays easily on DL/TL
    "X": 3.0,    # Plays easily on 2-letter words (AX, EX, OX, XI, XU)
    "H": 1.2,
    "C": 1.0,
    "D": 0.8,
    "M": 0.5,
    "P": 0.4,
    "T": 0.3,
    "R": 0.2,
    "E": 0.1,
    "N": 0.0,
    "A": -0.2,
    "L": -0.5,
    "I": -0.8,
    "O": -1.5,
    "G": -1.5,
    "B": -2.0,
    "K": -2.0,
    "F": -2.2,
    "Y": -2.2,
    "J": -3.0,
    "W": -3.5,
    "U": -4.0,
    "V": -5.5,   # Hard to dump, few 2-letter words
    "Q": -7.5,   # Massive liability without U
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

# Synergy bonuses for classic 2-tile and 3-tile bingo stems
STEM_SYNERGIES: Dict[str, float] = {
    "?S": 5.0,
    "ER": 2.5,
    "ES": 3.0,
    "IN": 2.0,
    "RE": 2.5,
    "ST": 2.5,
    "RS": 2.5,
    "QU": 6.5,   # Neutralizes Q penalty
}


def compute_leave_equity(rack: Union[List[str], str]) -> float:
    """
    Computes the strategic expected equity (in Scrabble points) of a rack leave.

    Args:
        rack: List or string of tiles remaining in rack (e.g. ['A', 'E', 'R', 'T'] or "AERT").

    Returns:
        float: Expected leave equity in points (can be positive or negative).
    """
    if not rack:
        return 0.0

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

    # 1. Duplicate tile penalties (e.g. holding II, UUU, VV)
    for tile, count in tile_counts.items():
        if count > 1:
            pen = DUPLICATE_PENALTIES.get(tile, -2.5)
            # Escalating penalty for 3+ of same tile
            excess = count - 1
            equity += pen * excess * (1.2 ** (excess - 1))

    # 2. Vowel / Consonant balance penalty
    leave_len = len(rack)
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

    # 3. Two-letter synergy bonus
    tiles_set = set(tile_counts.keys())
    if blank_count > 0 and "S" in tiles_set:
        equity += STEM_SYNERGIES.get("?S", 5.0)
    if "Q" in tiles_set and "U" in tiles_set:
        equity += STEM_SYNERGIES.get("QU", 6.5)
    if "E" in tiles_set and "R" in tiles_set:
        equity += STEM_SYNERGIES.get("ER", 2.5)
    if "I" in tiles_set and "N" in tiles_set:
        equity += STEM_SYNERGIES.get("IN", 2.0)
    if "S" in tiles_set and "T" in tiles_set:
        equity += STEM_SYNERGIES.get("ST", 2.5)

    return round(equity, 2)
