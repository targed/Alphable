"""
Alphable V4 Hybrid Value Network Architecture.

Combines a 32-channel ResNet-18 spatial board encoder with an 8-head cross-attention
fusion mechanism over the 64-dimensional game state vector, outputting anchored
strategic equity estimates in [-1.0, 1.0].
"""

from __future__ import annotations
import math
from typing import Tuple, Optional, Dict, Any

import torch
import torch.nn as nn
import torch.nn.functional as F


class BasicBlock(nn.Module):
    """ResNet basic residual block with 2 conv layers and skip connection."""
    expansion = 1

    def __init__(self, in_planes: int, planes: int, stride: int = 1):
        super().__init__()
        self.conv1 = nn.Conv2d(
            in_planes, planes, kernel_size=3, stride=stride, padding=1, bias=False
        )
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(
            planes, planes, kernel_size=3, stride=1, padding=1, bias=False
        )
        self.bn2 = nn.BatchNorm2d(planes)

        self.shortcut = nn.Sequential()
        if stride != 1 or in_planes != planes:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_planes, planes, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes),
            )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        out = F.relu(out)
        return out


class ResNet18BoardEncoder(nn.Module):
    """
    ResNet-18 backbone tailored for 32-channel 15x15 Scrabble board representations.
    """

    def __init__(self, in_channels: int = 32, feature_dim: int = 512):
        super().__init__()
        self.in_planes = 64

        # Initial convolution preserves 15x15 spatial resolution
        self.conv1 = nn.Conv2d(
            in_channels, 64, kernel_size=3, stride=1, padding=1, bias=False
        )
        self.bn1 = nn.BatchNorm2d(64)

        # 4 ResNet stages (2 blocks each = 8 residual blocks total)
        self.layer1 = self._make_layer(64, num_blocks=2, stride=1)
        self.layer2 = self._make_layer(128, num_blocks=2, stride=2)
        self.layer3 = self._make_layer(256, num_blocks=2, stride=2)
        self.layer4 = self._make_layer(512, num_blocks=2, stride=2)

        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.proj = nn.Linear(512, feature_dim)

    def _make_layer(self, planes: int, num_blocks: int, stride: int) -> nn.Sequential:
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for s in strides:
            layers.append(BasicBlock(self.in_planes, planes, s))
            self.in_planes = planes * BasicBlock.expansion
        return nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, 32, 15, 15)
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = self.pool(out)
        out = torch.flatten(out, 1)  # (B, 512)
        return self.proj(out)


class StateEncoder(nn.Module):
    """Encodes the 64-dimensional game state vector into feature space."""

    def __init__(self, in_dim: int = 64, feature_dim: int = 512):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 256),
            nn.LayerNorm(256),
            nn.GELU(),
            nn.Linear(256, feature_dim),
            nn.LayerNorm(feature_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class CrossAttentionFusion(nn.Module):
    """
    Multi-head cross-attention: spatial board representations attend to
    game state vector (score margin, remaining bag, rack letters, belief confidence).
    """

    def __init__(self, embed_dim: int = 512, num_heads: int = 8, dropout: float = 0.1):
        super().__init__()
        self.cross_attn = nn.MultiheadAttention(
            embed_dim=embed_dim, num_heads=num_heads, dropout=dropout, batch_first=True
        )
        self.norm1 = nn.LayerNorm(embed_dim)
        self.ffn = nn.Sequential(
            nn.Linear(embed_dim, embed_dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(embed_dim * 2, embed_dim),
        )
        self.norm2 = nn.LayerNorm(embed_dim)

    def forward(self, board_feat: torch.Tensor, state_feat: torch.Tensor) -> torch.Tensor:
        # Shapes: board_feat: (B, D), state_feat: (B, D)
        q = board_feat.unsqueeze(1)  # (B, 1, D)
        k = state_feat.unsqueeze(1)  # (B, 1, D)
        v = state_feat.unsqueeze(1)  # (B, 1, D)

        attended, _ = self.cross_attn(query=q, key=k, value=v)
        x = self.norm1(board_feat + attended.squeeze(1))
        out = self.norm2(x + self.ffn(x))
        return out


class V4ValueNetwork(nn.Module):
    """
    Alphable V4 Hybrid ResNet-18 + Cross-Attention Value Network.
    """

    def __init__(
        self,
        board_channels: int = 32,
        state_dim: int = 64,
        feature_dim: int = 512,
        num_heads: int = 8,
    ):
        super().__init__()
        self.board_encoder = ResNet18BoardEncoder(
            in_channels=board_channels, feature_dim=feature_dim
        )
        self.state_encoder = StateEncoder(in_dim=state_dim, feature_dim=feature_dim)
        self.fusion = CrossAttentionFusion(embed_dim=feature_dim, num_heads=num_heads)

        # Equity Prediction Head
        self.equity_head = nn.Sequential(
            nn.Linear(feature_dim, 128),
            nn.LayerNorm(128),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(128, 32),
            nn.GELU(),
            nn.Linear(32, 1),
            nn.Tanh(),  # Bounded equity output in [-1.0, 1.0]
        )

    def forward(
        self, board_tensor: torch.Tensor, state_vector: torch.Tensor
    ) -> torch.Tensor:
        """
        Forward pass.
        Args:
            board_tensor: (B, 32, 15, 15)
            state_vector: (B, 64)
        Returns:
            equity: (B, 1) in [-1.0, 1.0]
        """
        board_feat = self.board_encoder(board_tensor)
        state_feat = self.state_encoder(state_vector)
        fused = self.fusion(board_feat, state_feat)
        equity = self.equity_head(fused)
        return equity

    @torch.no_grad()
    def evaluate_batch(
        self, board_tensors: torch.Tensor, state_vectors: torch.Tensor
    ) -> torch.Tensor:
        """Fast inference evaluation for move candidates."""
        self.eval()
        return self(board_tensors, state_vectors)
