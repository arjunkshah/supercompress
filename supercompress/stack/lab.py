"""Turn Lab — multi-turn session demo showing context explosion vs SuperCompress."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List

from supercompress import compress_for_turn
from supercompress.stack.agent.loop import StackAgent
from supercompress.stack.agent.prompts import AGENT_TURN_SYSTEM
from supercompress.stack.api_models import (
    AgentPhase,
    CompressStats,
    LabTurnHistoryEntry,
    LabTurnRequest,
    LabTurnResponse,
)
from supercompress.stack.config import get_settings

DEFAULT_QUERIES = [
    "What should I ship today?",
    "Any blockers on my open PRs?",
    "Summarize my unread email",
    "What's the full picture across all my apps?",
]


@dataclass
class LabSession:
    blocks: List[str] = field(default_factory=list)
    turn: int = 0
    history: List[LabTurnHistoryEntry] = field(default_factory=list)


_sessions: Dict[str, LabSession] = {}


def reset_lab_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


def run_lab_turn(req: LabTurnRequest) -> LabTurnResponse:
    session_id = req.session_id or uuid.uuid4().hex[:16]
    session = _sessions.setdefault(session_id, LabSession())

    s = get_settings()
    agent = StackAgent(s)
    budget = req.budget_ratio

    turn_num = session.turn + 1
    query = req.query or DEFAULT_QUERIES[min(turn_num - 1, len(DEFAULT_QUERIES) - 1)]

    phases: List[AgentPhase] = []

    phases.append(AgentPhase(phase="tavily", detail=f"Web research: {query[:80]}"))
    bundle = agent.tavily.search_and_answer(query)
    session.blocks.append(bundle.to_context_block())
    phases.append(
        AgentPhase(
            phase="tavily",
            detail=f"{len(bundle.hits)} sources" + (" · synthesis ready" if bundle.answer else ""),
        )
    )

    phases.append(AgentPhase(phase="composio", detail="Gathering connected apps (GitHub · Gmail · Linear)"))
    composio_data = agent.composio.gather_all()
    session.blocks.extend(composio_data.all_context_blocks())
    gh = len(composio_data.github.prs_needing_review) + len(composio_data.github.open_issues)
    gm = len(composio_data.gmail.unanswered) + len(composio_data.gmail.important)
    lin = len(composio_data.linear.blocked) + len(composio_data.linear.in_progress)
    phases.append(AgentPhase(phase="composio", detail=f"{gh} GitHub · {gm} Gmail · {lin} Linear items"))

    session.turn = turn_num
    phases.append(
        AgentPhase(phase="gather", detail=f"{len(session.blocks)} context blocks accumulated (turn {turn_num})")
    )

    compressed, mem = compress_for_turn(session.blocks, query, budget_ratio=budget)
    memory_stats = {
        "policy": mem.policy_name,
        "original_tokens": mem.original_tokens,
        "kept_tokens": mem.kept_tokens,
        "kv_savings_pct": mem.kv_savings_pct,
    }
    phases.append(
        AgentPhase(
            phase="supercompress",
            detail=f"{mem.original_tokens}→{mem.kept_tokens} tokens · {mem.kv_savings_pct:.1f}% KV saved",
            memory_stats=memory_stats,
        )
    )

    messages = [
        {"role": "system", "content": AGENT_TURN_SYSTEM},
        {
            "role": "user",
            "content": f"## Context (SuperCompress @ {budget:.0%})\n\n{compressed}\n\n## Task\n{query}",
        },
    ]
    nebius_result = agent.nebius.chat(messages, tools=agent.composio.get_openai_tools())
    answer = nebius_result.content or ""
    phases.append(
        AgentPhase(
            phase="nebius",
            detail=f"Inference via {getattr(agent.nebius, 'model', 'nebius')}",
        )
    )

    memory = CompressStats(
        original_tokens=mem.original_tokens,
        kept_tokens=mem.kept_tokens,
        kv_savings_pct=round(mem.kv_savings_pct, 1),
        policy_name=mem.policy_name,
        budget_ratio=budget,
    )

    entry = LabTurnHistoryEntry(
        turn=turn_num,
        original_tokens=mem.original_tokens,
        compressed_tokens=mem.kept_tokens,
        kv_savings_pct=round(mem.kv_savings_pct, 1),
        blocks=len(session.blocks),
    )
    session.history.append(entry)

    return LabTurnResponse(
        session_id=session_id,
        turn=turn_num,
        query=query,
        answer=answer,
        memory=memory,
        phases=phases,
        turn_history=list(session.history),
    )
