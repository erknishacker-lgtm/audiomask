"""
Banco SQLite de usuários, planos e uso (vídeos processados).
"""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "users.db")

# Planos oficiais
PLANS: Dict[str, Dict[str, Any]] = {
    "free": {
        "id": "free",
        "name_pt": "Gratuito",
        "name_en": "Free",
        "video_limit": 2,
        "price_brl": 0.0,
        "active": True,
    },
    "pro": {
        "id": "pro",
        "name_pt": "Pro",
        "name_en": "Pro",
        "video_limit": 99999,  # ilimitado prático
        "price_brl": 49.90,
        "active": True,
    },
}

ADMIN_EMAIL = "admin@audiomask.com"
ADMIN_PASSWORD = "Admin@AudioMask2026"


def _hash_password(password: str, salt: Optional[str] = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    dig = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000
    )
    return f"{salt}${dig.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
        return secrets.compare_digest(_hash_password(password, salt), stored)
    except Exception:
        return False


@dataclass
class User:
    id: int
    email: str
    name: str
    role: str  # admin | user
    plan: str  # free | pro
    videos_used: int
    video_limit: int
    active: bool
    notes: str
    created_at: str

    @property
    def videos_left(self) -> int:
        return max(0, int(self.video_limit) - int(self.videos_used))

    @property
    def can_process(self) -> bool:
        return self.active and self.videos_left > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "plan": self.plan,
            "videos_used": self.videos_used,
            "video_limit": self.video_limit,
            "videos_left": self.videos_left,
            "active": self.active,
            "notes": self.notes,
            "created_at": self.created_at,
            "plan_price": PLANS.get(self.plan, {}).get("price_brl", 0),
        }


class UserDB:
    def __init__(self, path: str = DB_PATH) -> None:
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._init_schema()
        self._seed_admin()

    @contextmanager
    def _conn(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()

    def _init_schema(self) -> None:
        with self._conn() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    plan TEXT NOT NULL DEFAULT 'free',
                    videos_used INTEGER NOT NULL DEFAULT 0,
                    video_limit INTEGER NOT NULL DEFAULT 2,
                    active INTEGER NOT NULL DEFAULT 1,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    platform TEXT,
                    filename TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )

    def _seed_admin(self) -> None:
        if self.get_by_email(ADMIN_EMAIL):
            return
        self.create_user(
            email=ADMIN_EMAIL,
            name="Administrador",
            password=ADMIN_PASSWORD,
            role="admin",
            plan="pro",
            video_limit=99999,
        )

    def _row_user(self, row: sqlite3.Row) -> User:
        return User(
            id=int(row["id"]),
            email=row["email"],
            name=row["name"],
            role=row["role"],
            plan=row["plan"],
            videos_used=int(row["videos_used"]),
            video_limit=int(row["video_limit"]),
            active=bool(row["active"]),
            notes=row["notes"] or "",
            created_at=row["created_at"],
        )

    def create_user(
        self,
        email: str,
        name: str,
        password: str,
        role: str = "user",
        plan: str = "free",
        video_limit: Optional[int] = None,
    ) -> Optional[User]:
        email = email.strip().lower()
        if not email or not password or len(password) < 6:
            return None
        if self.get_by_email(email):
            return None
        plan_info = PLANS.get(plan, PLANS["free"])
        limit = video_limit if video_limit is not None else int(plan_info["video_limit"])
        now = datetime.now(timezone.utc).isoformat()
        ph = _hash_password(password)
        with self._conn() as con:
            cur = con.execute(
                """
                INSERT INTO users
                (email, name, password_hash, role, plan, videos_used, video_limit, active, notes, created_at)
                VALUES (?, ?, ?, ?, ?, 0, ?, 1, '', ?)
                """,
                (email, name.strip() or email.split("@")[0], ph, role, plan, limit, now),
            )
            uid = int(cur.lastrowid)
        return self.get_by_id(uid)

    def authenticate(self, email: str, password: str) -> Optional[User]:
        user = self.get_by_email(email.strip().lower())
        if not user:
            return None
        with self._conn() as con:
            row = con.execute(
                "SELECT password_hash, active FROM users WHERE id = ?", (user.id,)
            ).fetchone()
        if not row or not row["active"]:
            return None
        if not _verify_password(password, row["password_hash"]):
            return None
        return user

    def get_by_email(self, email: str) -> Optional[User]:
        with self._conn() as con:
            row = con.execute(
                "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
            ).fetchone()
        return self._row_user(row) if row else None

    def get_by_id(self, user_id: int) -> Optional[User]:
        with self._conn() as con:
            row = con.execute(
                "SELECT * FROM users WHERE id = ?", (int(user_id),)
            ).fetchone()
        return self._row_user(row) if row else None

    def list_users(self) -> List[User]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT * FROM users ORDER BY id ASC"
            ).fetchall()
        return [self._row_user(r) for r in rows]

    def update_user(
        self,
        user_id: int,
        *,
        name: Optional[str] = None,
        role: Optional[str] = None,
        plan: Optional[str] = None,
        video_limit: Optional[int] = None,
        videos_used: Optional[int] = None,
        active: Optional[bool] = None,
        notes: Optional[str] = None,
        new_password: Optional[str] = None,
    ) -> Optional[User]:
        user = self.get_by_id(user_id)
        if not user:
            return None
        fields = []
        vals: list = []
        if name is not None:
            fields.append("name = ?")
            vals.append(name)
        if role is not None:
            fields.append("role = ?")
            vals.append(role)
        if plan is not None:
            fields.append("plan = ?")
            vals.append(plan)
            if video_limit is None and plan in PLANS:
                fields.append("video_limit = ?")
                vals.append(int(PLANS[plan]["video_limit"]))
        if video_limit is not None:
            fields.append("video_limit = ?")
            vals.append(int(video_limit))
        if videos_used is not None:
            fields.append("videos_used = ?")
            vals.append(int(videos_used))
        if active is not None:
            fields.append("active = ?")
            vals.append(1 if active else 0)
        if notes is not None:
            fields.append("notes = ?")
            vals.append(notes)
        if new_password:
            fields.append("password_hash = ?")
            vals.append(_hash_password(new_password))
        if not fields:
            return user
        vals.append(user_id)
        with self._conn() as con:
            con.execute(
                f"UPDATE users SET {', '.join(fields)} WHERE id = ?", vals
            )
        return self.get_by_id(user_id)

    def consume_video(
        self, user_id: int, kind: str = "video", platform: str = "", filename: str = ""
    ) -> bool:
        """Consome 1 crédito se houver. Retorna False se sem cota."""
        user = self.get_by_id(user_id)
        if not user or not user.can_process:
            return False
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as con:
            con.execute(
                "UPDATE users SET videos_used = videos_used + 1 WHERE id = ?",
                (user_id,),
            )
            con.execute(
                """
                INSERT INTO usage_log (user_id, kind, platform, filename, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, kind, platform, filename, now),
            )
        return True

    def usage_for_user(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        with self._conn() as con:
            rows = con.execute(
                """
                SELECT * FROM usage_log WHERE user_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> Dict[str, Any]:
        users = self.list_users()
        return {
            "total_users": len(users),
            "active_users": sum(1 for u in users if u.active),
            "pro_users": sum(1 for u in users if u.plan == "pro"),
            "free_users": sum(1 for u in users if u.plan == "free"),
            "videos_processed": sum(u.videos_used for u in users),
        }


_db_singleton: Optional[UserDB] = None


def get_db() -> UserDB:
    global _db_singleton
    if _db_singleton is None:
        _db_singleton = UserDB()
    return _db_singleton
