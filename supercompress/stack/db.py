"""SQLite persistence for dashboard users, API keys, and usage."""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from supercompress.stack._paths import ROOT

_local = threading.local()
_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS api_keys (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    created_at REAL NOT NULL,
    last_used_at REAL,
    revoked INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS usage_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_id TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    original_tokens INTEGER NOT NULL DEFAULT 0,
    kept_tokens INTEGER NOT NULL DEFAULT 0,
    kv_savings_pct REAL NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    FOREIGN KEY (key_id) REFERENCES api_keys(id)
);

CREATE INDEX IF NOT EXISTS idx_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_keys_user ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_key ON usage_events(key_id);
"""


def db_path() -> Path:
    import os

    raw = os.environ.get("SUPERCOMPRESS_DB_PATH", "")
    if raw:
        return Path(raw)
    data = ROOT / "data"
    data.mkdir(parents=True, exist_ok=True)
    return data / "supercompress.db"


def get_conn() -> sqlite3.Connection:
    if not getattr(_local, "conn", None):
        conn = sqlite3.connect(str(db_path()), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _local.conn = conn
    return _local.conn


def init_db() -> None:
    conn = get_conn()
    conn.executescript(_SCHEMA)
    conn.commit()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def create_user(user_id: str, email: str, password_hash: str, name: str) -> Dict[str, Any]:
    now = time.time()
    conn = get_conn()
    conn.execute(
        "INSERT INTO users (id, email, password_hash, name, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, email.lower().strip(), password_hash, name.strip(), now),
    )
    conn.commit()
    return {"id": user_id, "email": email.lower().strip(), "name": name.strip(), "created_at": now}


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
    return _row_to_dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row_to_dict(row) if row else None


def create_api_key(
    key_id: str,
    user_id: str,
    name: str,
    key_prefix: str,
    key_hash: str,
) -> Dict[str, Any]:
    now = time.time()
    conn = get_conn()
    conn.execute(
        """INSERT INTO api_keys (id, user_id, name, key_prefix, key_hash, created_at, revoked)
           VALUES (?, ?, ?, ?, ?, ?, 0)""",
        (key_id, user_id, name.strip(), key_prefix, key_hash, now),
    )
    conn.commit()
    return {
        "id": key_id,
        "user_id": user_id,
        "name": name.strip(),
        "key_prefix": key_prefix,
        "created_at": now,
    }


def list_api_keys(user_id: str) -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT id, user_id, name, key_prefix, created_at, last_used_at, revoked
           FROM api_keys WHERE user_id = ? AND revoked = 0 ORDER BY created_at DESC""",
        (user_id,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def revoke_api_key(user_id: str, key_id: str) -> bool:
    conn = get_conn()
    cur = conn.execute(
        "UPDATE api_keys SET revoked = 1 WHERE id = ? AND user_id = ? AND revoked = 0",
        (key_id, user_id),
    )
    conn.commit()
    return cur.rowcount > 0


def lookup_api_key(key_hash: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    row = conn.execute(
        """SELECT id, user_id, name, key_prefix, key_hash, created_at, last_used_at, revoked
           FROM api_keys WHERE key_hash = ? AND revoked = 0""",
        (key_hash,),
    ).fetchone()
    return _row_to_dict(row) if row else None


def touch_api_key(key_id: str) -> None:
    conn = get_conn()
    conn.execute("UPDATE api_keys SET last_used_at = ? WHERE id = ?", (time.time(), key_id))
    conn.commit()


def log_usage(
    key_id: str,
    endpoint: str,
    *,
    original_tokens: int = 0,
    kept_tokens: int = 0,
    kv_savings_pct: float = 0,
) -> None:
    conn = get_conn()
    conn.execute(
        """INSERT INTO usage_events (key_id, endpoint, original_tokens, kept_tokens, kv_savings_pct, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (key_id, endpoint, original_tokens, kept_tokens, kv_savings_pct, time.time()),
    )
    conn.commit()


def usage_summary(user_id: str, *, limit: int = 50) -> Dict[str, Any]:
    conn = get_conn()
    totals = conn.execute(
        """SELECT COUNT(*) AS requests,
                  COALESCE(SUM(u.original_tokens), 0) AS original_tokens,
                  COALESCE(SUM(u.kept_tokens), 0) AS kept_tokens,
                  COALESCE(AVG(u.kv_savings_pct), 0) AS avg_savings
           FROM usage_events u
           JOIN api_keys k ON k.id = u.key_id
           WHERE k.user_id = ?""",
        (user_id,),
    ).fetchone()

    recent = conn.execute(
        """SELECT u.endpoint, u.original_tokens, u.kept_tokens, u.kv_savings_pct, u.created_at, k.name AS key_name
           FROM usage_events u
           JOIN api_keys k ON k.id = u.key_id
           WHERE k.user_id = ?
           ORDER BY u.created_at DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()

    by_key = conn.execute(
        """SELECT k.id, k.name, k.key_prefix, COUNT(u.id) AS requests,
                  COALESCE(SUM(u.original_tokens), 0) AS original_tokens,
                  COALESCE(SUM(u.kept_tokens), 0) AS kept_tokens
           FROM api_keys k
           LEFT JOIN usage_events u ON u.key_id = k.id
           WHERE k.user_id = ? AND k.revoked = 0
           GROUP BY k.id ORDER BY requests DESC""",
        (user_id,),
    ).fetchall()

    return {
        "totals": _row_to_dict(totals) if totals else {},
        "recent": [_row_to_dict(r) for r in recent],
        "by_key": [_row_to_dict(r) for r in by_key],
    }
