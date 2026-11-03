"""
Woogles Platform Integration Bot for Alphable V4.

Provides the player agent bridge between Woogles.io games and BAMSSearch.
Translates Woogles board representations and notation into Alphable V4 GameState,
invokes BAMS search, and formats moves in Woogles coordinate notation (e.g., '8D CATS' or 'D8 CATS').
"""

from __future__ import annotations
import os
import sys
import time
from typing import Dict, List, Tuple, Optional, Any

from alphable_v4.engine.move import Move
from alphable_v4.engine.game_state import GameState
from alphable_v4.engine.magpie_bindings import MagpieEngine
from alphable_v4.search.bams import BAMSSearch, BAMSConfig


class WooglesBotAgent:
    """
    Alphable V4 Game Agent for Woogles.io matches.
    """

    def __init__(
        self,
        engine: MagpieEngine,
        checkpoint_path: Optional[str] = None,
        lexicon: str = "CSW24",
        num_samples: int = 32,
        candidate_beam: int = 15,
        seed: Optional[int] = None,
    ):
        self.engine = engine
        self.lexicon = lexicon
        self.engine.set_lexicon(lexicon)

        self.config = BAMSConfig(
            num_samples=num_samples,
            candidate_beam=candidate_beam,
            seed=seed,
        )

        if checkpoint_path and os.path.exists(checkpoint_path):
            self.search = BAMSSearch.from_checkpoint(
                engine=self.engine,
                checkpoint_path=checkpoint_path,
                config=self.config,
            )
        else:
            self.search = BAMSSearch(
                engine=self.engine,
                config=self.config,
            )

    def select_action(
        self,
        board: List[List[Optional[str]]],
        rack: List[str],
        score: int = 0,
        opp_score: int = 0,
        unseen_counts: Optional[Dict[str, int]] = None,
        bag_count: int = 86,
    ) -> Tuple[Move, str, Dict[str, Any]]:
        """
        Receives current board & rack, executes BAMS, and formats Woogles command string.

        Returns:
            (selected_move, woogles_command_str, metadata)
        """
        state = GameState(
            board=board,
            rack=[r.upper() for r in rack],
            score=score,
            opp_score=opp_score,
            unseen_counts=unseen_counts,
            bag_count=bag_count,
            lexicon=self.lexicon,
        )

        move, meta = self.search.select_move(state)

        # Format Woogles string
        if not move.is_placement:
            if move.word == "--":
                cmd_str = "pass"
            else:
                cmd_str = f"exchange {move.word}"
        else:
            coord_str = move.to_woogles_coord()
            cmd_str = f"play {coord_str} {move.word}"

        return move, cmd_str, meta

    def set_lexicon(self, lexicon: str) -> None:
        """Dynamically switches lexicon between CSW24 and NWL23."""
        self.lexicon = lexicon
        self.engine.set_lexicon(lexicon)
