"""Вспомогательные функции: контроль доступа, логирование, форматирование."""

from __future__ import annotations

import functools
import logging
import logging.handlers
from html import escape
from typing import Callable

from telebot import TeleBot
from telebot.types import CallbackQuery, Message

from bot.config import ROOT_DIR, settings
from bot.database import Discount, Order, Product, apply_discount

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Логирование
# ---------------------------------------------------------------------------
def setup_logging(level: str = "INFO") -> None:
    """Унифицированная настройка логирования (консоль + ротация файла)."""

    log_dir = ROOT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "bot.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(file_handler)


# ---------------------------------------------------------------------------
# Контроль доступа администратора
# ---------------------------------------------------------------------------
def admin_only(handler: Callable) -> Callable:
    """Декоратор для хендлеров telebot, который пропускает только админов.

    Реализует принцип «по умолчанию запрещено». Любая попытка доступа
    со стороны пользователя, не входящего в ADMIN_IDS, фиксируется в
    журнале admin_actions, а пользователю отправляется сообщение об
    отказе. Применяется как обычный декоратор Python.
    """

    from bot.database import get_db  # локальный импорт для избежания циклов

    @functools.wraps(handler)
    def wrapper(message_or_callback, *args, **kwargs):
        user = getattr(message_or_callback, "from_user", None)
        user_id = user.id if user else 0
        if not settings.is_admin(user_id):
            logger.warning(
                "Запрещённый доступ: user_id=%s, hander=%s",
                user_id, handler.__name__,
            )
            db = get_db()
            db.log_action(
                admin_id=user_id, action="access_denied",
                target=handler.__name__,
            )
            bot: TeleBot = kwargs.get("bot") or args[0] \
                if (args or kwargs.get("bot")) else None
            try:
                if isinstance(message_or_callback, Message):
                    if bot is not None:
                        bot.reply_to(
                            message_or_callback,
                            "⛔ Доступ закрыт. Этот бот предназначен только "
                            "для администраторов магазина.",
                        )
                elif isinstance(message_or_callback, CallbackQuery):
                    if bot is not None:
                        bot.answer_callback_query(
                            message_or_callback.id,
                            "Доступ запрещён", show_alert=True,
                        )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Не удалось ответить об отказе: %s", exc)
            return None
        return handler(message_or_callback, *args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# Форматирование
# ---------------------------------------------------------------------------
def format_money(value: float) -> str:
    return f"{value:,.2f} ₽".replace(",", " ")


def format_order_card(order: Order) -> str:
    comment = order.comment or "—"
    tg_id = order.customer_telegram_id or "—"
    return (
        f"<b>Заказ №{order.id}</b> "
        f"(внешний: <code>{escape(order.external_id)}</code>)\n"
        f"Статус: <b>{escape(order.status_label)}</b>\n"
        f"Создан: {escape(order.created_at)}\n"
        f"Обновлён: {escape(order.updated_at)}\n\n"
        f"<b>Клиент:</b> {escape(order.customer_name)}\n"
        f"<b>Телефон:</b> <code>{escape(order.customer_phone)}</code>\n"
        f"<b>Telegram ID:</b> <code>{tg_id}</code>\n"
        f"<b>Адрес:</b> {escape(order.address)}\n\n"
        f"<b>Состав заказа:</b>\n{escape(order.items)}\n\n"
        f"<b>Сумма:</b> {format_money(order.total)}\n"
        f"<b>Комментарий:</b> {escape(comment)}"
    )


def format_product_card(product: Product,
                        discount: Discount | None = None) -> str:
    final = apply_discount(product.price, discount)
    lines = [
        f"<b>{escape(product.title)}</b>",
        f"Артикул: <code>{escape(product.sku)}</code>",
        f"Категория: {escape(product.category)}",
        "",
    ]
    if discount and final < product.price:
        lines.append(
            f"Цена: <s>{format_money(product.price)}</s> → "
            f"<b>{format_money(final)}</b>  "
            f"({escape(discount.label)})"
        )
    else:
        lines.append(f"Цена: <b>{format_money(product.price)}</b>")
    stock_label = (f"<b>{product.stock}</b> шт. в наличии"
                   if product.stock > 0 else "<b>нет в наличии</b>")
    lines.append(f"Остаток: {stock_label}")
    lines.append(
        "Статус: " + ("<b>в продаже</b>" if product.is_active
                      else "<b>снят с продажи</b>")
    )
    if product.description:
        lines.append("")
        lines.append(f"<i>{escape(product.description)}</i>")
    lines.append("")
    lines.append(f"Обновлён: {escape(product.updated_at)}")
    return "\n".join(lines)
