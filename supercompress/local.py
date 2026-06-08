"""Build token records from real text on a laptop — no GPU, no HF download."""

from __future__ import annotations

import re
from typing import List, Tuple

import numpy as np

from supercompress.features import (
    SemanticType,
    TokenRecord,
    classify_token_semantic,
    synthesize_attention_mass,
    tokenize_context_lines,
)
from supercompress.oracle import extract_question_entities


def _deterministic_attention(
    semantic: SemanticType,
    entity_match: float,
    recency_norm: float,
    line_ctx: str,
    tok: str,
) -> Tuple[float, float, float, float]:
    """Cheap attention proxy from metadata only (stable across runs)."""
    base = {
        SemanticType.CODE: 0.55,
        SemanticType.COMMENT: 0.25,
        SemanticType.CHAT: 0.35,
        SemanticType.BOILERPLATE: 0.08,
    }[semantic]

    struct_boost = 0.0
    if re.match(r"^(def|class|async)\b", line_ctx.strip()) and tok in ("def", "class", "async"):
        struct_boost = 0.35
    elif "def " in line_ctx:
        parts = line_ctx.split()
        if "def" in parts:
            idx = parts.index("def")
            if idx + 1 < len(parts) and tok == parts[idx + 1].split("(")[0]:
                struct_boost = 0.3

    important = entity_match > 0 or struct_boost > 0
    mass, layer_m = synthesize_attention_mass(
        semantic,
        important,
        recency_norm,
        np.random.default_rng(0),
    )
    mass = float(np.clip(mass + 0.25 * entity_match + struct_boost * 0.5, 0.01, 1.0))
    layer_m = float(np.clip(layer_m + 0.15 * entity_match, 0.01, 1.0))
    recency = recency_norm
    h2o = float(np.clip(layer_m * (0.7 + 0.3 * (1 - recency)), 0.01, 1.0))
    snap = float(np.clip(mass * (0.3 + 0.7 * recency), 0.01, 1.0))
    return mass, layer_m, h2o, snap


def build_inference_records(
    lines: List[str],
    question: str,
) -> Tuple[List[TokenRecord], List[int]]:
    """
    Token records + parallel line index per token for text reconstruction.

    Uses question entities and code structure — not training oracle labels.
    """
    tokens = tokenize_context_lines(lines)
    entities = extract_question_entities(question)
    seq_len = len(tokens)
    records: List[TokenRecord] = []
    line_for_token: List[int] = []

    line_idx = 0
    tok_in_line = 0
    for pos, tok in enumerate(tokens):
        while line_idx < len(lines):
            line = lines[line_idx]
            parts = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|[^\s]", line) or [" "]
            if tok_in_line < len(parts):
                break
            line_idx += 1
            tok_in_line = 0
        line_ctx = lines[line_idx] if line_idx < len(lines) else ""
        sem = classify_token_semantic(tok, line_ctx)
        age_norm = pos / max(seq_len - 1, 1)
        entity_match = 1.0 if tok in entities else 0.0
        mass, layer_m, h2o, snap = _deterministic_attention(
            sem, entity_match, age_norm, line_ctx, tok
        )
        records.append(
            TokenRecord(
                text=tok,
                position=pos,
                semantic_type=sem,
                is_oracle_important=False,
                attention_mass=mass,
                layer_attention_mean=layer_m,
                question_entity_match=entity_match,
                h2o_score=h2o,
                snapkv_score=snap,
            )
        )
        line_for_token.append(line_idx)
        tok_in_line += 1

    return records, line_for_token


def read_context(path: str | None, stdin_fallback: bool = True) -> str:
    """Load context from file path, literal @file, or stdin."""
    if path is None or path == "-":
        if not stdin_fallback:
            raise ValueError("No context path provided")
        import sys

        return sys.stdin.read()
    if path.startswith("@"):
        path = path[1:]
    from pathlib import Path

    return Path(path).read_text(encoding="utf-8", errors="replace")
