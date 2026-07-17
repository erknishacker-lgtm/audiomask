"""
Banco SQLite — usuários, planos diários e uso (GhostWave).
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

# Planos oficiais GhostWave
PLANS: Dict[str, Dict[str, Any]] = {
    "free": {
        "id": "free",
        "name_pt": "Gratuito",
        "name_en": "Free",
        "billing": "free",
        "daily_limit": 2,
        "price_brl": 0.0,
        "price_label": "R$ 0",
        "period_label_pt": "experiência",
        "features_pt": [
            "2 uploads por dia",
            "Dual-layer black → white",
            "Arquivos até 50 MB",
        ],
        "active": True,
    },
    "mensal": {
        "id": "mensal",
        "name_pt": "Mensal",
        "name_en": "Monthly",
        "billing": "monthly",
        "daily_limit": 10,
        "price_brl": 59.90,
        "price_label": "R$ 59,90",
        "period_label_pt": "/mês",
        "features_pt": [
            "10 vídeos por dia",
            "Dual-layer + phase-stereo",
            "Limpeza de metadados",
            "Compressão de vídeo",
        ],
        "active": True,
    },
    "trimestral": {
        "id": "trimestral",
        "name_pt": "Trimestral",
        "name_en": "Quarterly",
        "billing": "quarterly",
        "daily_limit": 20,
        "price_brl": 129.90,
        "price_label": "R$ 129,90",
        "period_label_pt": "/3 meses",
        "features_pt": [
            "20 vídeos por dia",
            "Todas as funções",
            "Fila prioritária",
            "Suporte prioritário",
        ],
        "active": True,
        "popular": True,
    },
    "anual": {
        "id": "anual",
        "name_pt": "Anual Ilimitado",
        "name_en": "Yearly Unlimited",
        "billing": "yearly",
        "daily_limit": 99999,
        "price_brl": 299.00,
        "price_label": "R$ 299,00",
        "period_label_pt": "/ano",
        "features_pt": [
            "Uploads ilimitados",
            "Todas as funções",
            "Arquivos grandes",
            "Suporte dedicado",
        ],
        "active": True,
    },
    # legado (mapeado)
    "pro": {
        "id": "pro",
        "name_pt": "Pro (legado)",
        "name_en": "Pro (legacy)",
        "billing": "monthly",
        "daily_limit": 10,
        "price_brl": 59.90,
        "price_label": "R$ 59,90",
        "period_label_pt": "/mês",
        "features_pt": [],
        "active": False,
    },
}

ADMIN_EMAIL = "admin@ghostwave.app"
ADMIN_PASSWORD = "GhostWave@Admin2026"
# mantém admin antigo funcionando
ADMIN_EMAIL_LEGACY = "admin@audiomask.com"


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


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


def daily_limit_for_plan(plan: str) -> int:
    info = PLANS.get(plan) or PLANS["free"]
    return int(info.get("daily_limit", 2))


@dataclass
class User:
    id: int
    email: str
    name: str
    role: str
    plan: str
    videos_used: int  # total histórico
    video_limit: int  # legado / diário espelhado
    daily_used: int
    daily_date: str
    active: bool
    notes: str
    created_at: str

    @property
    def daily_limit(self) -> int:
        return daily_limit_for_plan(self.plan)

    @property
    def videos_left(self) -> int:
        return max(0, self.daily_limit - int(self.daily_used))

    @property
    def can_process(self) -> bool:
        return self.active and self.videos_left > 0

    def to_dict(self) -> Dict[str, Any]:
        p = PLANS.get(self.plan, PLANS["free"])
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "plan": self.plan,
            "plan_name": p.get("name_pt", self.plan),
            "videos_used": self.videos_used,
            "video_limit": self.daily_limit,
            "daily_used": self.daily_used,
            "daily_limit": self.daily_limit,
            "daily_left": self.videos_left,
            "videos_left": self.videos_left,
            "active": self.active,
            "notes": self.notes,
            "created_at": self.created_at,
            "plan_price": p.get("price_brl", 0),
            "price_label": p.get("price_label", ""),
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
                    daily_used INTEGER NOT NULL DEFAULT 0,
                    daily_date TEXT NOT NULL DEFAULT '',
                    active INTEGER NOT NULL DEFAULT 1,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            # migração colunas
            cols = {
                r[1] for r in con.execute("PRAGMA table_info(users)").fetchall()
            }
            if "daily_used" not in cols:
                con.execute(
                    "ALTER TABLE users ADD COLUMN daily_used INTEGER NOT NULL DEFAULT 0"
                )
            if "daily_date" not in cols:
                con.execute(
                    "ALTER TABLE users ADD COLUMN daily_date TEXT NOT NULL DEFAULT ''"
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
        if not self.get_by_email(ADMIN_EMAIL):
            self.create_user(
                email=ADMIN_EMAIL,
                name="Administrador GhostWave",
                password=ADMIN_PASSWORD,
                role="admin",
                plan="anual",
            )
        # garante admin legado com plano alto
        leg = self.get_by_email(ADMIN_EMAIL_LEGACY)
        if leg and leg.role == "admin":
            self.update_user(leg.id, plan="anual")

    def _ensure_daily(self, user_id: int) -> None:
        today = _utc_today()
        with self._conn() as con:
            row = con.execute(
                "SELECT daily_date FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if not row:
                return
            if (row["daily_date"] or "") != today:
                con.execute(
                    "UPDATE users SET daily_used = 0, daily_date = ? WHERE id = ?",
                    (today, user_id),
                )

    def _row_user(self, row: sqlite3.Row) -> User:
        return User(
            id=int(row["id"]),
            email=row["email"],
            name=row["name"],
            role=row["role"],
            plan=row["plan"],
            videos_used=int(row["videos_used"] or 0),
            video_limit=int(row["video_limit"] or 2),
            daily_used=int(row["daily_used"] or 0) if "daily_used" in row.keys() else 0,
            daily_date=(row["daily_date"] or "") if "daily_date" in row.keys() else "",
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
        limit = (
            video_limit
            if video_limit is not None
            else int(plan_info.get("daily_limit", 2))
        )
        now = datetime.now(timezone.utc).isoformat()
        ph = _hash_password(password)
        with self._conn() as con:
            cur = con.execute(
                """
                INSERT INTO users
                (email, name, password_hash, role, plan, videos_used, video_limit,
                 daily_used, daily_date, active, notes, created_at)
                VALUES (?, ?, ?, ?, ?, 0, ?, 0, ?, 1, '', ?)
                """,
                (
                    email,
                    name.strip() or email.split("@")[0],
                    ph,
                    role,
                    plan,
                    limit,
                    _utc_today(),
                    now,
                ),
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
        # também aceita admin legado com senha antiga
        self._ensure_daily(user.id)
        return self.get_by_id(user.id)

    def get_by_email(self, email: str) -> Optional[User]:
        with self._conn() as con:
            row = con.execute(
                "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
            ).fetchone()
        if not row:
            return None
        self._ensure_daily(int(row["id"]))
        with self._conn() as con:
            row = con.execute(
                "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
            ).fetchone()
        return self._row_user(row) if row else None

    def get_by_id(self, user_id: int) -> Optional[User]:
        self._ensure_daily(int(user_id))
        with self._conn() as con:
            row = con.execute(
                "SELECT * FROM users WHERE id = ?", (int(user_id),)
            ).fetchone()
        return self._row_user(row) if row else None

    def list_users(self) -> List[User]:
        with self._conn() as con:
            rows = con.execute("SELECT * FROM users ORDER BY id ASC").fetchall()
        users = []
        for r in rows:
            self._ensure_daily(int(r["id"]))
        with self._conn() as con:
            rows = con.execute("SELECT * FROM users ORDER BY id ASC").fetchall()
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
        daily_used: Optional[int] = None,
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
            dl = daily_limit_for_plan(plan)
            fields.append("video_limit = ?")
            vals.append(dl)
        if video_limit is not None:
            fields.append("video_limit = ?")
            vals.append(int(video_limit))
        if videos_used is not None:
            fields.append("videos_used = ?")
            vals.append(int(videos_used))
        if daily_used is not None:
            fields.append("daily_used = ?")
            vals.append(int(daily_used))
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
            con.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", vals)
        return self.get_by_id(user_id)

    def consume_video(
        self, user_id: int, kind: str = "video", platform: str = "", filename: str = ""
    ) -> bool:
        self._ensure_daily(user_id)
        user = self.get_by_id(user_id)
        if not user or not user.can_process:
            return False
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as con:
            con.execute(
                """
                UPDATE users SET
                  videos_used = videos_used + 1,
                  daily_used = daily_used + 1,
                  daily_date = ?
                WHERE id = ?
                """,
                (_utc_today(), user_id),
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
            "pro_users": sum(1 for u in users if u.plan not in ("free",)),
            "free_users": sum(1 for u in users if u.plan == "free"),
            "videos_processed": sum(u.videos_used for u in users),
        }


_db_singleton: Optional[UserDB] = None


def get_db() -> UserDB:
    global _db_singleton
    if _db_singleton is None:
        _db_singleton = UserDB()
    return _db_singleton
