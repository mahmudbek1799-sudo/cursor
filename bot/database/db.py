"""Слой доступа к данным (SQLite + aiosqlite).

Хранит:
    * users           — известные пользователи (кэш профилей);
    * group_settings  — индивидуальные настройки каждой группы (антиспам,
                        лимит варнов, доверенные домены, список мата);
    * warns           — выданные предупреждения;
    * bans            — активные баны / муты;
    * logs            — единый журнал нарушений и админ-действий.

Все методы — корутины. Класс ``Database`` представляет собой
синглтон-обёртку: в проекте используется готовый экземпляр ``db``.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

import aiosqlite

from config import settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    full_name   TEXT,
    first_seen  INTEGER NOT NULL,
    last_seen   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS group_settings (
    chat_id          INTEGER PRIMARY KEY,
    title            TEXT,
    antispam_msgs    INTEGER NOT NULL DEFAULT 5,
    antispam_seconds INTEGER NOT NULL DEFAULT 10,
    warn_limit       INTEGER NOT NULL DEFAULT 3,
    mute_hours       INTEGER NOT NULL DEFAULT 24,
    bad_words        TEXT    NOT NULL DEFAULT '[]',
    trusted_domains  TEXT    NOT NULL DEFAULT '[]',
    antispam_on      INTEGER NOT NULL DEFAULT 1,
    antilinks_on     INTEGER NOT NULL DEFAULT 1,
    antibadwords_on  INTEGER NOT NULL DEFAULT 1,
    welcome_text     TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS warns (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id   INTEGER NOT NULL,
    user_id   INTEGER NOT NULL,
    admin_id  INTEGER NOT NULL,
    reason    TEXT,
    created   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_warns_chat_user ON warns(chat_id, user_id);

CREATE TABLE IF NOT EXISTS bans (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id    INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    admin_id   INTEGER NOT NULL,
    kind       TEXT NOT NULL,            -- ban | mute
    reason     TEXT,
    until_ts   INTEGER,                  -- 0 / NULL = бессрочно
    active     INTEGER NOT NULL DEFAULT 1,
    created    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bans_chat_user ON bans(chat_id, user_id);

CREATE TABLE IF NOT EXISTS logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id   INTEGER,
    user_id   INTEGER,
    admin_id  INTEGER,
    action    TEXT NOT NULL,
    details   TEXT,
    created   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_logs_chat ON logs(chat_id);
CREATE INDEX IF NOT EXISTS idx_logs_action ON logs(action);
"""


@dataclass(slots=True)
class GroupSettings:
    chat_id: int
    title: str
    antispam_msgs: int
    antispam_seconds: int
    warn_limit: int
    mute_hours: int
    bad_words: list[str]
    trusted_domains: list[str]
    antispam_on: bool
    antilinks_on: bool
    antibadwords_on: bool
    welcome_text: str


class Database:
    """Асинхронная обёртка над SQLite.

    Соединение открывается один раз при ``connect()`` и переиспользуется
    в течение жизни процесса. ``aiosqlite`` сам гарантирует, что запросы
    сериализуются на уровне библиотеки.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path: Path = path or settings.db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        if self._conn is not None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected. Call connect() first.")
        return self._conn

    # ------------------------------------------------------------------ users
    async def upsert_user(
        self, user_id: int, username: str | None, full_name: str
    ) -> None:
        now = int(time.time())
        await self.conn.execute(
            """
            INSERT INTO users(user_id, username, full_name, first_seen, last_seen)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username  = excluded.username,
                full_name = excluded.full_name,
                last_seen = excluded.last_seen
            """,
            (user_id, username, full_name, now, now),
        )
        await self.conn.commit()

    async def get_user(self, user_id: int) -> aiosqlite.Row | None:
        cur = await self.conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        )
        return await cur.fetchone()

    # ------------------------------------------------------------ group_settings
    async def get_settings(self, chat_id: int, title: str = "") -> GroupSettings:
        cur = await self.conn.execute(
            "SELECT * FROM group_settings WHERE chat_id = ?", (chat_id,)
        )
        row = await cur.fetchone()
        if row is None:
            await self.conn.execute(
                """
                INSERT INTO group_settings(
                    chat_id, title,
                    antispam_msgs, antispam_seconds,
                    warn_limit, mute_hours,
                    bad_words, trusted_domains
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chat_id,
                    title,
                    settings.default_antispam_messages,
                    settings.default_antispam_seconds,
                    settings.default_warn_limit,
                    settings.default_mute_hours,
                    json.dumps(settings.default_bad_words, ensure_ascii=False),
                    json.dumps(settings.default_trusted_domains, ensure_ascii=False),
                ),
            )
            await self.conn.commit()
            cur = await self.conn.execute(
                "SELECT * FROM group_settings WHERE chat_id = ?", (chat_id,)
            )
            row = await cur.fetchone()
        assert row is not None
        return GroupSettings(
            chat_id=row["chat_id"],
            title=row["title"] or "",
            antispam_msgs=row["antispam_msgs"],
            antispam_seconds=row["antispam_seconds"],
            warn_limit=row["warn_limit"],
            mute_hours=row["mute_hours"],
            bad_words=json.loads(row["bad_words"] or "[]"),
            trusted_domains=json.loads(row["trusted_domains"] or "[]"),
            antispam_on=bool(row["antispam_on"]),
            antilinks_on=bool(row["antilinks_on"]),
            antibadwords_on=bool(row["antibadwords_on"]),
            welcome_text=row["welcome_text"] or "",
        )

    async def update_setting(self, chat_id: int, field: str, value: Any) -> None:
        allowed = {
            "antispam_msgs",
            "antispam_seconds",
            "warn_limit",
            "mute_hours",
            "bad_words",
            "trusted_domains",
            "antispam_on",
            "antilinks_on",
            "antibadwords_on",
            "welcome_text",
            "title",
        }
        if field not in allowed:
            raise ValueError(f"Запрещённое поле настроек: {field}")
        if field in {"bad_words", "trusted_domains"} and not isinstance(value, str):
            value = json.dumps(list(value), ensure_ascii=False)
        await self.conn.execute(
            f"UPDATE group_settings SET {field} = ? WHERE chat_id = ?",
            (value, chat_id),
        )
        await self.conn.commit()

    # -------------------------------------------------------------------- warns
    async def add_warn(
        self, chat_id: int, user_id: int, admin_id: int, reason: str
    ) -> int:
        await self.conn.execute(
            """
            INSERT INTO warns(chat_id, user_id, admin_id, reason, created)
            VALUES (?, ?, ?, ?, ?)
            """,
            (chat_id, user_id, admin_id, reason, int(time.time())),
        )
        await self.conn.commit()
        cur = await self.conn.execute(
            "SELECT COUNT(*) FROM warns WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )
        row = await cur.fetchone()
        return int(row[0]) if row else 0

    async def count_warns(self, chat_id: int, user_id: int) -> int:
        cur = await self.conn.execute(
            "SELECT COUNT(*) FROM warns WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )
        row = await cur.fetchone()
        return int(row[0]) if row else 0

    async def clear_warns(self, chat_id: int, user_id: int) -> None:
        await self.conn.execute(
            "DELETE FROM warns WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )
        await self.conn.commit()

    # --------------------------------------------------------------------- bans
    async def add_ban(
        self,
        chat_id: int,
        user_id: int,
        admin_id: int,
        kind: str,
        reason: str,
        until_ts: int | None,
    ) -> None:
        await self.conn.execute(
            """
            INSERT INTO bans(chat_id, user_id, admin_id, kind, reason, until_ts, created)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (chat_id, user_id, admin_id, kind, reason, until_ts or 0, int(time.time())),
        )
        await self.conn.commit()

    async def deactivate_bans(self, chat_id: int, user_id: int, kind: str) -> None:
        await self.conn.execute(
            """
            UPDATE bans SET active = 0
            WHERE chat_id = ? AND user_id = ? AND kind = ? AND active = 1
            """,
            (chat_id, user_id, kind),
        )
        await self.conn.commit()

    # --------------------------------------------------------------------- logs
    async def log(
        self,
        action: str,
        *,
        chat_id: int | None = None,
        user_id: int | None = None,
        admin_id: int | None = None,
        details: str = "",
    ) -> None:
        await self.conn.execute(
            """
            INSERT INTO logs(chat_id, user_id, admin_id, action, details, created)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (chat_id, user_id, admin_id, action, details, int(time.time())),
        )
        await self.conn.commit()

    async def fetch_logs(
        self, chat_id: int, limit: int = 1000
    ) -> Iterable[aiosqlite.Row]:
        cur = await self.conn.execute(
            """
            SELECT created, action, user_id, admin_id, details
            FROM logs
            WHERE chat_id = ? OR chat_id IS NULL
            ORDER BY id DESC
            LIMIT ?
            """,
            (chat_id, limit),
        )
        return await cur.fetchall()

    # -------------------------------------------------------------------- stats
    async def stats(self, chat_id: int) -> dict[str, int]:
        async def _scalar(query: str, args: tuple = ()) -> int:
            cur = await self.conn.execute(query, args)
            row = await cur.fetchone()
            return int(row[0]) if row else 0

        return {
            "warns": await _scalar(
                "SELECT COUNT(*) FROM warns WHERE chat_id = ?", (chat_id,)
            ),
            "bans": await _scalar(
                "SELECT COUNT(*) FROM bans WHERE chat_id = ? AND kind = 'ban'",
                (chat_id,),
            ),
            "mutes": await _scalar(
                "SELECT COUNT(*) FROM bans WHERE chat_id = ? AND kind = 'mute'",
                (chat_id,),
            ),
            "violations": await _scalar(
                "SELECT COUNT(*) FROM logs WHERE chat_id = ? AND action LIKE 'violation%'",
                (chat_id,),
            ),
        }


db = Database()
