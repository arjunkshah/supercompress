"""Nebius Token Factory model IDs — defaults and deprecation migration."""

from __future__ import annotations

from typing import List, Optional

# Current defaults (see https://docs.tokenfactory.nebius.com/switch)
DEFAULT_NEBIUS_MODEL = "moonshotai/Kimi-K2.5"

# Deprecated Kimi K2 builds — auto-migrate on setup/doctor
DEPRECATED_NEBIUS_MODELS = {
    "moonshotai/Kimi-K2-Instruct-0905": DEFAULT_NEBIUS_MODEL,
    "moonshotai/kimi_k2_instruct": DEFAULT_NEBIUS_MODEL,
    "moonshotai/kimi_k2_thinking": DEFAULT_NEBIUS_MODEL,
    "moonshotai/Kimi-K2-Instruct": DEFAULT_NEBIUS_MODEL,
}

FALLBACK_NEBIUS_MODELS: List[str] = [
    DEFAULT_NEBIUS_MODEL,
    "moonshotai/Kimi-K2.5-fast",
    "moonshotai/Kimi-K2.6",
    "meta-llama/Llama-3.3-70B-Instruct",
]


def normalize_nebius_model(model: Optional[str]) -> str:
    """Return a supported model ID, migrating deprecated slugs."""
    raw = (model or "").strip()
    if not raw:
        return DEFAULT_NEBIUS_MODEL
    lowered = raw.lower()
    for old, new in DEPRECATED_NEBIUS_MODELS.items():
        if raw == old or lowered == old.lower():
            return new
    return raw


def is_deprecated_nebius_model(model: Optional[str]) -> bool:
    raw = (model or "").strip()
    if not raw:
        return False
    lowered = raw.lower()
    return any(raw == old or lowered == old.lower() for old in DEPRECATED_NEBIUS_MODELS)
