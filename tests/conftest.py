import os

import pytest


@pytest.fixture(autouse=True)
def disable_api_auth(monkeypatch):
    """Tests run without API keys unless a test opts out."""
    monkeypatch.setenv("SUPERCOMPRESS_AUTH_DISABLED", "1")
