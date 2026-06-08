"""Nebius integration — lazy exports to avoid config import cycles."""

from __future__ import annotations

from typing import TYPE_CHECKING

from supercompress.stack.nebius.models import (
    DEFAULT_NEBIUS_MODEL,
    DEPRECATED_NEBIUS_MODELS,
    FALLBACK_NEBIUS_MODELS,
    normalize_nebius_model,
)

if TYPE_CHECKING:
    from supercompress.stack.nebius.client import InferenceResult, NebiusClient

__all__ = [
    "DEFAULT_NEBIUS_MODEL",
    "DEPRECATED_NEBIUS_MODELS",
    "FALLBACK_NEBIUS_MODELS",
    "InferenceResult",
    "NebiusClient",
    "get_nebius",
    "normalize_nebius_model",
]


def __getattr__(name: str):
    if name in ("NebiusClient", "InferenceResult", "get_nebius"):
        from supercompress.stack.nebius.client import InferenceResult, NebiusClient, get_nebius

        return {"NebiusClient": NebiusClient, "InferenceResult": InferenceResult, "get_nebius": get_nebius}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
