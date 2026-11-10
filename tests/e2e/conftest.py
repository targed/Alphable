"""
Shared Pytest Fixtures for Alphable V4 E2E Test Suite.
"""

import os
import pytest
from typing import Generator

from alphable_v4.engine.game_state import GameState
from alphable_v4.engine.magpie_bindings import MagpieEngine
from alphable_v4.search.bams import BAMSConfig


@pytest.fixture(scope="session")
def shared_engine() -> Generator[MagpieEngine, None, None]:
    """Session-scoped MAGPIE engine initialized with CSW24 lexicon."""
    engine = MagpieEngine(lexicon="CSW24")
    yield engine
    engine.close()


@pytest.fixture(scope="session")
def shared_nwl_engine() -> Generator[MagpieEngine, None, None]:
    """Session-scoped MAGPIE engine initialized with NWL23 lexicon."""
    engine = MagpieEngine(lexicon="NWL23")
    yield engine
    engine.close()


@pytest.fixture(scope="session")
def checkpoint_path() -> str:
    """Absolute path to the V4 Champion Value Network checkpoint."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.normpath(
        os.path.join(base_dir, "..", "..", "alphable_v4", "models", "checkpoints", "v4_value_net_best.pt")
    )
    assert os.path.exists(path), f"Checkpoint not found at: {path}"
    return path


@pytest.fixture(scope="session")
def rl_checkpoint_path() -> str:
    """Absolute path to the RL Gen-1 Value Network checkpoint."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.normpath(
        os.path.join(base_dir, "..", "..", "alphable_v4", "models", "checkpoints", "v4_value_net_rl_gen1.pt")
    )
    assert os.path.exists(path), f"RL Checkpoint not found at: {path}"
    return path


@pytest.fixture
def fast_bams_config() -> BAMSConfig:
    """Fast, deterministic BAMS search configuration for E2E testing."""
    return BAMSConfig(
        num_samples=4,
        candidate_beam=4,
        max_static_deficit=3.0,
        nested_2ply=False,
        candidate_beam_2ply=0,
        samples_2ply=0,
        use_volatility_control=True,
        volatility_weight=0.4,
        dynamic_beam=False,
        use_exact_endgame=True,
        use_pre_endgame=True,
        seed=42,
        device="cpu",
    )


@pytest.fixture
def fast_2ply_bams_config() -> BAMSConfig:
    """Fast, deterministic 2-ply BAMS configuration for E2E testing."""
    return BAMSConfig(
        num_samples=4,
        candidate_beam=4,
        max_static_deficit=3.0,
        nested_2ply=True,
        candidate_beam_2ply=2,
        samples_2ply=2,
        weight_2ply=0.18,
        use_volatility_control=True,
        volatility_weight=0.4,
        dynamic_beam=False,
        use_exact_endgame=True,
        use_pre_endgame=True,
        seed=42,
        device="cpu",
    )


@pytest.fixture
def standard_opening_state() -> GameState:
    """Standard fresh board state with opening rack."""
    return GameState(
        rack=["A", "E", "I", "N", "R", "S", "T"],
        opp_rack=["C", "A", "B", "I", "N", "E", "T"],
        score=0,
        opp_score=0,
        bag_count=86,
        scoreless_turns=0,
        lexicon="CSW24",
    )


@pytest.fixture
def midgame_state() -> GameState:
    """Clustered midgame board state with center play."""
    state = GameState(
        rack=["R", "E", "T", "I", "N", "A", "S"],
        opp_rack=["B", "E", "A", "S", "T", "L", "Y"],
        score=120,
        opp_score=110,
        bag_count=54,
        scoreless_turns=0,
        lexicon="CSW24",
    )
    # Place 'TRAIN' across center row 8 (0-indexed row 7, cols 7..11)
    state.board[7][7] = "T"
    state.board[7][8] = "R"
    state.board[7][9] = "A"
    state.board[7][10] = "I"
    state.board[7][11] = "N"
    return state
