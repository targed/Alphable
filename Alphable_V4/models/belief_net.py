"""
Opponent Hidden Rack Belief Network for Alphable V4.

Provides both:
1. Fast Bayesian inference (Dirichlet-Multinomial over remaining unseen tiles)
2. Neural belief inference using visible board and play history.
"""

from __future__ import annotations
import math
import copy
from typing import List, Dict, Optional, Tuple, Any
from collections import Counter
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from alphable_v4.engine.game_state import GameState, STANDARD_TILE_COUNTS
from alphable_v4.engine.move import Move


class OpponentTracker:
    """
    Tracks opponent move history and maintains posterior tile likelihood weights.
    
    Applies Bayesian negative evidence updates:
    If an opponent plays a low-scoring move while high-scoring plays or hooks
    requiring power tiles (e.g., ?, S, Z, Q, X, J) were available on the board,
    the posterior likelihood of the opponent holding those power tiles is decayed.
    When opponent plays and draws new tiles, posterior weights regress toward 1.0.
    """

    def __init__(self):
        self.tile_weights: Dict[str, float] = {
            chr(ord('A') + i): 1.0 for i in range(26)
        }
        self.tile_weights['?'] = 1.0
        self.history: List[Dict[str, Any]] = []

    def reset(self):
        """Resets all tile weights back to prior 1.0."""
        for t in self.tile_weights:
            self.tile_weights[t] = 1.0
        self.history.clear()

    def update_after_opponent_move(
        self,
        opp_move: Move,
        state_before: Optional[GameState] = None,
        engine: Optional[Any] = None,
    ) -> None:
        """
        Updates posterior tile weights given opponent's move.
        
        - If exchange/pass: sharp decay on ?, S, and high-value tiles.
        - If low scoring move (< 25 pts): decay ? and unplayed power tiles.
        - Replenishment: freshly drawn tiles regress rack weights toward 1.0.
        """
        tiles_played = 0
        if opp_move.is_exchange:
            # Exchanged tiles: highly unlikely to hold blank or S
            self.tile_weights['?'] = max(0.05, self.tile_weights['?'] * 0.15)
            self.tile_weights['S'] = max(0.10, self.tile_weights['S'] * 0.25)
            tiles_played = len(opp_move.word) if opp_move.word else 3
        elif opp_move.is_pass:
            # Passed: no legal moves available
            self.tile_weights['?'] = max(0.05, self.tile_weights['?'] * 0.10)
            self.tile_weights['S'] = max(0.05, self.tile_weights['S'] * 0.15)
            tiles_played = 0
        else:
            # Placement move
            tiles_played = len(opp_move.tiles_placed) if opp_move.tiles_placed else 1
            if opp_move.score < 25:
                # Modest score: decay blank likelihood
                self.tile_weights['?'] = max(0.08, self.tile_weights['?'] * 0.40)
                
                # If engine and state_before are available, inspect missed high-scoring plays
                if engine is not None and state_before is not None:
                    try:
                        top_plays = engine.generate_moves(game_state=state_before, max_candidates=10)
                        for tp in top_plays:
                            if tp.score >= 38:
                                for ch in tp.tiles_placed.upper():
                                    if ch in ('?', 'Z', 'Q', 'X', 'J', 'S'):
                                        self.tile_weights[ch] = max(0.10, self.tile_weights[ch] * 0.35)
                    except Exception:
                        pass
            elif opp_move.score >= 50:
                # Opponent played a bingo or explosive play; reset blank/? weight to normal
                self.tile_weights['?'] = 1.0
                self.tile_weights['S'] = 1.0

        # Replenishment from bag:
        # The opponent keeps (7 - tiles_played) tiles and draws tiles_played from the bag
        # New bag tiles have prior weight 1.0
        kept = max(0, 7 - tiles_played)
        drawn = min(7, tiles_played)
        if kept + drawn > 0:
            kept_frac = kept / (kept + drawn)
            drawn_frac = drawn / (kept + drawn)
            for t in self.tile_weights:
                self.tile_weights[t] = float(kept_frac * self.tile_weights[t] + drawn_frac * 1.0)

        self.history.append({
            "move": opp_move,
            "tiles_played": tiles_played,
            "weights_snapshot": dict(self.tile_weights),
        })


class BayesianRackInference:
    """
    Bayesian Opponent Rack Inference Engine.
    
    Given the current game state and unseen tiles pool (tiles not on board
    and not on our rack), samples opponent racks from the exact hypergeometric /
    Dirichlet-multinomial tile probability distribution.
    """

    def __init__(self, default_rack_size: int = 7):
        self.default_rack_size = default_rack_size

    def get_unseen_tile_pool(self, state: GameState) -> List[str]:
        """Returns the full list of remaining unseen tiles."""
        pool: List[str] = []
        for tile, count in state.unseen_counts.items():
            pool.extend([tile] * count)
        return pool

    def sample_opponent_racks(
        self,
        state: GameState,
        num_samples: int = 64,
        rack_size: Optional[int] = None,
        seed: Optional[int] = None,
        tracker: Optional[OpponentTracker] = None,
    ) -> List[List[str]]:
        """
        Samples num_samples opponent racks without replacement from unseen tiles pool.
        
        When tracker is provided, samples according to posterior tile likelihoods
        using Bayesian negative evidence filtering.
        Uses Common Random Numbers (CRN) when seed is fixed.
        """
        rng = np.random.RandomState(seed) if seed is not None else np.random
        pool = self.get_unseen_tile_pool(state)
        total_unseen = len(pool)

        if rack_size is None:
            # If known opp_rack size or remaining tiles
            rack_size = min(self.default_rack_size, total_unseen)

        if total_unseen <= rack_size:
            # Deterministic: opponent holds all remaining unseen tiles
            return [list(pool) for _ in range(num_samples)]

        pool_arr = np.array(pool)

        if tracker is not None:
            weights = np.array([
                max(0.01, tracker.tile_weights.get(t.upper(), 1.0))
                for t in pool
            ], dtype=np.float64)
            w_sum = weights.sum()
            probs = weights / w_sum if w_sum > 0 else None

            samples: List[List[str]] = []
            for _ in range(num_samples):
                drawn_indices = rng.choice(total_unseen, size=rack_size, replace=False, p=probs)
                samples.append(pool_arr[drawn_indices].tolist())
            return samples
        else:
            samples: List[List[str]] = []
            for _ in range(num_samples):
                drawn_indices = rng.choice(total_unseen, size=rack_size, replace=False)
                samples.append(pool_arr[drawn_indices].tolist())
            return samples

    def compute_belief_confidence(self, state: GameState) -> float:
        """
        Calculates a normalized certainty metric [0.0, 1.0] about opponent's rack.
        Certainty approaches 1.0 as the unseen bag pool shrinks toward 0 (endgame).
        """
        total_unseen = sum(state.unseen_counts.values())
        if total_unseen <= 7:
            return 1.0
        # Sigmoid-like transition from midgame (80 unseen -> ~0.15) to endgame (7 unseen -> 1.0)
        conf = 1.0 - min(1.0, (total_unseen - 7) / 79.0)
        return float(conf)


class NeuralBeliefNet(nn.Module):
    """
    Feed-forward neural belief network predicting 27-class opponent rack distribution.
    """

    def __init__(self, state_dim: int = 64, hidden_dim: int = 256):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 27),
            nn.Softmax(dim=-1),
        )

    def forward(self, state_vec: torch.Tensor) -> torch.Tensor:
        if state_vec.dim() == 1:
            state_vec = state_vec.unsqueeze(0)
        return self.fc(state_vec)
