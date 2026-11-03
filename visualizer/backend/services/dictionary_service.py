"""
Dictionary and Word Definition Service for Visualizer Studio.
Provides lexicon validity verification (CSW24 & NWL23) and definition lookup.
"""

import os
import re
import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
CSW24_PATH = BASE_DIR / "resources" / "CSW24.txt"
NWL23_PATH = BASE_DIR / "resources" / "NWL23.txt"

# Standard Scrabble Letter Point Values
LETTER_POINTS = {
    'A': 1, 'B': 3, 'C': 3, 'D': 2, 'E': 1, 'F': 4, 'G': 2, 'H': 4, 'I': 1,
    'J': 8, 'K': 5, 'L': 1, 'M': 3, 'N': 1, 'O': 1, 'P': 3, 'Q': 10, 'R': 1,
    'S': 1, 'T': 1, 'U': 1, 'V': 4, 'W': 4, 'X': 8, 'Y': 4, 'Z': 10, '?': 0
}


class DictionaryService:
    """Manages lexicon word validation and word definition retrieval."""

    def __init__(self):
        self._csw24_set: Optional[set] = None
        self._nwl23_defs: Optional[Dict[str, str]] = None
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _ensure_loaded(self):
        if self._csw24_set is None:
            csw = set()
            if CSW24_PATH.exists():
                with open(CSW24_PATH, "r", encoding="utf-8") as f:
                    for line in f:
                        w = line.strip().split()
                        if w:
                            csw.add(w[0].upper())
            self._csw24_set = csw

        if self._nwl23_defs is None:
            nwl = {}
            if NWL23_PATH.exists():
                with open(NWL23_PATH, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split(" ", 1)
                        if parts and parts[0]:
                            w = parts[0].upper()
                            d = parts[1] if len(parts) > 1 else ""
                            nwl[w] = d
            self._nwl23_defs = nwl

    def lookup_word(self, word: str, lexicon: str = "CSW24") -> Dict[str, Any]:
        """
        Looks up word validity, letter score, part of speech, and definition.
        """
        clean_word = re.sub(r'[^A-Za-z]', '', word).upper()
        if not clean_word:
            return {
                "word": word,
                "valid": False,
                "lexicon": lexicon,
                "valid_csw24": False,
                "valid_nwl23": False,
                "length": 0,
                "score": 0,
                "definition": "Empty or invalid query.",
                "part_of_speech": "",
                "source": "None"
            }

        cache_key = f"{clean_word}_{lexicon.upper()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        self._ensure_loaded()

        in_csw = clean_word in self._csw24_set
        in_nwl = clean_word in self._nwl23_defs
        lex_upper = lexicon.upper()
        is_valid = in_csw if lex_upper.startswith("CSW") else in_nwl

        # Base tile score calculation
        score = sum(LETTER_POINTS.get(ch, 0) for ch in clean_word)

        # Curated Collins Scrabble glosses for historical / British tournament words
        COLLINS_GLOSSARY = {
            'SAULIE': ('noun', 'a hired mourner at a funeral (Scottish)'),
            'SAULIES': ('noun', 'plural of SAULIE: hired mourners at a funeral (Scottish)'),
            'CATERAN': ('noun', 'a Highland marauder or irregular soldier'),
            'CATERANS': ('noun', 'plural of CATERAN: Highland marauders'),
            'OUGIYA': ('noun', 'a monetary unit of Mauritania'),
            'OUGIYAS': ('noun', 'plural of OUGIYA'),
            'CHIRK': ('verb', 'to make a shrill chirping sound'),
            'CHIRKS': ('verb', 'third person present of CHIRK'),
            'CHIRKED': ('verb', 'past tense of CHIRK'),
            'KYBOSH': ('noun', 'something that stops or finishes something; kibosh'),
            'KYBOSHES': ('noun', 'plural of KYBOSH'),
            'ZA': ('noun', 'slang for pizza'),
            'ZAS': ('noun', 'plural of ZA'),
            'QI': ('noun', 'the circulating life force in Chinese philosophy'),
            'QIS': ('noun', 'plural of QI'),
        }

        # 1. Check local NWL dictionary definitions first
        definition_text = ""
        pos_text = ""
        source = "None"

        if in_nwl and self._nwl23_defs.get(clean_word):
            raw_def = self._nwl23_defs[clean_word]
            pos_match = re.search(r'\[([a-z]+)[^\]]*\]', raw_def)
            if pos_match:
                pos_map = {
                    'n': 'noun', 'v': 'verb', 'adj': 'adjective',
                    'adv': 'adverb', 'interj': 'interjection', 'prep': 'preposition'
                }
                pos_key = pos_match.group(1).lower()
                pos_text = pos_map.get(pos_key, pos_key)

            clean_def = re.sub(r'\[.*?\]', '', raw_def)
            clean_def = re.sub(r'\{([^}=]+)=?[^}]*\}', r'\1', clean_def).strip()
            definition_text = clean_def
            source = "NWL23 Official"

        # 1.5 Check Collins glossary
        if not definition_text and clean_word in COLLINS_GLOSSARY:
            pos_text, definition_text = COLLINS_GLOSSARY[clean_word]
            source = "CSW24 Collins Glossary"

        # 1.8 Check morphological inflections in NWL (plural / verb forms)
        if not definition_text:
            stems = []
            if clean_word.endswith('IES') and len(clean_word) > 4:
                stems.append((clean_word[:-3] + 'Y', 'plural of'))
                stems.append((clean_word[:-1], 'plural of'))
            elif clean_word.endswith('ES') and len(clean_word) > 3:
                stems.append((clean_word[:-2], 'plural/third-person of'))
                stems.append((clean_word[:-1], 'plural of'))
            elif clean_word.endswith('S') and len(clean_word) > 2:
                stems.append((clean_word[:-1], 'plural of'))
            if clean_word.endswith('ING') and len(clean_word) > 4:
                stems.append((clean_word[:-3], 'present participle of'))
                stems.append((clean_word[:-3] + 'E', 'present participle of'))
            if clean_word.endswith('ED') and len(clean_word) > 3:
                stems.append((clean_word[:-2], 'past tense of'))
                stems.append((clean_word[:-1], 'past tense of'))

            for stem, rel in stems:
                if stem in self._nwl23_defs and self._nwl23_defs[stem]:
                    stem_def = re.sub(r'\[.*?\]', '', self._nwl23_defs[stem])
                    stem_def = re.sub(r'\{([^}=]+)=?[^}]*\}', r'\1', stem_def).strip()
                    definition_text = f"{rel.capitalize()} {stem}: {stem_def}"
                    pos_text = "inflection"
                    source = "NWL23 (Derived)"
                    break

        # 2. If not found in NWL or definition is blank, query Datamuse API
        if not definition_text and is_valid:
            try:
                url = f"https://api.datamuse.com/words?sp={urllib.parse.quote(clean_word.lower())}&md=d&max=5"
                req = urllib.request.Request(url, headers={"User-Agent": "AlphableStudio/2.0"})
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    api_data = json.loads(resp.read().decode())
                    if api_data and isinstance(api_data, list):
                        for item in api_data:
                            if item.get("word", "").upper() == clean_word and item.get("defs"):
                                raw = item["defs"][0]
                                parts = raw.split("\t", 1)
                                if len(parts) == 2:
                                    pos_abbr = parts[0]
                                    pos_map = {'n': 'noun', 'v': 'verb', 'adj': 'adjective', 'adv': 'adverb'}
                                    pos_text = pos_map.get(pos_abbr, pos_abbr)
                                    definition_text = parts[1].strip()
                                else:
                                    definition_text = raw.strip()
                                source = "Public Dictionary"
                                break
            except Exception:
                pass

        if not definition_text:
            if is_valid:
                definition_text = f"Official tournament word in {lex_upper} (worth {score} base points). Acceptable move in competition."
                pos_text = "tournament word"
            else:
                definition_text = f"Not an acceptable word in official {lex_upper} lexicon."

        result = {
            "word": clean_word,
            "valid": is_valid,
            "lexicon": lex_upper,
            "valid_csw24": in_csw,
            "valid_nwl23": in_nwl,
            "length": len(clean_word),
            "score": score,
            "definition": definition_text,
            "part_of_speech": pos_text,
            "source": source
        }

        self._cache[cache_key] = result
        return result


dictionary_service = DictionaryService()
