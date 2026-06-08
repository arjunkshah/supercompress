"""Password hashing, JWT sessions, and API key verification."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from supercompress.stack import db

PBKDF2_ITERATIONS = 260_000
API_KEY_PREFIX = "sc_live_"
TOKEN_TTL_SECONDS = 60 * 60 * 24 * 14  # 14 days

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def auth_disabled() -> bool:
    return os.environ.get("SUPERCOMPRESS_AUTH_DISABLED", "").strip().lower() in ("1", "true", "yes")


def jwt_secret() -> str:
    secret = os.environ.get("SUPERCOMPRESS_JWT_SECRET", "").strip()
    if not secret:
        secret = os.environ.get("SUPERCOMPRESS_MASTER_SECRET", "").strip()
    if not secret:
        secret = "dev-insecure-change-me"
    return secret


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2${PBKDF2_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters_s, salt_b64, digest_b64 = stored.split("$", 3)
        if algo != "pbkdf2":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        got = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iters_s))
        return hmac.compare_digest(got, expected)
    except (ValueError, TypeError):
        return False


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def create_session_token(user_id: str) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = {
        "sub": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(jwt_secret().encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url(sig)}"


def decode_session_token(token: str) -> Optional[str]:
    try:
        header, body, sig = token.split(".", 2)
        expected = hmac.new(jwt_secret().encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url(expected), sig):
            return None
        payload = json.loads(_b64url_decode(body))
        if int(payload.get("exp", 0)) < time.time():
            return None
        return str(payload.get("sub", "")) or None
    except (ValueError, json.JSONDecodeError, TypeError):
        return None


def generate_api_key() -> tuple[str, str, str]:
    """Return (full_key, display_prefix, hash)."""
    raw = secrets.token_urlsafe(32)
    full = f"{API_KEY_PREFIX}{raw}"
    display = f"{API_KEY_PREFIX}{raw[:4]}…{raw[-4:]}"
    key_hash = hash_api_key(full)
    return full, display, key_hash


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.strip().encode()).hexdigest()


def new_id() -> str:
    return uuid.uuid4().hex


def extract_api_key(
    request: Request,
    header_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> Optional[str]:
    if header_key:
        return header_key.strip()
    if bearer and bearer.credentials:
        cred = bearer.credentials.strip()
        if cred.startswith(API_KEY_PREFIX):
            return cred
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer ") and API_KEY_PREFIX in auth:
        return auth.split(" ", 1)[1].strip()
    return None


def require_api_key(
    request: Request,
    header_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> Dict[str, Any]:
    if auth_disabled():
        return {"id": "dev", "user_id": "dev", "name": "dev"}

    key = extract_api_key(request, header_key, bearer)
    if not key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Create one at /dashboard.html — pass X-API-Key header.",
        )
    record = db.lookup_api_key(hash_api_key(key))
    if not record:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key.")
    db.touch_api_key(record["id"])
    request.state.api_key_id = record["id"]
    request.state.api_key_user_id = record["user_id"]
    return record


def require_user(
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> Dict[str, Any]:
    if not bearer or not bearer.credentials:
        raise HTTPException(status_code=401, detail="Sign in required.")
    user_id = decode_session_token(bearer.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


def log_request_usage(request: Request, endpoint: str, stats: Dict[str, Any]) -> None:
    if auth_disabled():
        return
    key_id = getattr(request.state, "api_key_id", None)
    if not key_id:
        return
    db.log_usage(
        key_id,
        endpoint,
        original_tokens=int(stats.get("original_tokens", 0)),
        kept_tokens=int(stats.get("kept_tokens", 0)),
        kv_savings_pct=float(stats.get("kv_savings_pct", 0)),
    )
