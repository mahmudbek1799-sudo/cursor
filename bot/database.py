"""Слой работы с базой данных SQLite.

Реализован полностью на стандартной библиотеке ``sqlite3`` (без
сторонних ORM). Все SQL-запросы выполняются параметризованно, что
исключает возможность SQL-инъекций. Соединение с БД создаётся при
каждой операции и сразу закрывается, что упрощает многопоточную
работу telebot и снимает нагрузку с пула.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, List, Optional, Sequence

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


# ---------------------------------------------------------------------------
# DTO-модели
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class Order:
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
class Product:
    id: int
    sku: str
    title: str
    category: str
    price: float
    stock: int
    description: str
    is_active: int
    updated_at: str


@dataclass(slots=True)
class Discount:
    id: int
    product_id: Optional[int]
    kind: str
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


@dataclass(slots=True)
class BlockedUser:
    user_id: int
    reason: str
    blocked_at: str


def apply_discount(price: float, discount: Optional[Discount]) -> float:
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


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
class Database:
    """Высокоуровневая обёртка над SQLite-соединением.

    Все запросы параметризованы. Класс потокобезопасен: используется
    блокировка ``threading.RLock`` и режим ``check_same_thread=False``,
    что важно для telebot (polling-поток + фоновая синхронизация).
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        if not self._db_path.is_absolute():
            self._db_path = ROOT_DIR / self._db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    @property
    def path(self) -> Path:
        return self._db_path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            conn = sqlite3.connect(
                self._db_path,
                detect_types=sqlite3.PARSE_DECLTYPES,
                check_same_thread=False,
            )
            try:
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON;")
                yield conn
            finally:
                conn.close()

    def init_schema(self) -> None:
        """Создать таблицы и индексы, если они ещё не существуют."""

        with self.connect() as conn:
            conn.executescript(
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
                CREATE INDEX IF NOT EXISTS idx_orders_created_at
                    ON orders(created_at);

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
            self._safe_add_column(conn, "products",
                                  "description", "TEXT NOT NULL DEFAULT ''")
            self._safe_add_column(conn, "products",
                                  "is_active", "INTEGER NOT NULL DEFAULT 1")
            conn.commit()
        logger.info("Схема БД инициализирована (%s)", self._db_path)

    @staticmethod
    def _safe_add_column(conn: sqlite3.Connection, table: str,
                         column: str, ddl: str) -> None:
        cur = conn.execute(f"PRAGMA table_info({table})")
        existing = {row["name"] for row in cur.fetchall()}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    # ------------------------------------------------------------------
    # Заказы
    # ------------------------------------------------------------------
    def upsert_order(self, data: dict) -> bool:
        """Создать или обновить заказ по ``external_id``.

        Возвращает ``True``, если был создан новый заказ.
        """

        with self.connect() as conn:
            row = conn.execute(
                "SELECT id FROM orders WHERE external_id = ?",
                (str(data["external_id"]),),
            ).fetchone()
            if row is None:
                conn.execute(
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
                conn.commit()
                return True
            conn.execute(
                """
                UPDATE orders SET
                    customer_name = ?,
                    customer_phone = ?,
                    customer_telegram_id =
                        COALESCE(?, customer_telegram_id),
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
            conn.commit()
            return False

    def list_orders(
        self,
        statuses: Optional[Sequence[str]] = None,
        limit: int = 20,
        offset: int = 0,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Order]:
        query = "SELECT * FROM orders WHERE 1=1"
        params: list = []
        if statuses:
            placeholders = ",".join(["?"] * len(statuses))
            query += f" AND status IN ({placeholders})"
            params.extend(statuses)
        if date_from:
            query += " AND date(created_at) >= ?"
            params.append(date_from)
        if date_to:
            query += " AND date(created_at) <= ?"
            params.append(date_to)
        query += " ORDER BY datetime(created_at) DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [Order(**dict(row)) for row in rows]

    def get_order(self, order_id: int) -> Optional[Order]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM orders WHERE id = ?",
                (order_id,),
            ).fetchone()
        return Order(**dict(row)) if row else None

    def set_order_status(self, order_id: int, status: str) -> bool:
        if status not in ORDER_STATUSES:
            raise ValueError(f"Недопустимый статус заказа: {status}")
        with self.connect() as conn:
            cur = conn.execute(
                """
                UPDATE orders SET status = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (status, order_id),
            )
            conn.commit()
            return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Аналитика
    # ------------------------------------------------------------------
    def stats_summary(self) -> dict:
        today = datetime.now().date()
        week_start = (today - timedelta(days=6)).isoformat()
        month_start = (today - timedelta(days=29)).isoformat()

        def _scalar(conn: sqlite3.Connection, q: str, p: tuple = ()) -> float:
            row = conn.execute(q, p).fetchone()
            return float(row[0] or 0) if row else 0.0

        with self.connect() as conn:
            total = int(_scalar(conn, "SELECT COUNT(*) FROM orders"))
            new_count = int(_scalar(
                conn, "SELECT COUNT(*) FROM orders WHERE status='new'"))
            completed = int(_scalar(
                conn, "SELECT COUNT(*) FROM orders WHERE status='completed'"))
            cancelled = int(_scalar(
                conn, "SELECT COUNT(*) FROM orders WHERE status='cancelled'"))
            today_count = int(_scalar(
                conn,
                "SELECT COUNT(*) FROM orders WHERE date(created_at)=?",
                (today.isoformat(),)))
            week_count = int(_scalar(
                conn,
                "SELECT COUNT(*) FROM orders WHERE date(created_at)>=?",
                (week_start,)))
            month_count = int(_scalar(
                conn,
                "SELECT COUNT(*) FROM orders WHERE date(created_at)>=?",
                (month_start,)))
            revenue_today = _scalar(
                conn,
                "SELECT COALESCE(SUM(total),0) FROM orders "
                "WHERE date(created_at)=? AND status='completed'",
                (today.isoformat(),))
            revenue_week = _scalar(
                conn,
                "SELECT COALESCE(SUM(total),0) FROM orders "
                "WHERE date(created_at)>=? AND status='completed'",
                (week_start,))
        return {
            "total": total, "new": new_count,
            "completed": completed, "cancelled": cancelled,
            "today": today_count, "week": week_count,
            "month": month_count,
            "revenue_today": revenue_today,
            "revenue_week": revenue_week,
        }

    def orders_per_day(self, days: int = 7) -> list[tuple[str, int]]:
        start = (datetime.now().date()
                 - timedelta(days=days - 1)).isoformat()
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT date(created_at) AS day, COUNT(*) AS cnt
                FROM orders
                WHERE date(created_at) >= ?
                GROUP BY day ORDER BY day
                """,
                (start,),
            ).fetchall()
        return [(r["day"], int(r["cnt"])) for r in rows]

    # ------------------------------------------------------------------
    # Клиенты и блокировки
    # ------------------------------------------------------------------
    def upsert_client(self, telegram_id: int,
                      full_name: Optional[str] = None,
                      phone: Optional[str] = None,
                      username: Optional[str] = None) -> None:
        with self.connect() as conn:
            conn.execute(
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
            conn.commit()

    def list_client_ids(self) -> List[int]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT telegram_id FROM clients
                WHERE telegram_id NOT IN
                    (SELECT user_id FROM blocked_users)
                """
            ).fetchall()
        return [int(r["telegram_id"]) for r in rows]

    def block_user(self, user_id: int, reason: str = "") -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO blocked_users (user_id, reason)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET reason = excluded.reason
                """,
                (user_id, reason),
            )
            conn.commit()

    def unblock_user(self, user_id: int) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                "DELETE FROM blocked_users WHERE user_id = ?",
                (user_id,),
            )
            conn.commit()
            return cur.rowcount > 0

    def is_blocked(self, user_id: int) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM blocked_users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return row is not None

    def list_blocked(self) -> List[BlockedUser]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM blocked_users ORDER BY blocked_at DESC"
            ).fetchall()
        return [BlockedUser(**dict(r)) for r in rows]

    # ------------------------------------------------------------------
    # Журнал
    # ------------------------------------------------------------------
    def log_action(self, admin_id: int, action: str,
                   target: str = "", payload: str = "") -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO admin_actions
                    (admin_id, action, target, payload)
                VALUES (?, ?, ?, ?)
                """,
                (admin_id, action, target, payload),
            )
            conn.commit()

    def recent_actions(self, limit: int = 20) -> List[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT admin_id, action, target, payload, created_at
                FROM admin_actions ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Каталог товаров
    # ------------------------------------------------------------------
    def upsert_product(self, product: dict) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id FROM products WHERE sku = ?",
                (str(product["sku"]),),
            ).fetchone()
            is_new = row is None
            conn.execute(
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
            conn.commit()
            return is_new

    def get_product(self, product_id: int) -> Optional[Product]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM products WHERE id = ?",
                (product_id,),
            ).fetchone()
        return Product(**dict(row)) if row else None

    def get_product_by_sku(self, sku: str) -> Optional[Product]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM products WHERE sku = ?",
                (sku,),
            ).fetchone()
        return Product(**dict(row)) if row else None

    def list_products(
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
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [Product(**dict(r)) for r in rows]

    def count_products(self, category: Optional[str] = None,
                       only_active: bool = False) -> int:
        query = "SELECT COUNT(*) AS cnt FROM products WHERE 1=1"
        params: list = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if only_active:
            query += " AND is_active = 1"
        with self.connect() as conn:
            row = conn.execute(query, params).fetchone()
        return int(row["cnt"]) if row else 0

    def list_categories(self) -> List[str]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT category FROM products ORDER BY category"
            ).fetchall()
        return [r["category"] for r in rows]

    def update_product_price(self, product_id: int,
                             new_price: float) -> bool:
        if new_price < 0:
            raise ValueError("Цена не может быть отрицательной")
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE products SET price = ?, updated_at = datetime('now') "
                "WHERE id = ?",
                (float(new_price), product_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def update_product_stock(self, product_id: int, new_stock: int) -> bool:
        if new_stock < 0:
            raise ValueError("Остаток не может быть отрицательным")
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE products SET stock = ?, updated_at = datetime('now') "
                "WHERE id = ?",
                (int(new_stock), product_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def set_product_active(self, product_id: int, is_active: bool) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE products SET is_active = ?, "
                "updated_at = datetime('now') WHERE id = ?",
                (1 if is_active else 0, product_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def delete_product(self, product_id: int) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                "DELETE FROM products WHERE id = ?",
                (product_id,),
            )
            conn.commit()
            return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Скидки
    # ------------------------------------------------------------------
    def add_discount(self, kind: str, value: float,
                     product_id: Optional[int] = None,
                     valid_from: Optional[str] = None,
                     valid_to: Optional[str] = None) -> int:
        if kind not in ("percent", "fixed"):
            raise ValueError("kind должен быть 'percent' или 'fixed'")
        if value <= 0:
            raise ValueError("Значение скидки должно быть положительным")
        if kind == "percent" and value > 100:
            raise ValueError("Процентная скидка не может быть больше 100")
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO discounts
                    (product_id, kind, value, valid_from, valid_to, active)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (product_id, kind, float(value), valid_from, valid_to),
            )
            conn.commit()
            return int(cur.lastrowid)

    def deactivate_discount(self, discount_id: int) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE discounts SET active = 0 WHERE id = ?",
                (discount_id,),
            )
            conn.commit()
            return cur.rowcount > 0

    def list_discounts(self, only_active: bool = True) -> List[Discount]:
        query = "SELECT * FROM discounts"
        if only_active:
            query += (
                " WHERE active = 1 AND "
                "(valid_to IS NULL OR valid_to >= datetime('now'))"
            )
        query += " ORDER BY id DESC"
        with self.connect() as conn:
            rows = conn.execute(query).fetchall()
        return [Discount(**dict(r)) for r in rows]

    def get_active_discount_for_product(
            self, product_id: int) -> Optional[Discount]:
        """Вернуть лучшую активную скидку (минимальная итоговая цена)."""

        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM discounts
                WHERE active = 1
                  AND (valid_from IS NULL
                       OR valid_from <= datetime('now'))
                  AND (valid_to   IS NULL
                       OR valid_to   >= datetime('now'))
                  AND (product_id = ? OR product_id IS NULL)
                """,
                (product_id,),
            ).fetchall()
        if not rows:
            return None
        product = self.get_product(product_id)
        if product is None:
            return Discount(**dict(rows[0]))
        best: Optional[Discount] = None
        best_price = product.price
        for r in rows:
            d = Discount(**dict(r))
            new_price = apply_discount(product.price, d)
            if new_price < best_price:
                best, best_price = d, new_price
        return best or Discount(**dict(rows[0]))


_db: Optional[Database] = None


def get_db() -> Database:
    """Получить глобальный экземпляр :class:`Database`."""

    global _db
    if _db is None:
        _db = Database(settings.db_path)
    return _db
