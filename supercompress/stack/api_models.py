"""HTTP API request/response models."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CompressBlocksRequest(BaseModel):
    """Primary API — merge blocks then compress (agent loop integration)."""

    context_blocks: List[str] = Field(..., min_length=1, description="Tavily, Composio, etc. markdown blocks")
    query: str = Field(..., description="Current user task / question for this turn")
    budget_ratio: float = Field(default=0.35, ge=0.05, le=1.0, description="Fraction of tokens to keep")


class CompressTextRequest(BaseModel):
    """Single blob of context (split on --- for blocks if present)."""

    context: str
    query: str = "What matters in this context?"
    budget_ratio: float = Field(default=0.35, ge=0.05, le=1.0)


class CompressStats(BaseModel):
    original_tokens: int
    kept_tokens: int
    kv_savings_pct: float
    policy_name: str
    budget_ratio: float
    fifo_kept_tokens: Optional[int] = None


class CompressResponse(BaseModel):
    compressed_text: str
    stats: CompressStats


class CompareResponse(BaseModel):
    query: str
    fifo: CompressStats
    supercompress: CompressStats


class AgentTurnRequest(BaseModel):
    """
    Primary product — every call runs Tavily + Composio + SuperCompress + Nebius.

    Pass `context_blocks` for your app state (tasks, reminders, chat history).
    Connect Composio in the dashboard for Gmail/GitHub/etc.
    """

    query: str = Field(..., description="User message or task for this turn")
    context_blocks: List[str] = Field(
        default_factory=list,
        description="Your app data as markdown blocks — tasks, reminders, session state",
    )
    budget_ratio: float = Field(default=0.35, ge=0.05, le=1.0)


class AgentPhase(BaseModel):
    phase: str
    detail: str
    memory_stats: Optional[dict] = None


class AgentTurnResponse(BaseModel):
    answer: str
    query: str
    memory: CompressStats
    phases: List[AgentPhase]
    actions: List[dict] = Field(default_factory=list)
    sources: dict = Field(default_factory=dict)
    model: str = ""
    stack: dict = Field(
        default_factory=lambda: {
            "tavily": True,
            "composio": True,
            "supercompress": True,
            "nebius": True,
        },
        description="Sponsors invoked on every request",
    )
