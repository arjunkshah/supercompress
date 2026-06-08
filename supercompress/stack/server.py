"""Minimal API — health, doctor, OpenClaw webhook."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI
from pydantic import BaseModel

from supercompress.stack.agent.loop import StackAgent
from supercompress.stack.agent.prompts import OPENCLAW_BRIDGE_SYSTEM
from supercompress.stack.config import get_settings

app = FastAPI(title="SuperCompress", version="0.2.0")


class OpenClawMessage(BaseModel):
    message: str
    session_id: str = "default"


@app.get("/health")
def health() -> Dict[str, Any]:
    s = get_settings()
    return {
        "ok": True,
        "demo_mode": s.demo_mode,
        "stack": ["tavily", "composio", "supercompress", "nebius", "openclaw"],
    }


@app.get("/doctor")
def doctor() -> Dict[str, Any]:
    from supercompress.stack.doctor import run_doctor_checks

    checks = run_doctor_checks()
    return {
        "ok": all(c.ok for c in checks),
        "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in checks],
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
        "endpoints": {"chat": "/openclaw/chat", "health": "/health"},
        "stack": ["openclaw", "tavily", "composio", "supercompress", "nebius"],
    }
