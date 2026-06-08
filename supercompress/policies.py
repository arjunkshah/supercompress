"""KV eviction policies: baselines and learned."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

import numpy as np
import torch

from supercompress.features import TokenRecord, build_feature_tensor
from supercompress.model import EvictionPolicyNetwork


class EvictionPolicy(ABC):
    """Select up to `budget` token indices to retain in KV cache."""

    name: str = "base"

    @abstractmethod
    def select(self, records: List[TokenRecord], budget: int) -> List[int]:
        ...


class FIFO(EvictionPolicy):
    """Drop oldest first — keep most recent `budget` tokens."""

    name = "FIFO"

    def select(self, records: List[TokenRecord], budget: int) -> List[int]:
        n = len(records)
        b = min(budget, n)
        return list(range(n - b, n))


class LRU(EvictionPolicy):
    """Keep tokens with highest recency score (same as recent-biased here)."""

    name = "LRU"

    def select(self, records: List[TokenRecord], budget: int) -> List[int]:
        n = len(records)
        scores = [(r.position, i) for i, r in enumerate(records)]
        scores.sort(reverse=True)
        kept = sorted([i for _, i in scores[: min(budget, n)]])
        return [records[i].position for i in kept]


class SlidingWindow(EvictionPolicy):
    """Fixed window on recent half + always keep first 5% (attention sinks)."""

    name = "Sliding Window"

    def select(self, records: List[TokenRecord], budget: int) -> List[int]:
        n = len(records)
        b = min(budget, n)
        sink = max(1, n // 20)
        recent = b - sink
        if recent < 0:
            recent = 0
        indices = list(range(sink)) + list(range(max(0, n - recent), n))
        return sorted(set(indices))[:b]


class RandomPolicy(EvictionPolicy):
    name = "Random"

    def __init__(self, seed: int = 0):
        self.rng = np.random.default_rng(seed)

    def select(self, records: List[TokenRecord], budget: int) -> List[int]:
        n = len(records)
        b = min(budget, n)
        chosen = self.rng.choice(n, size=b, replace=False)
        return sorted([records[i].position for i in chosen])


class OraclePolicy(EvictionPolicy):
    """Upper bound: keep all oracle-important then fill with recent."""

    name = "Oracle"

    def select(self, records: List[TokenRecord], budget: int) -> List[int]:
        n = len(records)
        b = min(budget, n)
        important = [r.position for r in records if r.is_oracle_important]
        remaining = b - len(important)
        if remaining <= 0:
            return sorted(important)[:b]
        recent = [r.position for r in records if r.position not in important]
        recent.sort(reverse=True)
        return sorted(set(important + recent[:remaining]))


class LearnedPolicy(EvictionPolicy):
    """Top-k tokens by EvictionPolicyNetwork keep score."""

    name = "Learned Policy"

    def __init__(self, model: EvictionPolicyNetwork, device: str = "cpu"):
        self.model = model
        self.device = device
        self.model.eval()

    def select(self, records: List[TokenRecord], budget: int) -> List[int]:
        n = len(records)
        b = min(budget, n)
        feats = build_feature_tensor(records, n).to(self.device)
        with torch.no_grad():
            scores = self.model.keep_scores(feats).cpu().numpy()
        top_idx = np.argsort(scores)[-b:]
        return sorted([records[i].position for i in top_idx])


class AttentionHeuristicPolicy(EvictionPolicy):
    """Non-learned baseline: keep highest attention mass."""

    name = "Attention Heuristic"

    def select(self, records: List[TokenRecord], budget: int) -> List[int]:
        n = len(records)
        b = min(budget, n)
        scores = np.array([r.attention_mass for r in records])
        top_idx = np.argsort(scores)[-b:]
        return sorted([records[i].position for i in top_idx])


class H2OPolicy(EvictionPolicy):
    """
    Heavy Hitter Oracle (H2O): retain attention sinks + recent window + top cumulative-attention tokens.

    Reference: Zhang et al., "H2O: Heavy-Hitter Oracle for Efficient Generative Inference of LLMs"
    """

    name = "H2O"

    def __init__(self, sink_tokens: int = 4, recent_ratio: float = 0.2):
        self.sink_tokens = sink_tokens
        self.recent_ratio = recent_ratio

    def select(self, records: List[TokenRecord], budget: int) -> List[int]:
        n = len(records)
        b = min(budget, n)
        sink = min(self.sink_tokens, max(1, b // 10))
        recent = max(1, int(b * self.recent_ratio))
        hh_slots = max(0, b - sink - recent)

        kept: set[int] = set(range(sink))
        kept.update(range(max(0, n - recent), n))

        scores = np.array([getattr(r, "h2o_score", r.layer_attention_mean) for r in records])
        candidates = [i for i in range(n) if i not in kept]
        for idx in sorted(candidates, key=lambda i: scores[i], reverse=True)[:hh_slots]:
            kept.add(idx)

        if len(kept) > b:
            # Trim lowest-scoring non-sink, non-recent
            ranked = sorted(kept, key=lambda i: scores[i])
            kept = set(ranked[-b:])
        return sorted(kept)


class SnapKVPolicy(EvictionPolicy):
    """
    SnapKV-style: score prefix tokens by attention from an observation window at sequence end.

    Reference: Li et al., "SnapKV: LLM Knows What You are Looking for Before Generation"
    """

    name = "SnapKV"

    def __init__(self, sink_tokens: int = 4):
        self.sink_tokens = sink_tokens

    def select(self, records: List[TokenRecord], budget: int) -> List[int]:
        n = len(records)
        b = min(budget, n)
        sink = min(self.sink_tokens, max(1, b // 10))
        kept: set[int] = set(range(sink))

        scores = np.array([getattr(r, "snapkv_score", r.attention_mass) for r in records])
        remaining = b - len(kept)
        candidates = [i for i in range(n) if i not in kept]
        for idx in sorted(candidates, key=lambda i: scores[i], reverse=True)[:remaining]:
            kept.add(idx)
        return sorted(kept)
