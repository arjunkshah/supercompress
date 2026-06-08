"""Load the bundled ~5K-param SuperCompress policy."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import torch

from supercompress.features import FEATURE_DIM
from supercompress.model import EvictionPolicyNetwork
from supercompress.policies import LearnedPolicy

PKG_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATHS = (
    PKG_ROOT / "checkpoints" / "default.pt",
    PKG_ROOT / "checkpoints" / "harbor_policy.pt",
)


def resolve_checkpoint(explicit: Optional[str | Path] = None) -> Path:
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise FileNotFoundError(f"Checkpoint not found: {p}")
        return p
    for p in DEFAULT_PATHS:
        if p.exists():
            return p
    raise FileNotFoundError(
        "No memory checkpoint. Run: supercompress-train --fast"
    )


def load_policy(
    checkpoint: Optional[str | Path] = None,
    device: str = "cpu",
) -> tuple[EvictionPolicyNetwork, LearnedPolicy, Path]:
    ckpt_path = resolve_checkpoint(checkpoint)
    model = EvictionPolicyNetwork(feature_dim=FEATURE_DIM, hidden_dim=64)
    try:
        state = torch.load(ckpt_path, map_location=device, weights_only=True)
    except TypeError:
        state = torch.load(ckpt_path, map_location=device)
    model.load_state_dict(state)
    model.eval()
    return model, LearnedPolicy(model, device=device), ckpt_path
