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


@dataclass(slots=True)
class Product:
    """DTO товара мебельного магазина."""

    id: int
    sku: str
    title: str
    category: str
    price: float
    stock: int
    description: str
    is_active: int
    updated_at: str

    @property
    def in_stock(self) -> bool:
        return bool(self.is_active) and self.stock > 0


@dataclass(slots=True)
class Discount:
    """DTO скидки. ``product_id is None`` означает глобальную скидку."""

    id: int
    product_id: Optional[int]
    kind: str       # 'percent' | 'fixed'
    value: float
    valid_from: Optional[str]
    valid_to: Optional[str]
    active: int
    created_at: str

    @property
    def label(self) -> str:
        if self.kind == "percent":
            return f"-{self.value:g}%"
        return f"-{self.value:,.0f} ₽".replace(",", " ")


def apply_discount(price: float, discount: Optional["Discount"]) -> float:
    """Применить скидку к цене (процентную или фиксированную).

    Никогда не возвращает отрицательное значение: если фиксированная
    скидка больше цены — возвращается 0.
    """

    if discount is None:
        return round(price, 2)
    if discount.kind == "percent":
        result = price * (1 - float(discount.value) / 100.0)
    elif discount.kind == "fixed":
        result = price - float(discount.value)
    else:
        result = price
    return round(max(0.0, result), 2)


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
                    description TEXT NOT NULL DEFAULT '',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_products_category
                    ON products(category);

                CREATE TABLE IF NOT EXISTS discounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    kind TEXT NOT NULL CHECK(kind IN ('percent', 'fixed')),
                    value REAL NOT NULL,
                    valid_from TEXT,
                    valid_to TEXT,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (product_id) REFERENCES products(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_discounts_product_id
                    ON discounts(product_id);
                CREATE INDEX IF NOT EXISTS idx_discounts_active
                    ON discounts(active);
                """
            )
            # Совместимость со старыми схемами: добавим недостающие поля.
            await self._safe_add_column(conn, "products",
                                        "description", "TEXT NOT NULL DEFAULT ''")
            await self._safe_add_column(conn, "products",
                                        "is_active", "INTEGER NOT NULL DEFAULT 1")
            await conn.commit()
        logger.info("Схема БД успешно инициализирована (%s)", self._db_path)

    @staticmethod
    async def _safe_add_column(conn: aiosqlite.Connection,
                               table: str, column: str, ddl: str) -> None:
        """Добавить колонку, если она ещё не существует."""

        cur = await conn.execute(f"PRAGMA table_info({table})")
        existing = {row["name"] for row in await cur.fetchall()}
        if column not in existing:
            await conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

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
    # Каталог товаров
    # ------------------------------------------------------------------
    async def upsert_product(self, product: dict) -> bool:
        """Создать или обновить товар по ``sku``.

        Возвращает ``True``, если запись была создана впервые.
        """

        async with self.connect() as conn:
            cur = await conn.execute(
                "SELECT id FROM products WHERE sku = ?",
                (str(product["sku"]),),
            )
            row = await cur.fetchone()
            is_new = row is None
            await conn.execute(
                """
                INSERT INTO products (sku, title, category, price, stock,
                                      description, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(sku) DO UPDATE SET
                    title = excluded.title,
                    category = excluded.category,
                    price = excluded.price,
                    stock = excluded.stock,
                    description = excluded.description,
                    is_active = excluded.is_active,
                    updated_at = datetime('now')
                """,
                (
                    str(product["sku"]),
                    product.get("title", ""),
                    product.get("category", "other"),
                    float(product.get("price", 0) or 0),
                    int(product.get("stock", 0) or 0),
                    product.get("description", ""),
                    int(product.get("is_active", 1)),
                ),
            )
            await conn.commit()
            return is_new

    async def get_product(self, product_id: int) -> Optional[Product]:
        async with self.connect() as conn:
            cur = await conn.execute(
                "SELECT * FROM products WHERE id = ?",
                (product_id,),
            )
            row = await cur.fetchone()
        return Product(**dict(row)) if row else None

    async def get_product_by_sku(self, sku: str) -> Optional[Product]:
        async with self.connect() as conn:
            cur = await conn.execute(
                "SELECT * FROM products WHERE sku = ?",
                (sku,),
            )
            row = await cur.fetchone()
        return Product(**dict(row)) if row else None

    async def list_products(
        self,
        category: Optional[str] = None,
        only_active: bool = False,
        limit: int = 30,
        offset: int = 0,
    ) -> List[Product]:
        query = "SELECT * FROM products WHERE 1=1"
        params: list = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if only_active:
            query += " AND is_active = 1"
        query += " ORDER BY category, title LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        async with self.connect() as conn:
            cur = await conn.execute(query, params)
            rows = await cur.fetchall()
        return [Product(**dict(r)) for r in rows]

    async def count_products(self, category: Optional[str] = None,
                             only_active: bool = False) -> int:
        query = "SELECT COUNT(*) AS cnt FROM products WHERE 1=1"
        params: list = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if only_active:
            query += " AND is_active = 1"
        async with self.connect() as conn:
            cur = await conn.execute(query, params)
            row = await cur.fetchone()
        return int(row["cnt"]) if row else 0

    async def list_categories(self) -> List[str]:
        async with self.connect() as conn:
            cur = await conn.execute(
                "SELECT DISTINCT category FROM products ORDER BY category"
            )
            rows = await cur.fetchall()
        return [r["category"] for r in rows]

    async def update_product_price(self, product_id: int, new_price: float) -> bool:
        if new_price < 0:
            raise ValueError("Цена не может быть отрицательной")
        async with self.connect() as conn:
            cur = await conn.execute(
                """
                UPDATE products SET price = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (float(new_price), product_id),
            )
            await conn.commit()
            return cur.rowcount > 0

    async def update_product_stock(self, product_id: int, new_stock: int) -> bool:
        if new_stock < 0:
            raise ValueError("Остаток не может быть отрицательным")
        async with self.connect() as conn:
            cur = await conn.execute(
                """
                UPDATE products SET stock = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (int(new_stock), product_id),
            )
            await conn.commit()
            return cur.rowcount > 0

    async def set_product_active(self, product_id: int, is_active: bool) -> bool:
        async with self.connect() as conn:
            cur = await conn.execute(
                """
                UPDATE products SET is_active = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (1 if is_active else 0, product_id),
            )
            await conn.commit()
            return cur.rowcount > 0

    async def delete_product(self, product_id: int) -> bool:
        async with self.connect() as conn:
            cur = await conn.execute(
                "DELETE FROM products WHERE id = ?",
                (product_id,),
            )
            await conn.commit()
            return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Скидки
    # ------------------------------------------------------------------
    async def add_discount(
        self,
        kind: str,
        value: float,
        product_id: Optional[int] = None,
        valid_from: Optional[str] = None,
        valid_to: Optional[str] = None,
    ) -> int:
        if kind not in ("percent", "fixed"):
            raise ValueError("kind должен быть 'percent' или 'fixed'")
        if value <= 0:
            raise ValueError("Значение скидки должно быть положительным")
        if kind == "percent" and value > 100:
            raise ValueError("Процентная скидка не может быть больше 100")
        async with self.connect() as conn:
            cur = await conn.execute(
                """
                INSERT INTO discounts
                    (product_id, kind, value, valid_from, valid_to, active)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (product_id, kind, float(value), valid_from, valid_to),
            )
            await conn.commit()
            return int(cur.lastrowid)

    async def deactivate_discount(self, discount_id: int) -> bool:
        async with self.connect() as conn:
            cur = await conn.execute(
                "UPDATE discounts SET active = 0 WHERE id = ?",
                (discount_id,),
            )
            await conn.commit()
            return cur.rowcount > 0

    async def list_discounts(self, only_active: bool = True) -> List[Discount]:
        query = "SELECT * FROM discounts"
        if only_active:
            query += (
                " WHERE active = 1 AND (valid_to IS NULL OR valid_to >= datetime('now'))"
            )
        query += " ORDER BY id DESC"
        async with self.connect() as conn:
            cur = await conn.execute(query)
            rows = await cur.fetchall()
        return [Discount(**dict(r)) for r in rows]

    async def get_active_discount_for_product(
        self, product_id: int
    ) -> Optional[Discount]:
        """Вернёт лучшую активную скидку: персональную или глобальную.

        Если для товара есть несколько активных скидок, выбирается та, что
        даёт наибольшее снижение цены.
        """

        async with self.connect() as conn:
            cur = await conn.execute(
                """
                SELECT * FROM discounts
                WHERE active = 1
                  AND (valid_from IS NULL OR valid_from <= datetime('now'))
                  AND (valid_to   IS NULL OR valid_to   >= datetime('now'))
                  AND (product_id = ? OR product_id IS NULL)
                """,
                (product_id,),
            )
            rows = await cur.fetchall()
        if not rows:
            return None
        product = await self.get_product(product_id)
        if product is None:
            return Discount(**dict(rows[0]))
        best: Optional[Discount] = None
        best_price = product.price
        for r in rows:
            d = Discount(**dict(r))
            new_price = apply_discount(product.price, d)
            if new_price < best_price:
                best_price = new_price
                best = d
        return best or Discount(**dict(rows[0]))


_db: Optional[Database] = None


def get_db() -> Database:
    """Получить глобальный экземпляр :class:`Database`."""

    global _db
    if _db is None:
        _db = Database(settings.db_path)
    return _db
