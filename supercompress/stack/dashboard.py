"""Dashboard API — signup, login, API keys, usage."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from supercompress.stack import auth, db
from supercompress.stack.composio import get_composio
from supercompress.stack.config import settings_for_user
from supercompress.stack.firebase_auth import firebase_enabled, public_config

router = APIRouter(tags=["Dashboard"])

CONNECTABLE_TOOLKITS = ["gmail", "github", "linear", "slack", "notion", "googlecalendar"]


class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class CreateKeyRequest(BaseModel):
    name: str = "Default"


class AuthResponse(BaseModel):
    token: str
    user: Dict[str, Any]


class KeyCreatedResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    api_key: str
    created_at: float


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    return {"id": user["id"], "email": user["email"], "name": user.get("name", ""), "created_at": user["created_at"]}


@router.get("/auth/config")
def auth_config() -> Dict[str, Any]:
    """Public Firebase web config for dashboard client."""
    cfg = public_config()
    return {
        "firebase": cfg,
        "auth": "firebase" if cfg.get("enabled") else "legacy",
    }


@router.post("/auth/signup", response_model=AuthResponse)
def signup(req: SignupRequest) -> AuthResponse:
    if firebase_enabled() and public_config().get("enabled"):
        raise HTTPException(
            status_code=400,
            detail="Sign up via Firebase on the dashboard (email or Google).",
        )
    email = req.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Invalid email address.")
    if db.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="Email already registered.")
    user_id = auth.new_id()
    user = db.create_user(user_id, email, auth.hash_password(req.password), req.name or email.split("@")[0])
    token = auth.create_session_token(user_id)
    return AuthResponse(token=token, user=_public_user(user))


@router.post("/auth/login", response_model=AuthResponse)
def login(req: LoginRequest) -> AuthResponse:
    if firebase_enabled() and public_config().get("enabled"):
        raise HTTPException(status_code=400, detail="Sign in via Firebase on the dashboard.")
    user = db.get_user_by_email(req.email)
    if not user or not auth.verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = auth.create_session_token(user["id"])
    return AuthResponse(token=token, user=_public_user(user))


@router.get("/dashboard/me")
def me(user: Dict[str, Any] = Depends(auth.require_user)) -> Dict[str, Any]:
    return {"user": _public_user(user)}


@router.get("/dashboard/keys")
def list_keys(user: Dict[str, Any] = Depends(auth.require_user)) -> Dict[str, List[Dict[str, Any]]]:
    keys = db.list_api_keys(user["id"])
    return {
        "keys": [
            {
                "id": k["id"],
                "name": k["name"],
                "key_prefix": k["key_prefix"],
                "created_at": k["created_at"],
                "last_used_at": k.get("last_used_at"),
            }
            for k in keys
        ]
    }


@router.post("/dashboard/keys", response_model=KeyCreatedResponse)
def create_key(
    req: CreateKeyRequest,
    user: Dict[str, Any] = Depends(auth.require_user),
) -> KeyCreatedResponse:
    full_key, prefix, key_hash = auth.generate_api_key()
    key_id = auth.new_id()
    record = db.create_api_key(key_id, user["id"], req.name or "Default", prefix, key_hash)
    return KeyCreatedResponse(
        id=record["id"],
        name=record["name"],
        key_prefix=prefix,
        api_key=full_key,
        created_at=record["created_at"],
    )


@router.delete("/dashboard/keys/{key_id}")
def delete_key(key_id: str, user: Dict[str, Any] = Depends(auth.require_user)) -> Dict[str, bool]:
    if not db.revoke_api_key(user["id"], key_id):
        raise HTTPException(status_code=404, detail="Key not found.")
    return {"ok": True}


@router.get("/dashboard/usage")
def usage(user: Dict[str, Any] = Depends(auth.require_user)) -> Dict[str, Any]:
    return db.usage_summary(user["id"])


@router.get("/dashboard/integrations")
def integrations(user: Dict[str, Any] = Depends(auth.require_user)) -> Dict[str, Any]:
    """Composio connection status for this developer account."""
    composio = get_composio(settings_for_user(user["id"]))
    summary = composio.connection_summary()
    return {
        "toolkits": CONNECTABLE_TOOLKITS,
        "linked": summary.get("linked", []),
        "missing": summary.get("missing_oauth", []),
        "all_linked": summary.get("all_linked", False),
        "note": "Connect apps here — every API call gathers from your linked Composio accounts.",
    }


@router.post("/dashboard/integrations/connect/{toolkit}")
def connect_integration(toolkit: str, user: Dict[str, Any] = Depends(auth.require_user)) -> Dict[str, Any]:
    slug = toolkit.lower().strip()
    if slug not in CONNECTABLE_TOOLKITS:
        raise HTTPException(status_code=400, detail=f"Unknown toolkit. Use: {', '.join(CONNECTABLE_TOOLKITS)}")
    composio = get_composio(settings_for_user(user["id"]))
    result = composio.auth_connect(slug)
    if result.error and not result.already_connected:
        raise HTTPException(status_code=502, detail=result.error)
    return {
        "toolkit": slug,
        "already_connected": result.already_connected,
        "redirect_url": result.redirect_url,
    }
