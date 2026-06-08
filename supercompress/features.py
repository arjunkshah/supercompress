"""Per-token metadata features for eviction policy decisions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional, Tuple

import numpy as np
import torch


class SemanticType(IntEnum):
    CODE = 0
    COMMENT = 1
    CHAT = 2
    BOILERPLATE = 3


SEMANTIC_NAMES = ["code", "comment", "chat", "boilerplate"]


@dataclass
class TokenRecord:
    """Single token with metadata used by the eviction network."""

    text: str
    position: int
    semantic_type: SemanticType
    is_oracle_important: bool
    attention_mass: float
    layer_attention_mean: float
    question_entity_match: float = 0.0
    h2o_score: float = 0.0
    snapkv_score: float = 0.0


def classify_token_semantic(text: str, line_context: str) -> SemanticType:
    """Heuristic semantic classifier — no external model required."""
    t = text.strip()
    if t.startswith("#") or t.startswith("//") or "/*" in line_context:
        return SemanticType.COMMENT
    if t.startswith("User:") or t.startswith("Assistant:") or t.startswith(">"):
        return SemanticType.CHAT
    boilerplate_patterns = (
        r"^import\s",
        r"^from\s+\w+\s+import",
        r"^# -\*- coding",
        r"^LICENSE",
        r"^Copyright",
        r"^\s*$",
        r"^---$",
        r"^```",
    )
    for pat in boilerplate_patterns:
        if re.match(pat, line_context.strip()):
            return SemanticType.BOILERPLATE
    return SemanticType.CODE


def synthesize_attention_mass(
    semantic: SemanticType,
    is_important: bool,
    recency_norm: float,
    rng: np.random.Generator,
) -> Tuple[float, float]:
    """
    Simulate attention statistics when a full LLM is unavailable.

    Important code tokens get higher mass; boilerplate gets damped.
    """
    base = {
        SemanticType.CODE: 0.55,
        SemanticType.COMMENT: 0.25,
        SemanticType.CHAT: 0.35,
        SemanticType.BOILERPLATE: 0.08,
    }[semantic]
    if is_important:
        base += 0.35
    base += 0.15 * recency_norm
    noise = rng.normal(0, 0.06)
    mass = float(np.clip(base + noise, 0.01, 1.0))
    layer_mean = float(np.clip(mass * rng.uniform(0.85, 1.15), 0.01, 1.0))
    return mass, layer_mean


FEATURE_DIM = 9


def build_feature_tensor(records: List[TokenRecord], seq_len: int) -> torch.Tensor:
    """
    Build per-token feature matrix for the policy network.

    Features (dim=9):
      - attention_mass
      - layer_attention_mean
      - recency (1 - age/len)
      - question_entity_match (inference-time signal from user query)
      - semantic one-hot (4)
    """
    n = len(records)
    feats = np.zeros((n, FEATURE_DIM), dtype=np.float32)
    for i, rec in enumerate(records):
        age = seq_len - 1 - rec.position
        recency = 1.0 - age / max(seq_len, 1)
        feats[i, 0] = rec.attention_mass
        feats[i, 1] = rec.layer_attention_mean
        feats[i, 2] = recency
        feats[i, 3] = rec.question_entity_match
        feats[i, 4 + int(rec.semantic_type)] = 1.0
    return torch.from_numpy(feats)


def tokenize_context_lines(lines: List[str]) -> List[str]:
    """Simple whitespace + punctuation split for demo tokens."""
    tokens: List[str] = []
    for line in lines:
        parts = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|[^\s]", line)
        if not parts:
            tokens.append(" ")
        else:
            tokens.extend(parts)
    return tokens
