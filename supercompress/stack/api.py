"""Public HTTP API — any language can POST JSON, get compressed context back."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Request

from supercompress import compare_policies, compress_for_turn
from supercompress.stack.auth import log_request_usage, require_api_key
from supercompress.stack.api_models import (
    CompareResponse,
    CompressBlocksRequest,
    CompressResponse,
    CompressStats,
    CompressTextRequest,
)
from supercompress.stack.config import get_settings
from supercompress.stack.turn4_demo import QUERY, TURN_BLOCKS

router = APIRouter(tags=["SuperCompress API"])


def _stats_from_result(result, *, fifo_tokens: int | None = None) -> CompressStats:
    return CompressStats(
        original_tokens=result.original_tokens,
        kept_tokens=result.kept_tokens,
        kv_savings_pct=round(result.kv_savings_pct, 1),
        policy_name=result.policy_name,
        budget_ratio=result.budget_ratio,
        fifo_kept_tokens=fifo_tokens,
    )


@router.get("/health")
def api_health() -> Dict[str, Any]:
    s = get_settings()
    return {
        "ok": True,
        "service": "supercompress",
        "version": "v1",
        "demo_mode": s.demo_mode,
        "endpoints": {
            "compress": "POST /v1/compress",
            "compress_blocks": "POST /v1/compress/blocks",
            "compare": "POST /v1/compare",
            "docs": "/docs",
        },
    }


@router.post("/compress/blocks", response_model=CompressResponse)
def compress_blocks(
    req: CompressBlocksRequest,
    request: Request,
    _key: Dict[str, Any] = Depends(require_api_key),
) -> CompressResponse:
    """Recommended — pass Tavily + Composio blocks separately."""
    blocks = [b for b in req.context_blocks if b.strip()]
    compressed, result = compress_for_turn(blocks, req.query, budget_ratio=req.budget_ratio)
    merged = "\n\n---\n\n".join(blocks)
    fifo = compare_policies(merged, req.query, budget_ratio=req.budget_ratio)["FIFO"]
    stats = _stats_from_result(result, fifo_tokens=fifo.kept_tokens)
    log_request_usage(request, "/v1/compress/blocks", stats.model_dump())
    return CompressResponse(compressed_text=compressed, stats=stats)


@router.post("/compress", response_model=CompressResponse)
def compress_text(
    req: CompressTextRequest,
    request: Request,
    _key: Dict[str, Any] = Depends(require_api_key),
) -> CompressResponse:
    """Single string — splits on --- into blocks when present."""
    parts = [p.strip() for p in req.context.split("---") if p.strip()]
    blocks = parts if len(parts) > 1 else [req.context]
    inner = CompressBlocksRequest(
        context_blocks=blocks,
        query=req.query,
        budget_ratio=req.budget_ratio,
    )
    return compress_blocks(inner, request, _key)


@router.post("/compare", response_model=CompareResponse)
def compare(
    req: CompressBlocksRequest,
    request: Request,
    _key: Dict[str, Any] = Depends(require_api_key),
) -> CompareResponse:
    blocks = [b for b in req.context_blocks if b.strip()]
    merged = "\n\n---\n\n".join(blocks)
    cmp = compare_policies(merged, req.query, budget_ratio=req.budget_ratio)
    sc_stats = _stats_from_result(cmp["SuperCompress"])
    log_request_usage(request, "/v1/compare", sc_stats.model_dump())
    return CompareResponse(
        query=req.query,
        fifo=_stats_from_result(cmp["FIFO"]),
        supercompress=sc_stats,
    )


@router.get("/turns/demo")
def turns_demo() -> Dict[str, Any]:
    turns: List[Dict[str, Any]] = []
    for i, blocks in enumerate(TURN_BLOCKS, start=1):
        merged = "\n\n---\n\n".join(blocks)
        _, sc = compress_for_turn(blocks, QUERY)
        cmp = compare_policies(merged, QUERY)
        turns.append(
            {
                "turn": i,
                "blocks": len(blocks),
                "fifo_tokens": cmp["FIFO"].kept_tokens,
                "sc_tokens": sc.kept_tokens,
                "kv_savings_pct": round(sc.kv_savings_pct, 1),
                "original_tokens": sc.original_tokens,
            }
        )
    return {"query": QUERY, "turns": turns}
