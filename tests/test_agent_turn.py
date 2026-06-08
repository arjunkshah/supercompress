"""Agent turn API — full stack product."""

from fastapi.testclient import TestClient

from supercompress.stack.config import get_settings
from supercompress.stack.server import app

client = TestClient(app)


def test_agent_turn_demo_stack(monkeypatch):
    monkeypatch.setenv("HARBOR_DEMO", "1")
    get_settings.cache_clear()

    r = client.post(
        "/v1/agent/turn",
        json={
            "query": "What should I ship today?",
            "context_blocks": ["## Tasks\n- Fix onboarding bug"],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["answer"]
    assert data["memory"]["kv_savings_pct"] >= 0
    phases = [p["phase"] for p in data["phases"]]
    assert "tavily" in phases
    assert "composio" in phases
    assert "memory" in phases
    assert "app" in phases or data.get("sources", {}).get("app_blocks", 0) >= 0
    assert data.get("stack", {}).get("tavily") is True

    get_settings.cache_clear()
