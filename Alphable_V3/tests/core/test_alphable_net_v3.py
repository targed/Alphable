import torch
import pytest
from alphable.core.alphable_net import AlphableValueNet

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
