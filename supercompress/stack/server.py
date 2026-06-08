"""API + static site + OpenClaw webhook."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from supercompress import compare_policies, compress_for_turn
from supercompress.stack._paths import ROOT
from supercompress.stack.agent.loop import StackAgent
from supercompress.stack.agent.prompts import OPENCLAW_BRIDGE_SYSTEM
from supercompress.stack.config import get_settings
from supercompress.stack.turn4_demo import QUERY, TURN_BLOCKS

app = FastAPI(title="SuperCompress", version="0.3.0")
WEB_DIR = ROOT / "web"


class OpenClawMessage(BaseModel):
    message: str
    session_id: str = "default"


class CompressRequest(BaseModel):
    context: str
    query: str = "What matters in this context?"
    budget_ratio: float = Field(default=0.35, ge=0.05, le=1.0)


@app.get("/api/health")
def health() -> Dict[str, Any]:
    s = get_settings()
    return {
        "ok": True,
        "demo_mode": s.demo_mode,
        "live": s.has_live_stack(),
        "stack": ["tavily", "composio", "supercompress", "nebius", "openclaw"],
    }


@app.get("/health")
def health_legacy() -> Dict[str, Any]:
    return health()


@app.get("/api/doctor")
@app.get("/doctor")
def doctor() -> Dict[str, Any]:
    from supercompress.stack.doctor import run_doctor_checks

    checks = run_doctor_checks()
    return {
        "ok": all(c.ok for c in checks),
        "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in checks],
    }


@app.get("/api/turns")
def api_turns() -> Dict[str, Any]:
    turns: List[Dict[str, Any]] = []
    for i, blocks in enumerate(TURN_BLOCKS, start=1):
        merged = "\n\n---\n\n".join(blocks)
        _, sc = compress_for_turn(blocks, QUERY)
        cmp = compare_policies(merged, QUERY)
        turns.append(
            {
                "turn": i,
                "blocks": len(blocks),
                "words": len(merged.split()),
                "fifo_tokens": cmp["FIFO"].kept_tokens,
                "sc_tokens": sc.kept_tokens,
                "kv_savings_pct": round(sc.kv_savings_pct, 1),
                "original_tokens": sc.original_tokens,
            }
        )
    return {"query": QUERY, "turns": turns}


@app.post("/api/compress")
def api_compress(req: CompressRequest) -> Dict[str, Any]:
    parts = [p.strip() for p in req.context.split("---") if p.strip()]
    blocks = parts if len(parts) > 1 else [req.context]
    merged = "\n\n---\n\n".join(blocks)
    compressed, result = compress_for_turn(blocks, req.query, budget_ratio=req.budget_ratio)
    cmp = compare_policies(merged, req.query, budget_ratio=req.budget_ratio)
    return {
        "original_tokens": result.original_tokens,
        "kept_tokens": result.kept_tokens,
        "fifo_tokens": cmp["FIFO"].kept_tokens,
        "kv_savings_pct": round(result.kv_savings_pct, 1),
        "policy": result.policy_name,
        "compressed_preview": compressed[:2000],
    }


@app.post("/openclaw/chat")
def openclaw_chat(payload: OpenClawMessage) -> Dict[str, str]:
    agent = StackAgent()
    tavily = agent.tavily.search_and_answer(payload.message)
    github = agent.composio.gather_github()
    result = agent.run_with_tools(
        OPENCLAW_BRIDGE_SYSTEM,
        payload.message,
        [tavily.to_context_block(), github.to_context_block()],
        workflow="openclaw_chat",
    )
    return {
        "reply": result.summary or "",
        "kv_savings_pct": f"{result.memory_savings_pct:.1f}",
    }


@app.get("/openclaw/manifest")
def openclaw_manifest() -> Dict[str, Any]:
    return {
        "name": "supercompress",
        "site": "/",
        "app": "/app.html",
        "endpoints": {"chat": "/openclaw/chat", "compress": "/api/compress", "health": "/api/health"},
        "stack": ["openclaw", "tavily", "composio", "supercompress", "nebius"],
    }


if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="site")
