"""Хелперы форматирования сообщений для Telegram."""

from __future__ import annotations

from html import escape

from bot.database.db import Order, STATUS_LABELS


def format_money(value: float) -> str:
    return f"{value:,.2f} ₽".replace(",", " ")


def format_order_card(order: Order) -> str:
    """Сформировать HTML-карточку заказа для отображения администратору."""

    status = STATUS_LABELS.get(order.status, order.status)
    comment = order.comment or "—"
    tg_id = order.customer_telegram_id or "—"
    return (
        f"<b>Заказ №{order.id}</b> (внешний: <code>{escape(order.external_id)}</code>)\n"
        f"Статус: <b>{escape(status)}</b>\n"
        f"Создан: {escape(order.created_at)}\n"
        f"Обновлён: {escape(order.updated_at)}\n"
        f"\n"
        f"<b>Клиент:</b> {escape(order.customer_name)}\n"
        f"<b>Телефон:</b> <code>{escape(order.customer_phone)}</code>\n"
        f"<b>Telegram ID:</b> <code>{tg_id}</code>\n"
        f"<b>Адрес доставки:</b> {escape(order.address)}\n"
        f"\n"
        f"<b>Состав заказа:</b>\n{escape(order.items)}\n"
        f"\n"
        f"<b>Сумма:</b> {format_money(order.total)}\n"
        f"<b>Комментарий:</b> {escape(comment)}"
    )
