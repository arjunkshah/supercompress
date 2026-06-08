"""HTTP client — call a self-hosted or team SuperCompress API from any Python project."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import httpx


@dataclass
class RemoteCompressStats:
    original_tokens: int
    kept_tokens: int
    kv_savings_pct: float
    policy_name: str
    budget_ratio: float
    fifo_kept_tokens: Optional[int] = None


@dataclass
class RemoteCompressResult:
    compressed_text: str
    stats: RemoteCompressStats


class SuperCompressClient:
    """
    Talk to a running SuperCompress API server.

    Start server: ./bin/supercompress serve
    Default base: http://127.0.0.1:8787
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8787", *, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SuperCompressClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def health(self) -> dict:
        r = self._client.get("/v1/health")
        r.raise_for_status()
        return r.json()

    def compress_blocks(
        self,
        context_blocks: List[str],
        query: str,
        *,
        budget_ratio: float = 0.35,
    ) -> RemoteCompressResult:
        r = self._client.post(
            "/v1/compress/blocks",
            json={
                "context_blocks": context_blocks,
                "query": query,
                "budget_ratio": budget_ratio,
            },
        )
        r.raise_for_status()
        data = r.json()
        s = data["stats"]
        return RemoteCompressResult(
            compressed_text=data["compressed_text"],
            stats=RemoteCompressStats(
                original_tokens=s["original_tokens"],
                kept_tokens=s["kept_tokens"],
                kv_savings_pct=s["kv_savings_pct"],
                policy_name=s["policy_name"],
                budget_ratio=s["budget_ratio"],
                fifo_kept_tokens=s.get("fifo_kept_tokens"),
            ),
        )

    def compress(self, context: str, query: str, *, budget_ratio: float = 0.35) -> RemoteCompressResult:
        r = self._client.post(
            "/v1/compress",
            json={"context": context, "query": query, "budget_ratio": budget_ratio},
        )
        r.raise_for_status()
        data = r.json()
        s = data["stats"]
        return RemoteCompressResult(
            compressed_text=data["compressed_text"],
            stats=RemoteCompressStats(
                original_tokens=s["original_tokens"],
                kept_tokens=s["kept_tokens"],
                kv_savings_pct=s["kv_savings_pct"],
                policy_name=s["policy_name"],
                budget_ratio=s["budget_ratio"],
                fifo_kept_tokens=s.get("fifo_kept_tokens"),
            ),
        )
