"""Tests for BuilderShip sponsor stack (demo mode)."""

import os

import pytest


@pytest.fixture(autouse=True)
def demo_mode(monkeypatch):
    monkeypatch.setenv("HARBOR_DEMO", "1")


def test_doctor_demo_mode():
    from supercompress.stack.config import get_settings
    from supercompress.stack.doctor import run_doctor_checks

    get_settings.cache_clear()
    results = run_doctor_checks()
    names = {r.name for r in results}
    assert "SuperCompress memory" in names
    assert "Tavily search" in names
    assert "Composio toolkits" in names
    assert all(r.ok for r in results)


def test_demo_loop_runs(capsys):
    from supercompress.stack.config import get_settings
    from supercompress.stack.demo_loop import run_loop

    get_settings.cache_clear()
    assert run_loop(task="demo task", live=False) == 0
    out = capsys.readouterr().out
    assert "Tavily" in out
    assert "SuperCompress" in out
    assert "KV savings" in out


def test_stack_agent_compresses():
    from supercompress.stack.agent.loop import StackAgent
    from supercompress.stack.config import get_settings

    get_settings.cache_clear()
    agent = StackAgent()
    result = agent.run_with_tools(
        "You are a test agent.",
        "Summarize my PRs",
        ["## GitHub\n- PR #1 test"],
        workflow="test",
    )
    assert result.memory_savings_pct >= 0
    assert result.summary
