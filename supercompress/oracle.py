"""Heuristic oracle that labels which tokens must be kept for downstream QA."""

from __future__ import annotations

import re
from typing import List, Set

import numpy as np

from supercompress.features import SemanticType, TokenRecord, classify_token_semantic


def extract_question_entities(question: str) -> Set[str]:
    """Identifiers referenced in the user question (simulated coding QA)."""
    ids = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", question))
    stop = {
        "what", "how", "does", "the", "is", "are", "function", "return",
        "class", "def", "import", "from", "this", "that", "where", "when",
    }
    return {x for x in ids if x.lower() not in stop and len(x) > 2}


def mark_oracle_important(
    tokens: List[str],
    lines: List[str],
    question: str,
) -> List[bool]:
    """
    Oracle keep-set: signatures, defs, and entities mentioned in the question.
    """
    entities = extract_question_entities(question)
    important = [False] * len(tokens)

    line_idx = 0
    char_in_line = 0
    for i, tok in enumerate(tokens):
        while line_idx < len(lines) and char_in_line >= len(lines[line_idx]):
            line_idx += 1
            char_in_line = 0
        line = lines[line_idx] if line_idx < len(lines) else ""

        if re.match(r"^(def|class|async\s+def)\b", line) and tok in ("def", "class", "async") or (
            tok in entities
        ):
            important[i] = True
        if tok in entities:
            important[i] = True
        if re.match(rf"\b{re.escape(tok)}\s*=", line) and tok in entities:
            important[i] = True
        if "def " in line and tok in line.split():
            # function name token after def
            parts = line.split()
            if "def" in parts:
                idx = parts.index("def")
                if idx + 1 < len(parts) and tok == parts[idx + 1].split("(")[0]:
                    important[i] = True

        char_in_line += len(tok) + 1
        if char_in_line > len(line):
            line_idx += 1
            char_in_line = 0

    return important


def build_token_records(
    lines: List[str],
    question: str,
    rng,
) -> List[TokenRecord]:
    """Construct full token records with synthetic attention and oracle labels."""
    from supercompress.features import tokenize_context_lines, synthesize_attention_mass

    tokens = tokenize_context_lines(lines)
    oracle_flags = mark_oracle_important(tokens, lines, question)
    entities = extract_question_entities(question)
    seq_len = len(tokens)
    records: List[TokenRecord] = []

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
        mass, layer_m = synthesize_attention_mass(
            sem, oracle_flags[pos], age_norm, rng
        )
        entity_match = 1.0 if tok in entities else 0.0
        recency = pos / max(seq_len - 1, 1)
        h2o = float(np.clip(layer_m * (0.7 + 0.3 * (1 - recency)), 0.01, 1.0))
        snap = float(np.clip(mass * (0.3 + 0.7 * recency), 0.01, 1.0))
        records.append(
            TokenRecord(
                text=tok,
                position=pos,
                semantic_type=sem,
                is_oracle_important=oracle_flags[pos],
                attention_mass=mass,
                layer_attention_mean=layer_m,
                question_entity_match=entity_match,
                h2o_score=h2o,
                snapkv_score=snap,
            )
        )
        tok_in_line += 1

    return records
