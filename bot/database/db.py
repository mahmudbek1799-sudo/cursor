"""Асинхронный слой доступа к данным.

Используется библиотека ``aiosqlite``. Все SQL-запросы выполняются через
параметризованные команды, что исключает возможность SQL-инъекций.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import AsyncIterator, List, Optional, Sequence

import aiosqlite

from bot.config import ROOT_DIR, settings

logger = logging.getLogger(__name__)


ORDER_STATUSES: tuple[str, ...] = (
    "new",
    "confirmed",
    "in_delivery",
    "completed",
    "cancelled",
)

STATUS_LABELS: dict[str, str] = {
    "new": "Новый",
    "confirmed": "Подтверждён",
    "in_delivery": "В доставке",
    "completed": "Завершён",
    "cancelled": "Отменён",
}


@dataclass(slots=True)
class Order:
    """DTO-модель заказа, удобная для использования в обработчиках бота."""

    id: int
    external_id: str
    customer_name: str
    customer_phone: str
    customer_telegram_id: Optional[int]
    address: str
    items: str
    total: float
    status: str
    comment: str
    created_at: str
    updated_at: str

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status)


@dataclass(slots=True)
class BlockedUser:
    user_id: int
    reason: str
    blocked_at: str


class Database:
    """Высокоуровневая обёртка над SQLite-соединением.

    Хранит путь к файлу БД, инкапсулирует все типовые операции и
    обеспечивает создание схемы при первом запуске.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        if not self._db_path.is_absolute():
            self._db_path = ROOT_DIR / self._db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._db_path

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[aiosqlite.Connection]:
        """Асинхронный контекстный менеджер для одного соединения.

        Гарантирует, что соединение закрывается в любой ситуации,
        и устанавливает row_factory + включает поддержку внешних ключей.
        """

        conn = await aiosqlite.connect(self._db_path)
        try:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON;")
            yield conn
        finally:
            await conn.close()

    async def init_schema(self) -> None:
        """Создать таблицы и индексы, если они ещё не существуют."""

        async with self.connect() as conn:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    external_id TEXT NOT NULL UNIQUE,
                    customer_name TEXT NOT NULL,
                    customer_phone TEXT NOT NULL,
                    customer_telegram_id INTEGER,
                    address TEXT NOT NULL,
                    items TEXT NOT NULL,
                    total REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'new',
                    comment TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
                CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

                CREATE TABLE IF NOT EXISTS clients (
                    telegram_id INTEGER PRIMARY KEY,
                    full_name TEXT,
                    phone TEXT,
                    username TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS blocked_users (
                    user_id INTEGER PRIMARY KEY,
                    reason TEXT NOT NULL DEFAULT '',
                    blocked_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS admin_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL DEFAULT '',
                    payload TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_admin_actions_admin_id
                    ON admin_actions(admin_id);

                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sku TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'other',
                    price REAL NOT NULL DEFAULT 0,
                    stock INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                """
            )
            await conn.commit()
        logger.info("Схема БД успешно инициализирована (%s)", self._db_path)

    # ------------------------------------------------------------------
    # Заказы
    # ------------------------------------------------------------------
    async def upsert_order(self, data: dict) -> bool:
        """Создать или обновить заказ по ``external_id``.

        Возвращает ``True``, если был создан новый заказ (для уведомления
        администратора), и ``False`` — если обновлён существующий.
        """

        async with self.connect() as conn:
            cur = await conn.execute(
                "SELECT id, status FROM orders WHERE external_id = ?",
                (str(data["external_id"]),),
            )
            row = await cur.fetchone()
            if row is None:
                await conn.execute(
                    """
                    INSERT INTO orders (
                        external_id, customer_name, customer_phone,
                        customer_telegram_id, address, items, total,
                        status, comment
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(data["external_id"]),
                        data.get("customer_name", ""),
                        data.get("customer_phone", ""),
                        data.get("customer_telegram_id"),
                        data.get("address", ""),
                        data.get("items", ""),
                        float(data.get("total", 0) or 0),
                        data.get("status", "new"),
                        data.get("comment", ""),
                    ),
                )
                await conn.commit()
                return True
            await conn.execute(
                """
                UPDATE orders SET
                    customer_name = ?,
                    customer_phone = ?,
                    customer_telegram_id = COALESCE(?, customer_telegram_id),
                    address = ?,
                    items = ?,
                    total = ?,
                    comment = ?,
                    updated_at = datetime('now')
                WHERE external_id = ?
                """,
                (
                    data.get("customer_name", ""),
                    data.get("customer_phone", ""),
                    data.get("customer_telegram_id"),
                    data.get("address", ""),
                    data.get("items", ""),
                    float(data.get("total", 0) or 0),
                    data.get("comment", ""),
                    str(data["external_id"]),
                ),
            )
            await conn.commit()
            return False

    async def list_orders(
        self,
        statuses: Optional[Sequence[str]] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Order]:
        query = "SELECT * FROM orders"
        params: list = []
        if statuses:
            placeholders = ",".join(["?"] * len(statuses))
            query += f" WHERE status IN ({placeholders})"
            params.extend(statuses)
        query += " ORDER BY datetime(created_at) DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        async with self.connect() as conn:
            cur = await conn.execute(query, params)
            rows = await cur.fetchall()
        return [Order(**dict(row)) for row in rows]

    async def get_order(self, order_id: int) -> Optional[Order]:
        async with self.connect() as conn:
            cur = await conn.execute(
                "SELECT * FROM orders WHERE id = ?",
                (order_id,),
            )
            row = await cur.fetchone()
        return Order(**dict(row)) if row else None

    async def set_order_status(self, order_id: int, status: str) -> bool:
        if status not in ORDER_STATUSES:
            raise ValueError(f"Недопустимый статус заказа: {status}")
        async with self.connect() as conn:
            cur = await conn.execute(
                """
                UPDATE orders SET status = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (status, order_id),
            )
            await conn.commit()
            return cur.rowcount > 0

    async def set_order_comment(self, order_id: int, comment: str) -> bool:
        async with self.connect() as conn:
            cur = await conn.execute(
                """
                UPDATE orders SET comment = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (comment, order_id),
            )
            await conn.commit()
            return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Аналитика
    # ------------------------------------------------------------------
    async def stats_summary(self) -> dict:
        """Сводная статистика для команды ``/stats``."""

        today = datetime.now().date()
        week_start = (today - timedelta(days=6)).isoformat()
        month_start = (today - timedelta(days=29)).isoformat()

        async with self.connect() as conn:
            async def _scalar(query: str, params: tuple = ()) -> float:
                cur = await conn.execute(query, params)
                row = await cur.fetchone()
                return float(row[0] or 0) if row else 0.0

            total = int(await _scalar("SELECT COUNT(*) FROM orders"))
            new_count = int(
                await _scalar(
                    "SELECT COUNT(*) FROM orders WHERE status = 'new'"
                )
            )
            completed = int(
                await _scalar(
                    "SELECT COUNT(*) FROM orders WHERE status = 'completed'"
                )
            )
            cancelled = int(
                await _scalar(
                    "SELECT COUNT(*) FROM orders WHERE status = 'cancelled'"
                )
            )
            today_count = int(
                await _scalar(
                    "SELECT COUNT(*) FROM orders WHERE date(created_at) = ?",
                    (today.isoformat(),),
                )
            )
            week_count = int(
                await _scalar(
                    "SELECT COUNT(*) FROM orders WHERE date(created_at) >= ?",
                    (week_start,),
                )
            )
            month_count = int(
                await _scalar(
                    "SELECT COUNT(*) FROM orders WHERE date(created_at) >= ?",
                    (month_start,),
                )
            )
            revenue_today = await _scalar(
                """
                SELECT COALESCE(SUM(total), 0) FROM orders
                WHERE date(created_at) = ? AND status = 'completed'
                """,
                (today.isoformat(),),
            )
            revenue_week = await _scalar(
                """
                SELECT COALESCE(SUM(total), 0) FROM orders
                WHERE date(created_at) >= ? AND status = 'completed'
                """,
                (week_start,),
            )

        return {
            "total": total,
            "new": new_count,
            "completed": completed,
            "cancelled": cancelled,
            "today": today_count,
            "week": week_count,
            "month": month_count,
            "revenue_today": revenue_today,
            "revenue_week": revenue_week,
        }

    async def orders_per_day(self, days: int = 7) -> list[tuple[str, int]]:
        """Список пар (дата, число заказов) для графика дашборда."""

        start = (datetime.now().date() - timedelta(days=days - 1)).isoformat()
        async with self.connect() as conn:
            cur = await conn.execute(
                """
                SELECT date(created_at) AS day, COUNT(*) AS cnt
                FROM orders
                WHERE date(created_at) >= ?
                GROUP BY day
                ORDER BY day
                """,
                (start,),
            )
            rows = await cur.fetchall()
        return [(row["day"], int(row["cnt"])) for row in rows]

    # ------------------------------------------------------------------
    # Клиенты и блокировки
    # ------------------------------------------------------------------
    async def upsert_client(
        self,
        telegram_id: int,
        full_name: Optional[str] = None,
        phone: Optional[str] = None,
        username: Optional[str] = None,
    ) -> None:
        async with self.connect() as conn:
            await conn.execute(
                """
                INSERT INTO clients (telegram_id, full_name, phone, username)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    full_name = COALESCE(excluded.full_name, full_name),
                    phone     = COALESCE(excluded.phone, phone),
                    username  = COALESCE(excluded.username, username)
                """,
                (telegram_id, full_name, phone, username),
            )
            await conn.commit()

    async def list_client_ids(self) -> List[int]:
        async with self.connect() as conn:
            cur = await conn.execute(
                """
                SELECT telegram_id FROM clients
                WHERE telegram_id NOT IN (SELECT user_id FROM blocked_users)
                """
            )
            rows = await cur.fetchall()
        return [int(r["telegram_id"]) for r in rows]

    async def block_user(self, user_id: int, reason: str = "") -> None:
        async with self.connect() as conn:
            await conn.execute(
                """
                INSERT INTO blocked_users (user_id, reason)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET reason = excluded.reason
                """,
                (user_id, reason),
            )
            await conn.commit()

    async def unblock_user(self, user_id: int) -> bool:
        async with self.connect() as conn:
            cur = await conn.execute(
                "DELETE FROM blocked_users WHERE user_id = ?", (user_id,)
            )
            await conn.commit()
            return cur.rowcount > 0

    async def is_blocked(self, user_id: int) -> bool:
        async with self.connect() as conn:
            cur = await conn.execute(
                "SELECT 1 FROM blocked_users WHERE user_id = ?", (user_id,)
            )
            row = await cur.fetchone()
        return row is not None

    async def list_blocked(self) -> List[BlockedUser]:
        async with self.connect() as conn:
            cur = await conn.execute(
                "SELECT * FROM blocked_users ORDER BY blocked_at DESC"
            )
            rows = await cur.fetchall()
        return [BlockedUser(**dict(r)) for r in rows]

    # ------------------------------------------------------------------
    # Журнал действий администратора
    # ------------------------------------------------------------------
    async def log_action(
        self,
        admin_id: int,
        action: str,
        target: str = "",
        payload: str = "",
    ) -> None:
        async with self.connect() as conn:
            await conn.execute(
                """
                INSERT INTO admin_actions (admin_id, action, target, payload)
                VALUES (?, ?, ?, ?)
                """,
                (admin_id, action, target, payload),
            )
            await conn.commit()

    async def recent_actions(self, limit: int = 20) -> List[dict]:
        async with self.connect() as conn:
            cur = await conn.execute(
                """
                SELECT admin_id, action, target, payload, created_at
                FROM admin_actions
                ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            )
            rows = await cur.fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Каталог товаров (используется при синхронизации с сайтом магазина)
    # ------------------------------------------------------------------
    async def upsert_product(self, product: dict) -> None:
        async with self.connect() as conn:
            await conn.execute(
                """
                INSERT INTO products (sku, title, category, price, stock)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(sku) DO UPDATE SET
                    title = excluded.title,
                    category = excluded.category,
                    price = excluded.price,
                    stock = excluded.stock,
                    updated_at = datetime('now')
                """,
                (
                    str(product["sku"]),
                    product.get("title", ""),
                    product.get("category", "other"),
                    float(product.get("price", 0) or 0),
                    int(product.get("stock", 0) or 0),
                ),
            )
            await conn.commit()


_db: Optional[Database] = None


def get_db() -> Database:
    """Получить глобальный экземпляр :class:`Database`."""

    global _db
    if _db is None:
        _db = Database(settings.db_path)
    return _db
