"""Dashboard auth and API key tests."""

import os

import pytest
from fastapi.testclient import TestClient

from supercompress.stack import db
from supercompress.stack.server import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def enable_auth(monkeypatch):
    monkeypatch.delenv("SUPERCOMPRESS_AUTH_DISABLED", raising=False)
    db.init_db()


def test_signup_login_and_key_lifecycle():
    import uuid

    email = f"dev-{uuid.uuid4().hex[:8]}@supercompress.test"
    signup = client.post(
        "/v1/auth/signup",
        json={"email": email, "password": "testpass123", "name": "Dev"},
    )
    assert signup.status_code == 200
    token = signup.json()["token"]
    assert signup.json()["user"]["email"] == email

    login = client.post("/v1/auth/login", json={"email": email, "password": "testpass123"})
    assert login.status_code == 200

    keys = client.post(
        "/v1/dashboard/keys",
        json={"name": "CI key"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert keys.status_code == 200
    api_key = keys.json()["api_key"]
    assert api_key.startswith("sc_live_")

    denied = client.post(
        "/v1/compress/blocks",
        json={"context_blocks": ["hello world"], "query": "hi"},
    )
    assert denied.status_code == 401

    ok = client.post(
        "/v1/compress/blocks",
        json={"context_blocks": ["hello world " * 20], "query": "summarize"},
        headers={"X-API-Key": api_key},
    )
    assert ok.status_code == 200
    assert ok.json()["compressed_text"]

    usage = client.get("/v1/dashboard/usage", headers={"Authorization": f"Bearer {token}"})
    assert usage.status_code == 200
    assert usage.json()["totals"]["requests"] >= 1

    key_id = keys.json()["id"]
    revoke = client.delete(f"/v1/dashboard/keys/{key_id}", headers={"Authorization": f"Bearer {token}"})
    assert revoke.status_code == 200

    blocked = client.post(
        "/v1/compress/blocks",
        json={"context_blocks": ["hello"], "query": "hi"},
        headers={"X-API-Key": api_key},
    )
    assert blocked.status_code == 401
