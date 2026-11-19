"""
Tests for backwards compatibility shims in alphable/__init__.py.

Ensures existing checkpoints, unpicklers, and legacy scripts referencing
`alphable_v4` continue to resolve seamlessly to `alphable`.
"""

import sys
import torch
import alphable


def test_alphable_v4_root_alias():
    """Verify that importing alphable_v4 resolves to the alphable module."""
    import alphable_v4
    assert alphable_v4 is alphable


def test_alphable_v4_submodule_aliases():
    """Verify that all major submodules resolve identically under alphable_v4."""
    import alphable_v4.engine as engine
    import alphable_v4.models as models
    import alphable_v4.platform as platform
    import alphable_v4.search as search
    import alphable_v4.training as training

    assert engine is alphable.engine
    assert models is alphable.models
    assert platform is alphable.platform
    assert search is alphable.search
    assert training is alphable.training


def test_alphable_v4_leaf_aliases():
    """Verify that commonly imported leaf classes/modules resolve identically."""
    from alphable_v4.engine.game_state import GameState
    from alphable_v4.engine.magpie_bindings import MagpieEngine
    from alphable_v4.models.value_net import V4ValueNetwork
    from alphable_v4.models.belief_net import NeuralBeliefNet
    from alphable_v4.search.bams import BAMSSearch
    from alphable_v4.platform.eval import GameSimulator

    assert GameState is alphable.engine.game_state.GameState
    assert MagpieEngine is alphable.engine.magpie_bindings.MagpieEngine
    assert V4ValueNetwork is alphable.models.value_net.V4ValueNetwork
    assert NeuralBeliefNet is alphable.models.belief_net.NeuralBeliefNet
    assert BAMSSearch is alphable.search.bams.BAMSSearch
    assert GameSimulator is alphable.platform.eval.GameSimulator


def test_checkpoint_unpickling_backwards_compat():
    """Verify that pre-trained checkpoints pickled under older schemas load without error."""
    ckpt_path = "alphable/models/checkpoints/v4_value_net_best.pt"
    checkpoint = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    assert "model_state_dict" in checkpoint
    net = alphable.models.value_net.V4ValueNetwork()
    net.load_state_dict(checkpoint["model_state_dict"])
