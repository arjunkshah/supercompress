"""Firebase Admin — verify ID tokens from dashboard clients."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

_app = None
_init_attempted = False


def _has_service_account() -> bool:
    return bool(
        os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
        or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    )


def firebase_enabled() -> bool:
    return bool(
        _has_service_account()
        or (
            os.environ.get("FIREBASE_PROJECT_ID", "").strip()
            and os.environ.get("FIREBASE_API_KEY", "").strip()
        )
    )


def public_config() -> Dict[str, Any]:
    """Client-safe Firebase web config (from env)."""
    project_id = os.environ.get("FIREBASE_PROJECT_ID", "").strip()
    api_key = os.environ.get("FIREBASE_API_KEY", "").strip()
    auth_domain = os.environ.get("FIREBASE_AUTH_DOMAIN", "").strip() or (
        f"{project_id}.firebaseapp.com" if project_id else ""
    )
    return {
        "enabled": bool(project_id and api_key),
        "apiKey": api_key,
        "authDomain": auth_domain,
        "projectId": project_id,
        "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET", "").strip()
        or (f"{project_id}.appspot.com" if project_id else ""),
        "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID", "").strip(),
        "appId": os.environ.get("FIREBASE_APP_ID", "").strip(),
    }


def _ensure_app():
    global _app, _init_attempted
    if _app is not None or _init_attempted:
        return _app
    _init_attempted = True
    if not _has_service_account():
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials

        if firebase_admin._apps:
            _app = firebase_admin.get_app()
            return _app

        raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
        if raw:
            cred = credentials.Certificate(json.loads(raw))
        elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            cred = credentials.Certificate(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
        else:
            cred = credentials.ApplicationDefault()
        _app = firebase_admin.initialize_app(cred, {"projectId": os.environ.get("FIREBASE_PROJECT_ID")})
    except Exception:
        _app = None
    return _app


def _verify_via_identity_toolkit(token: str) -> Optional[Dict[str, Any]]:
    """Verify ID token via Identity Toolkit (works with public API key only)."""
    api_key = os.environ.get("FIREBASE_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        import httpx

        r = httpx.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={api_key}",
            json={"idToken": token},
            timeout=10,
        )
        if r.status_code != 200:
            return None
        users = r.json().get("users") or []
        if not users:
            return None
        u = users[0]
        return {
            "uid": u.get("localId"),
            "email": u.get("email"),
            "name": u.get("displayName"),
        }
    except Exception:
        return None


def verify_id_token(token: str) -> Optional[Dict[str, Any]]:
    """Return decoded Firebase claims or None."""
    if not token or not firebase_enabled():
        return None

    if _ensure_app() is not None:
        try:
            from firebase_admin import auth as fb_auth

            decoded = fb_auth.verify_id_token(token, check_revoked=True)
            return dict(decoded)
        except Exception:
            pass

    return _verify_via_identity_toolkit(token)
