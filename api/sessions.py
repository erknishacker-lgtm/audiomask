"""Sessões em memória + SQLite-backed user ids via token."""

from __future__ import annotations

import secrets
import time
from typing import Dict, Optional

# token -> {user_id, exp}
_SESSIONS: Dict[str, dict] = {}
TTL_SEC = 60 * 60 * 24 * 7  # 7 dias


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    _SESSIONS[token] = {"user_id": int(user_id), "exp": time.time() + TTL_SEC}
    return token


def get_user_id(token: Optional[str]) -> Optional[int]:
    if not token:
        return None
    data = _SESSIONS.get(token)
    if not data:
        return None
    if time.time() > data["exp"]:
        _SESSIONS.pop(token, None)
        return None
    return int(data["user_id"])


def destroy_session(token: Optional[str]) -> None:
    if token:
        _SESSIONS.pop(token, None)
