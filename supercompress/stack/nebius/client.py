"""Nebius Token Factory — OpenAI-compatible inference for SuperCompress stack."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from openai import OpenAI

from supercompress.stack.config import Settings, get_settings
from supercompress.stack.nebius.models import FALLBACK_NEBIUS_MODELS, normalize_nebius_model


@dataclass
class InferenceResult:
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    raw: Any = None


class NebiusClient:
    """Thin wrapper over Nebius Token Factory chat completions."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                base_url=self.settings.nebius_base_url,
                api_key=self.settings.nebius_api_key,
            )
        return self._client

    @property
    def model(self) -> str:
        return normalize_nebius_model(self.settings.nebius_model)

    def _chat_with_model(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> InferenceResult:
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        resp = self.client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        msg = choice.message
        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                )
        usage = {}
        if resp.usage:
            usage = {
                "prompt_tokens": resp.usage.prompt_tokens or 0,
                "completion_tokens": resp.usage.completion_tokens or 0,
                "total_tokens": resp.usage.total_tokens or 0,
            }
        return InferenceResult(
            content=msg.content or "",
            model=model,
            usage=usage,
            tool_calls=tool_calls,
            raw=resp,
        )

    def chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> InferenceResult:
        primary = self.model
        candidates = [primary] + [m for m in FALLBACK_NEBIUS_MODELS if m != primary]
        last_exc: Optional[Exception] = None
        for model in candidates:
            try:
                return self._chat_with_model(
                    model,
                    messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as exc:
                err = str(exc).lower()
                if "does not exist" in err or "404" in err or "not found" in err:
                    last_exc = exc
                    continue
                raise
        if last_exc:
            raise last_exc
        raise RuntimeError("No Nebius model available")


class DemoNebiusClient(NebiusClient):
    """Deterministic inference for demo mode — no API key required."""

    def __init__(self, settings: Optional[Settings] = None):
        super().__init__(settings)
        self._turn = 0

    def chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> InferenceResult:
        has_tool_results = any(m.get("role") == "tool" for m in messages)
        last_user = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        self._turn += 1
        if tools and not has_tool_results and "morning brief" in str(last_user).lower():
            return InferenceResult(
                content="",
                model="demo/nebius",
                tool_calls=[
                    {
                        "id": "demo_tc_1",
                        "type": "function",
                        "function": {
                            "name": "SLACK_SEND_MESSAGE",
                            "arguments": json.dumps(
                                {
                                    "channel": "C-demo",
                                    "text": "🌅 SuperCompress Morning Brief (demo)\n• 2 PRs need review\n• 1 blocked Linear ticket\n• Agent ecosystem news: OpenClaw adoption up",
                                }
                            ),
                        },
                    },
                    {
                        "id": "demo_tc_2",
                        "type": "function",
                        "function": {
                            "name": "LINEAR_CREATE_LINEAR_ISSUE",
                            "arguments": json.dumps(
                                {
                                    "title": "Unblock ENG-231 Gmail OAuth refresh",
                                    "description": "Auto-filed by SuperCompress morning brief",
                                }
                            ),
                        },
                    },
                ],
            )

        summary = (
            "# SuperCompress Brief (demo inference via Nebius Token Factory stand-in)\n\n"
            "## GitHub\n- PR #42: Add auth middleware — review requested\n"
            "- Issue #17: Memory leak in agent loop\n\n"
            "## Linear\n- ENG-231 blocked on API keys\n\n"
            "## Market intel (Tavily)\n"
            "- Composio ships OpenClaw plugin\n"
            "- Nebius Token Factory adds Kimi K2\n\n"
            "## Recommended actions\n"
            "1. Review PR #42 today\n2. Unblock ENG-231\n3. Post digest to #builders"
        )
        return InferenceResult(content=summary, model="demo/nebius", usage={"total_tokens": 512})


def get_nebius(settings: Optional[Settings] = None) -> NebiusClient:
    s = settings or get_settings()
    if s.demo_mode or not s.has_nebius():
        return DemoNebiusClient(s)
    return NebiusClient(s)
