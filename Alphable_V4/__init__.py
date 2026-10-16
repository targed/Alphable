"""Alphable V4 Root Package."""

try:
    import torch
    torch.backends.cudnn.enabled = False
    torch.backends.cudnn.benchmark = False
except ImportError:
    pass
