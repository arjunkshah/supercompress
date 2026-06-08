"""Public HTTP API — any language can POST JSON, get compressed context back."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Request

from supercompress import compare_policies, compress_for_turn
from supercompress.stack.auth import log_request_usage, require_api_key
from supercompress.stack.agent.loop import StackAgent
from supercompress.stack.api_models import (
    AgentPhase,
    AgentTurnRequest,
    AgentTurnResponse,
    CompareResponse,
    CompressBlocksRequest,
    CompressResponse,
    CompressStats,
    CompressTextRequest,
)
from supercompress.stack.config import get_settings, settings_for_user
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
        "stack": {
            "tavily": s.has_tavily() or s.demo_mode,
            "composio": s.has_composio() or s.demo_mode,
            "nebius": s.has_nebius() or s.demo_mode,
            "live": s.has_live_stack(),
        },
        "endpoints": {
            "agent_turn": "POST /v1/agent/turn",
            "compress_blocks": "POST /v1/compress/blocks",
            "docs": "/docs",
        },
    }


def _agent_result_to_response(result, query: str) -> AgentTurnResponse:
    mem_stats = None
    for t in reversed(result.turns):
        if t.phase == "memory" and t.memory_stats:
            mem_stats = t.memory_stats
            break
    memory = CompressStats(
        original_tokens=mem_stats.get("original_tokens", 0) if mem_stats else 0,
        kept_tokens=mem_stats.get("kept_tokens", 0) if mem_stats else 0,
        kv_savings_pct=mem_stats.get("kv_savings_pct", result.memory_savings_pct) if mem_stats else result.memory_savings_pct,
        policy_name=mem_stats.get("policy", "SuperCompress") if mem_stats else "SuperCompress",
        budget_ratio=get_settings().harbor_memory_budget,
    )
    phases = [
        AgentPhase(phase=t.phase, detail=t.detail, memory_stats=t.memory_stats)
        for t in result.turns
    ]
    model = ""
    for t in result.turns:
        if t.phase == "nebius" and "via" in t.detail:
            model = t.detail.split("via", 1)[-1].strip()
            break
    return AgentTurnResponse(
        answer=result.summary or "",
        query=query,
        memory=memory,
        phases=phases,
        actions=result.actions_taken,
        sources=result.prompt_meta,
        model=model,
        stack={
            "tavily": True,
            "composio": True,
            "supercompress": True,
            "nebius": True,
        },
    )


@router.post("/agent/turn", response_model=AgentTurnResponse)
def agent_turn(
    req: AgentTurnRequest,
    request: Request,
    _key: Dict[str, Any] = Depends(require_api_key),
) -> AgentTurnResponse:
    """
    **Primary API** — every call runs all sponsors:

    Tavily (web) → Composio (your connected apps) → your context_blocks → SuperCompress → Nebius.

    Connect Gmail/GitHub in the dashboard. Pass tasks/reminders as context_blocks.
    Use `answer` in your UI instead of calling OpenAI directly.
    """
    from fastapi import HTTPException

    s = get_settings()
    if not s.demo_mode and not s.has_live_stack():
        raise HTTPException(
            status_code=503,
            detail="Agent stack unavailable — server missing Tavily/Composio/Nebius keys.",
        )
    user_settings = settings_for_user(_key["user_id"])
    agent = StackAgent(user_settings)
    result = agent.agent_turn(
        req.query,
        app_blocks=req.context_blocks,
        budget_ratio=req.budget_ratio,
    )
    response = _agent_result_to_response(result, req.query)
    log_request_usage(request, "/v1/agent/turn", response.memory.model_dump())
    return response


@router.post("/compress/blocks", response_model=CompressResponse)
def compress_blocks(
    req: CompressBlocksRequest,
    request: Request,
    _key: Dict[str, Any] = Depends(require_api_key),
) -> CompressResponse:
    """Advanced — compress context you already gathered. Most apps should use POST /v1/agent/turn."""
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
