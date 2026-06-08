"""API server + marketing site."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from supercompress.stack._paths import ROOT
from supercompress.stack.agent.loop import StackAgent
from supercompress.stack.agent.prompts import OPENCLAW_BRIDGE_SYSTEM
from supercompress.stack.api import router as api_router
from supercompress.stack.config import get_settings
from supercompress.stack.dashboard import router as dashboard_router
from supercompress.stack.db import init_db

init_db()

app = FastAPI(
    title="SuperCompress API",
    version="1.0.0",
    description="Compress agent context before every LLM call. Use from any language via HTTP.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/v1")
app.include_router(api_router, prefix="/api")  # legacy alias
app.include_router(dashboard_router, prefix="/v1")
app.include_router(dashboard_router, prefix="/api")

WEB_DIR = ROOT / "web"


class OpenClawMessage(BaseModel):
    message: str
    session_id: str = "default"


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
        "api": "/v1",
        "docs": "/docs",
        "endpoints": {
            "compress": "POST /v1/compress/blocks",
            "health": "GET /v1/health",
            "openclaw": "POST /openclaw/chat",
        },
    }


# Static site last — API routes (/v1, /docs) take precedence
if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="site")
