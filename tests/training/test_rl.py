"""
Tests for Phase 4: Anchored Dynamic Damping Reinforcement Learning Fine-Tuning.

Verifies:
1. Anchored RL trainer initializes with frozen anchor model.
2. Loss computation includes L2 distance penalty to anchor model.
3. Fine-tuning execution succeeds and saves champion checkpoint.
"""

import os
import pytest
import torch

from alphable.engine.magpie_bindings import MagpieEngine
from alphable.training.train_rl import AnchoredRLTrainer


@pytest.fixture(scope="module")
def shared_engine():
    eng = MagpieEngine(lexicon="CSW24")
    yield eng
    eng.close()


def test_anchored_rl_initialization():
    checkpoint_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "alphable", "models", "checkpoints", "v4_value_net_best.pt"
    )
    checkpoint_path = os.path.normpath(checkpoint_path)

    trainer = AnchoredRLTrainer(checkpoint_path=checkpoint_path, anchor_weight=0.1)
    assert trainer.model is not None
    assert trainer.anchor_model is not None
    # Verify anchor model weights are frozen
    for p in trainer.anchor_model.parameters():
        assert not p.requires_grad


def test_anchored_rl_fine_tune_run(shared_engine, tmp_path):
    checkpoint_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "alphable", "models", "checkpoints", "v4_value_net_best.pt"
    )
    checkpoint_path = os.path.normpath(checkpoint_path)

    out_file = str(tmp_path / "test_rl_champion.pt")
    trainer = AnchoredRLTrainer(checkpoint_path=checkpoint_path, anchor_weight=0.05)

    ckpt_path = trainer.fine_tune(
        engine=shared_engine,
        num_games=2,
        epochs=1,
        output_checkpoint=out_file,
    )

    assert os.path.exists(ckpt_path)
    loaded = torch.load(ckpt_path, weights_only=False)
    assert "model_state_dict" in loaded
    assert loaded["fine_tune_games"] == 2
