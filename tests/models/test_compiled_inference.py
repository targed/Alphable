"""
tests/models/test_compiled_inference.py

Unit tests for CompiledValueNetwork (TorchScript C++ inference execution)
and numerical parity with standard PyTorch V4ValueNetwork.
"""

import os
import pytest
import torch

from alphable_v4.models.value_net import V4ValueNetwork
from alphable_v4.models.compiled_inference import CompiledValueNetwork
from alphable_v4.search.bams import BAMSSearch, BAMSConfig
from alphable_v4.engine.magpie_bindings import MagpieEngine


CHECKPOINT_PATH = "alphable_v4/models/checkpoints/v4_value_net_best.pt"
COMPILED_PATH = "alphable_v4/models/checkpoints/v4_value_net_compiled.pt"


@pytest.mark.unit
def test_compiled_value_net_loading():
    """Verifies CompiledValueNetwork loads successfully and flags compiled status."""
    if not os.path.exists(COMPILED_PATH):
        pytest.skip("Compiled model checkpoint not found.")

    net = CompiledValueNetwork(COMPILED_PATH, device="cpu")
    assert net.is_compiled is True
    assert net.model is not None


@pytest.mark.unit
def test_compiled_numerical_parity():
    """Verifies TorchScript compiled model produces outputs identical to eager PyTorch model."""
    if not os.path.exists(COMPILED_PATH) or not os.path.exists(CHECKPOINT_PATH):
        pytest.skip("Model checkpoints not found.")

    # Load standard model
    orig_net = V4ValueNetwork(board_channels=32, state_dim=64, feature_dim=512, num_heads=8)
    ckpt = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
    if "model_state_dict" in ckpt:
        orig_net.load_state_dict(ckpt["model_state_dict"], strict=False)
    else:
        orig_net.load_state_dict(ckpt, strict=False)
    orig_net.eval()

    # Load compiled model
    compiled_net = CompiledValueNetwork(COMPILED_PATH, device="cpu")

    # Generate synthetic inputs
    torch.manual_seed(42)
    board_batch = torch.randn(8, 32, 15, 15)
    state_batch = torch.randn(8, 64)

    with torch.no_grad():
        orig_out = orig_net.evaluate_batch(board_batch, state_batch)
        comp_out = compiled_net.evaluate_batch(board_batch, state_batch)

    # Parity check: max difference should be < 1e-4
    diff = torch.max(torch.abs(orig_out - comp_out)).item()
    assert diff < 1e-4, f"Output divergence exceeds tolerance: max diff {diff}"


@pytest.mark.unit
def test_compiled_fallback_nonexistent():
    """Verifies safe fallback when compiled file does not exist."""
    net = CompiledValueNetwork("non_existent_path.pt", device="cpu")
    assert net.is_compiled is False

    # Should still evaluate without crashing
    board_batch = torch.randn(2, 32, 15, 15)
    state_batch = torch.randn(2, 64)
    out = net.evaluate_batch(board_batch, state_batch)
    assert out.shape == (2, 1)


@pytest.mark.unit
def test_bams_loads_compiled_model(tmp_path):
    """Verifies BAMSSearch.from_checkpoint automatically utilizes compiled model."""
    if not os.path.exists(COMPILED_PATH) or not os.path.exists(CHECKPOINT_PATH):
        pytest.skip("Model checkpoints not found.")

    engine = MagpieEngine()
    bams = BAMSSearch.from_checkpoint(engine, CHECKPOINT_PATH)
    assert bams.value_net is not None
    assert isinstance(bams.value_net, CompiledValueNetwork)
    assert bams.value_net.is_compiled is True
