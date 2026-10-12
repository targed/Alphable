"""Alphable V4 Root Package."""

try:
    import torch
    torch.backends.cudnn.enabled = True
    torch.backends.cudnn.benchmark = True
except ImportError:
    pass
