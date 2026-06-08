"""ReAct agent loop — Tavily gather → Composio gather → SuperCompress → Nebius → Composio act."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from supercompress import compress_for_turn
from supercompress.stack.agent.prompts import INCIDENT_COMMANDER_SYSTEM, MORNING_BRIEF_SYSTEM
from supercompress.stack.composio import get_composio
from supercompress.stack.config import Settings, get_settings
from supercompress.stack.integrations import incident_instructions, morning_brief_instructions
from supercompress.stack.nebius import get_nebius
from supercompress.stack.tavily import get_tavily

logger = logging.getLogger(__name__)


@dataclass
class TurnLog:
    turn: int
    phase: str
    detail: str
    memory_stats: Optional[Dict[str, Any]] = None


@dataclass
class AgentRunResult:
    workflow: str
    summary: str
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)
    memory_savings_pct: float = 0.0
    turns: List[TurnLog] = field(default_factory=list)
    raw_messages: List[Dict[str, Any]] = field(default_factory=list)
    prompt_meta: Dict[str, Any] = field(default_factory=dict)


class StackAgent:
    """Orchestrates the full sponsor stack in a multi-turn tool-calling loop."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.tavily = get_tavily(self.settings)
        self.composio = get_composio(self.settings)
        self.nebius = get_nebius(self.settings)

    def _log(self, turns: List[TurnLog], turn: int, phase: str, detail: str, memory_stats=None):
        turns.append(TurnLog(turn=turn, phase=phase, detail=detail, memory_stats=memory_stats))
        logger.info("[%s] %s", phase, detail)

    def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        actions = []
        tool_messages = []
        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            result = self.composio.execute(name, args)
            actions.append({"tool": name, "arguments": args, "success": result.success, "error": result.error})
            tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.get("id", name),
                    "content": json.dumps(result.data if result.success else {"error": result.error}),
                }
            )
        return actions, tool_messages

    def run_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        context_blocks: List[str],
        *,
        workflow: str = "generic",
    ) -> AgentRunResult:
        turns: List[TurnLog] = []
        actions: List[Dict[str, Any]] = []

        merged_context = "\n\n".join(context_blocks)
        self._log(turns, 0, "gather", f"Raw context: {len(merged_context)} chars from {len(context_blocks)} blocks")

        compressed, mem = compress_for_turn(
            context_blocks,
            user_prompt,
            budget_ratio=self.settings.harbor_memory_budget,
        )
        self._log(
            turns,
            1,
            "memory",
            f"SuperCompress ({mem.policy_name}): {mem.original_tokens}→{mem.kept_tokens} tokens, "
            f"{mem.kv_savings_pct:.1f}% KV savings",
            memory_stats={
                "policy": mem.policy_name,
                "original_tokens": mem.original_tokens,
                "kept_tokens": mem.kept_tokens,
                "kv_savings_pct": mem.kv_savings_pct,
            },
        )

        tools = self.composio.get_openai_tools()
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"## Context (SuperCompress @ {self.settings.harbor_memory_budget:.0%} budget)\n\n"
                f"{compressed}\n\n## Task\n{user_prompt}",
            },
        ]

        final_summary = ""
        for turn_idx in range(2, 2 + self.settings.harbor_max_agent_turns):
            self._log(turns, turn_idx, "nebius", f"Inference turn {turn_idx - 1} via {getattr(self.nebius, 'model', 'nebius')}")
            result = self.nebius.chat(messages, tools=tools)

            if result.tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": result.content or "",
                        "tool_calls": result.tool_calls,
                    }
                )
                new_actions, tool_msgs = self._execute_tool_calls(result.tool_calls)
                actions.extend(new_actions)
                messages.extend(tool_msgs)
                self._log(turns, turn_idx, "composio", f"Executed {len(new_actions)} Composio tool(s)")
                continue

            final_summary = result.content
            self._log(turns, turn_idx, "complete", "Agent finished — no more tool calls")
            break

        return AgentRunResult(
            workflow=workflow,
            summary=final_summary,
            actions_taken=actions,
            memory_savings_pct=mem.kv_savings_pct,
            turns=turns,
            raw_messages=messages,
            prompt_meta={
                "system_preview": system_prompt[:400],
                "user_task": user_prompt[:800],
                "memory_policy": mem.policy_name,
                "context_blocks": len(context_blocks),
            },
        )

    def morning_brief(self, *, company: str = "OpenClaw", focus: str = "agent builders") -> AgentRunResult:
        """Full morning brief workflow across all integrations."""
        turns: List[TurnLog] = []
        self._log(turns, 0, "tavily", "Multi-query market research")
        tavily_news = self.tavily.search_and_answer(
            f"Latest news about {focus} and AI agents this week"
        )
        tavily_social = self.tavily.social_pulse(f"{company} {focus}")
        tavily_intel = self.tavily.company_intel(company)

        self._log(turns, 0, "composio", "Gathering from connected apps")
        composio_data = self.composio.gather_all()
        status = self.composio.integration_status()

        context_blocks = [
            tavily_news.to_context_block(),
            tavily_social.to_context_block(),
            tavily_intel.to_context_block(),
            *composio_data.all_context_blocks(),
        ]

        user_prompt = morning_brief_instructions(
            connected=status,
            slack_ready=self.composio.slack_delivery_ready(),
        )

        result = self.run_with_tools(
            MORNING_BRIEF_SYSTEM,
            user_prompt,
            context_blocks,
            workflow="morning_brief",
        )
        result.turns = turns + result.turns
        return result

    def incident_commander(
        self,
        incident_query: str,
        *,
        service_name: str = "production API",
    ) -> AgentRunResult:
        """Incident response workflow."""
        tavily_status = self.tavily.search_multi(
            [
                f"{service_name} outage status",
                f"{incident_query} site:status.github.com OR site:status.io",
                f"{incident_query} reddit OR hackernews",
            ],
            topic="news",
            time_range="day",
        )
        tavily_extract = self.tavily.extract_urls(
            [h.url for h in tavily_status.hits[:5]],
            query=incident_query,
        )
        tavily_status.extracted = tavily_extract

        composio_data = self.composio.gather_all()
        status = self.composio.integration_status()
        user_prompt = (
            f"Incident: {incident_query}\n"
            f"Service: {service_name}\n\n"
            + incident_instructions(
                connected=status,
                slack_ready=self.composio.slack_delivery_ready(),
            )
        )

        return self.run_with_tools(
            INCIDENT_COMMANDER_SYSTEM,
            user_prompt,
            [tavily_status.to_context_block(), *composio_data.all_context_blocks()],
            workflow="incident_commander",
        )
