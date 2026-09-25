import os
import torch
import pytest
from alphable.core.alphable_net import AlphableValueNet, load_checkpoint_compatible

def test_net_forward_and_no_dropout():
    net = AlphableValueNet(board_channels=31, state_vector_size=36)
    net.train() # In train mode, check no dropout layer exists
    for module in net.modules():
        assert not isinstance(module, torch.nn.Dropout), "Dropout should be removed from value net"

    b = torch.randn(4, 31, 15, 15)
    s = torch.randn(4, 36)
    out = net(b, s)
    assert out.shape == (4, 1)
    assert (out >= -1.0).all() and (out <= 1.0).all()


def test_net_forward_63_dim_state():
    net = AlphableValueNet(board_channels=31, state_vector_size=63)
    b = torch.randn(3, 31, 15, 15)
    s = torch.randn(3, 63)
    out = net(b, s)
    assert out.shape == (3, 1)
    assert (out >= -1.0).all() and (out <= 1.0).all()

def test_net_gradient_flow():
    net = AlphableValueNet(board_channels=31, state_vector_size=36)
    b = torch.randn(2, 31, 15, 15, requires_grad=True)
    s = torch.randn(2, 36, requires_grad=True)
    out = net(b, s)
    loss = out.sum()
    loss.backward()
    assert b.grad is not None
    assert s.grad is not None
    assert not torch.isnan(b.grad).any()
    assert not torch.isnan(s.grad).any()

def test_load_checkpoint_compatible_exact(tmp_path):
    net1 = AlphableValueNet(board_channels=31, state_vector_size=36, num_res_blocks=1, num_filters=16)
    ckpt_path = str(tmp_path / "exact_model.pth")
    torch.save(net1.state_dict(), ckpt_path)

    net2 = AlphableValueNet(board_channels=31, state_vector_size=36, num_res_blocks=1, num_filters=16)
    loaded, total = load_checkpoint_compatible(net2, ckpt_path)
    assert loaded == total

def test_load_checkpoint_compatible_mismatch(tmp_path):
    # Model with different state vector size
    net_old = AlphableValueNet(board_channels=31, state_vector_size=28, num_res_blocks=1, num_filters=16)
    ckpt_path = str(tmp_path / "wrapped_model.pth")
    # Save with dict wrapper
    torch.save({"model_state_dict": net_old.state_dict()}, ckpt_path)

    net_new = AlphableValueNet(board_channels=31, state_vector_size=36, num_res_blocks=1, num_filters=16)
    loaded, total = load_checkpoint_compatible(net_new, ckpt_path)
    # Some layers (conv trunk) match, but state_fc / fc_final won't match
    assert loaded > 0
    assert loaded < total
