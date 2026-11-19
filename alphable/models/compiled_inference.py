"""
alphable/models/compiled_inference.py

High-throughput compiled TorchScript inference wrapper for V4ValueNetwork.
Eliminates Python dispatch overhead and leverages multi-threaded C++ tensor kernels.
"""

from __future__ import annotations
import os
from typing import Optional
import torch

from alphable.models.value_net import V4ValueNetwork


class CompiledValueNetwork:
    """
    High-performance wrapper executing traced TorchScript models.
    Provides identical evaluate_batch API to V4ValueNetwork.
    """

    def __init__(self, model_path: str, device: str = "cpu"):
        self.device = torch.device(device)
        self.model_path = model_path
        
        if os.path.exists(model_path):
            try:
                self.model = torch.jit.load(model_path, map_location=self.device)
                self.model.eval()
                self.is_compiled = True
            except Exception:
                # Fallback to standard PyTorch model loading state dict
                self.model = V4ValueNetwork(board_channels=32, state_dim=64, feature_dim=512, num_heads=8)
                ckpt = torch.load(model_path, map_location=self.device, weights_only=False)
                if isinstance(ckpt, dict) and "model_state_dict" in ckpt:
                    self.model.load_state_dict(ckpt["model_state_dict"], strict=False)
                elif isinstance(ckpt, dict):
                    self.model.load_state_dict(ckpt, strict=False)
                self.model.to(self.device)
                self.model.eval()
                self.is_compiled = False
        else:
            # Fallback to standard PyTorch model with default architecture
            self.model = V4ValueNetwork(board_channels=32, state_dim=64, feature_dim=512, num_heads=8)
            self.model.to(self.device)
            self.model.eval()
            self.is_compiled = False

    def evaluate_batch(
        self,
        board_tensors: torch.Tensor,
        state_vectors: torch.Tensor,
    ) -> torch.Tensor:
        """
        Evaluates a batch of (board_tensor, state_vector) pairs.

        Args:
            board_tensors: (B, 32, 15, 15) float tensor
            state_vectors: (B, 64) float tensor

        Returns:
            (B, 1) scalar equity predictions
        """
        board_tensors = board_tensors.to(self.device)
        state_vectors = state_vectors.to(self.device)

        with torch.no_grad():
            preds = self.model(board_tensors, state_vectors)

        return preds

    def to(self, device: str) -> CompiledValueNetwork:
        self.device = torch.device(device)
        self.model.to(self.device)
        return self

    def eval(self) -> CompiledValueNetwork:
        self.model.eval()
        return self
