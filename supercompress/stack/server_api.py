"""Production API only — no static files. Deploy to Render/Railway/Fly."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from supercompress.stack.api import router as api_router
from supercompress.stack.dashboard import router as dashboard_router
from supercompress.stack.db import init_db

init_db()

app = FastAPI(
    title="SuperCompress API",
    version="1.0.0",
    description="Official public API — compress agent context before every LLM call.",
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
app.include_router(api_router, prefix="/api")
app.include_router(dashboard_router, prefix="/v1")
app.include_router(dashboard_router, prefix="/api")


@app.get("/")
def root():
    return {
        "service": "SuperCompress API",
        "docs": "/docs",
        "agent_turn": "POST /v1/agent/turn",
        "website": "https://buildersshipbycursor.vercel.app",
    }
