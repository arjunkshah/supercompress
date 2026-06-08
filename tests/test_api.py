"""HTTP API tests."""

from fastapi.testclient import TestClient

from supercompress.stack.server import app

client = TestClient(app)


def test_v1_health():
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["version"] == "v1"


def test_v1_compress_blocks():
    r = client.post(
        "/v1/compress/blocks",
        json={
            "context_blocks": ["## GitHub\nPR #42 open", "## Gmail\n2 unread"],
            "query": "what should I do first?",
            "budget_ratio": 0.35,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["compressed_text"]
    assert data["stats"]["kept_tokens"] <= data["stats"]["original_tokens"]
    assert data["stats"]["kv_savings_pct"] >= 0


def test_v1_compare():
    r = client.post(
        "/v1/compare",
        json={
            "context_blocks": ["def foo():\n    return 1\n" * 40],
            "query": "where is foo?",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "fifo" in body and "supercompress" in body
