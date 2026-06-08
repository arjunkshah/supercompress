"""CORS — browsers reject allow_credentials=True with allow_origins=['*']."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

DEFAULT_ORIGINS = [
    "https://buildersshipbycursor.vercel.app",
    "https://arjunkshah.github.io",
    "http://127.0.0.1:8787",
    "http://localhost:8787",
    "http://localhost:3000",
]


def _allowed_origins() -> list[str]:
    extra = os.environ.get("SUPERCOMPRESS_CORS_ORIGINS", "")
    origins = list(DEFAULT_ORIGINS)
    for part in extra.split(","):
        part = part.strip()
        if part and part not in origins:
            origins.append(part)
    return origins


def setup_cors(app: FastAPI) -> None:
    # API auth uses X-API-Key / Authorization headers — not cookies — so credentials=False
    # allows wildcard origins for third-party API clients.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins() if os.environ.get("SUPERCOMPRESS_CORS_STRICT") else ["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
