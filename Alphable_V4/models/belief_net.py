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
    ) -> List[List[str]]:
        """
        Samples num_samples opponent racks without replacement from unseen tiles pool.
        
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

        samples: List[List[str]] = []
        pool_arr = np.array(pool)

        for _ in range(num_samples):
            # Sample rack_size tiles without replacement from unseen pool
            drawn_indices = rng.choice(total_unseen, size=rack_size, replace=False)
            sampled_rack = pool_arr[drawn_indices].tolist()
            samples.append(sampled_rack)

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
