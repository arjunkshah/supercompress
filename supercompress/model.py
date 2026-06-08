"""EvictionPolicyNetwork — lightweight MLP over per-token metadata."""

from __future__ import annotations

import torch
import torch.nn as nn


class EvictionPolicyNetwork(nn.Module):
    """
    Scores each token for retention (higher = more likely to keep in KV cache).

    Input: (batch, seq_len, feature_dim) per-token metadata
    Output: (batch, seq_len) keep logits
    """

    def __init__(self, feature_dim: int = 9, hidden_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(feature_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        """
        Args:
            features: (B, T, F) or (T, F)
        Returns:
            logits: (B, T) or (T,) keep scores
        """
        if features.dim() == 2:
            logits = self.net(features).squeeze(-1)
            return logits
        logits = self.net(features).squeeze(-1)
        return logits

    def keep_scores(self, features: torch.Tensor) -> torch.Tensor:
        """Sigmoid probabilities for retention."""
        return torch.sigmoid(self.forward(features))
