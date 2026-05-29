"""Просмотр заказов, смена статуса, связь с клиентом."""

from __future__ import annotations

import logging
from html import escape

from telebot import TeleBot
from telebot.types import CallbackQuery, Message

from bot.database import ORDER_STATUSES, STATUS_LABELS, get_db
from bot.keyboards import (
    order_actions_keyboard,
    orders_filter_keyboard,
    status_change_keyboard,
)
from bot.utils import admin_only, format_order_card

logger = logging.getLogger(__name__)

_ACTIVE = ("new", "confirmed", "in_delivery")
_DONE = ("completed", "cancelled")

# Состояния FSM для отправки сообщения клиенту: chat_id -> order_id.
_pending_message: dict[int, int] = {}


def _orders_list_text(orders, title: str) -> str:
    if not orders:
        return f"<b>{escape(title)}</b>\n\nНет заказов в выбранной категории."
    lines = [f"<b>{escape(title)}</b>", ""]
    for o in orders:
        lines.append(
            f"#{o.id} | {escape(o.status_label)} | "
            f"{escape(o.customer_name)} | "
            f"{o.total:,.0f} ₽ | /order_{o.id}".replace(",", " ")
        )
    lines.append("")
    lines.append("Откройте карточку командой /order_&lt;id&gt;.")
    return "\n".join(lines)


def register(bot: TeleBot) -> None:

    # ------------------------------------------------------------------
    # Списки
    # ------------------------------------------------------------------
    @bot.message_handler(commands=["orders"])
    @admin_only
    def cmd_orders(message: Message) -> None:
        parts = message.text.split(maxsplit=1)
        arg = (parts[1].strip().lower() if len(parts) > 1 else "")
        db = get_db()
        if arg in ("", "active"):
            orders = db.list_orders(statuses=_ACTIVE)
            title = "📋 Активные заказы"
        elif arg in ("done", "completed", "finished"):
            orders = db.list_orders(statuses=_DONE)
            title = "✅ Завершённые заказы"
        elif arg == "all":
            orders = db.list_orders()
            title = "📦 Все заказы (последние 20)"
        elif arg in ORDER_STATUSES:
            orders = db.list_orders(statuses=(arg,))
            title = f"Заказы: {STATUS_LABELS[arg]}"
        else:
            bot.reply_to(message, "Неизвестный фильтр.")
            return
        bot.send_message(
            message.chat.id, _orders_list_text(orders, title),
            reply_markup=orders_filter_keyboard(),
            parse_mode="HTML",
        )

    @bot.message_handler(func=lambda m: m.text == "📋 Активные заказы")
    @admin_only
    def kb_active(message: Message) -> None:
        db = get_db()
        bot.send_message(
            message.chat.id,
            _orders_list_text(
                db.list_orders(statuses=_ACTIVE), "📋 Активные заказы"),
            reply_markup=orders_filter_keyboard(),
            parse_mode="HTML",
        )

    @bot.message_handler(func=lambda m: m.text == "✅ Завершённые")
    @admin_only
    def kb_done(message: Message) -> None:
        db = get_db()
        bot.send_message(
            message.chat.id,
            _orders_list_text(
                db.list_orders(statuses=_DONE), "✅ Завершённые заказы"),
            reply_markup=orders_filter_keyboard(),
            parse_mode="HTML",
        )

    @bot.callback_query_handler(
        func=lambda c: c.data and c.data.startswith("orders:f:"))
    @admin_only
    def cb_filter(callback: CallbackQuery) -> None:
        key = callback.data.split(":")[-1]
        db = get_db()
        if key == "all":
            orders = db.list_orders()
            title = "📦 Все заказы"
        else:
            orders = db.list_orders(statuses=(key,))
            title = f"Заказы: {STATUS_LABELS.get(key, key)}"
        try:
            bot.edit_message_text(
                _orders_list_text(orders, title),
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                reply_markup=orders_filter_keyboard(),
                parse_mode="HTML",
            )
        except Exception:  # noqa: BLE001
            pass
        bot.answer_callback_query(callback.id)

    # ------------------------------------------------------------------
    # Карточка заказа
    # ------------------------------------------------------------------
    def _send_order_card(chat_id: int, order_id: int) -> None:
        db = get_db()
        order = db.get_order(order_id)
        if order is None:
            bot.send_message(chat_id, "Заказ не найден.")
            return
        bot.send_message(
            chat_id, format_order_card(order),
            reply_markup=order_actions_keyboard(order.id),
            parse_mode="HTML",
        )

    @bot.message_handler(commands=["order"])
    @admin_only
    def cmd_order(message: Message) -> None:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip().isdigit():
            bot.reply_to(message, "Использование: /order &lt;id&gt;",
                         parse_mode="HTML")
            return
        _send_order_card(message.chat.id, int(parts[1].strip()))

    @bot.message_handler(regexp=r"^/order_(\d+)$")
    @admin_only
    def cmd_order_underscore(message: Message) -> None:
        oid = int(message.text.split("_", 1)[1])
        _send_order_card(message.chat.id, oid)

    @bot.callback_query_handler(
        func=lambda c: c.data and c.data.startswith("order:")
        and c.data.endswith(":open"))
    @admin_only
    def cb_open(callback: CallbackQuery) -> None:
        oid = int(callback.data.split(":")[1])
        db = get_db()
        order = db.get_order(oid)
        if order is None:
            bot.answer_callback_query(callback.id,
                                      "Заказ не найден", show_alert=True)
            return
        try:
            bot.edit_message_text(
                format_order_card(order),
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                reply_markup=order_actions_keyboard(order.id),
                parse_mode="HTML",
            )
        except Exception:  # noqa: BLE001
            pass
        bot.answer_callback_query(callback.id)

    @bot.callback_query_handler(
        func=lambda c: c.data and c.data.startswith("order:")
        and ":status" in c.data and c.data.endswith(":status"))
    @admin_only
    def cb_status(callback: CallbackQuery) -> None:
        oid = int(callback.data.split(":")[1])
        try:
            bot.edit_message_reply_markup(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                reply_markup=status_change_keyboard(oid),
            )
        except Exception:  # noqa: BLE001
            pass
        bot.answer_callback_query(callback.id, "Выберите новый статус")

    @bot.callback_query_handler(
        func=lambda c: c.data and c.data.startswith("order:")
        and ":set:" in c.data)
    @admin_only
    def cb_set_status(callback: CallbackQuery) -> None:
        parts = callback.data.split(":")
        oid, status = int(parts[1]), parts[3]
        if status not in ORDER_STATUSES:
            bot.answer_callback_query(callback.id,
                                      "Недопустимый статус", show_alert=True)
            return
        db = get_db()
        if not db.set_order_status(oid, status):
            bot.answer_callback_query(callback.id,
                                      "Заказ не найден", show_alert=True)
            return
        db.log_action(
            admin_id=callback.from_user.id, action="set_status",
            target=str(oid), payload=status,
        )
        order = db.get_order(oid)
        try:
            bot.edit_message_text(
                format_order_card(order),
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                reply_markup=order_actions_keyboard(oid),
                parse_mode="HTML",
            )
        except Exception:  # noqa: BLE001
            pass
        bot.answer_callback_query(
            callback.id, f"Статус: {STATUS_LABELS[status]}")
        # Уведомление клиенту, если он связан в Telegram.
        if (order and order.customer_telegram_id
                and not db.is_blocked(order.customer_telegram_id)):
            try:
                bot.send_message(
                    order.customer_telegram_id,
                    f"📦 Статус вашего заказа №{order.id} изменён на: "
                    f"<b>{STATUS_LABELS[status]}</b>.",
                    parse_mode="HTML",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Клиент %s недоступен: %s",
                               order.customer_telegram_id, exc)

    @bot.callback_query_handler(
        func=lambda c: c.data and c.data.startswith("order:")
        and c.data.endswith(":contact"))
    @admin_only
    def cb_contact(callback: CallbackQuery) -> None:
        oid = int(callback.data.split(":")[1])
        db = get_db()
        order = db.get_order(oid)
        if order is None:
            bot.answer_callback_query(callback.id,
                                      "Заказ не найден", show_alert=True)
            return
        text = (
            f"<b>Контактные данные клиента (заказ №{order.id})</b>\n\n"
            f"ФИО: {escape(order.customer_name)}\n"
            f"Телефон: <code>{escape(order.customer_phone)}</code>\n"
            f"Telegram ID: <code>{order.customer_telegram_id or '—'}</code>\n"
            f"Адрес: {escape(order.address)}"
        )
        bot.send_message(callback.message.chat.id, text, parse_mode="HTML")
        bot.answer_callback_query(callback.id)

    @bot.callback_query_handler(
        func=lambda c: c.data and c.data.startswith("order:")
        and c.data.endswith(":message"))
    @admin_only
    def cb_message_start(callback: CallbackQuery) -> None:
        oid = int(callback.data.split(":")[1])
        db = get_db()
        order = db.get_order(oid)
        if order is None or not order.customer_telegram_id:
            bot.answer_callback_query(
                callback.id,
                "У клиента нет связанного Telegram-аккаунта",
                show_alert=True)
            return
        _pending_message[callback.from_user.id] = oid
        bot.send_message(
            callback.message.chat.id,
            "✏️ Введите текст сообщения для клиента (или /cancel).",
        )
        bot.answer_callback_query(callback.id)

    @bot.message_handler(
        func=lambda m: m.from_user and
        m.from_user.id in _pending_message and (m.text or "") != "/cancel")
    @admin_only
    def msg_send_to_client(message: Message) -> None:
        oid = _pending_message.pop(message.from_user.id, None)
        if not oid:
            return
        db = get_db()
        order = db.get_order(oid)
        if order is None or not order.customer_telegram_id:
            bot.reply_to(message, "Клиент недоступен.")
            return
        if db.is_blocked(order.customer_telegram_id):
            bot.reply_to(message, "Этот клиент в чёрном списке.")
            return
        try:
            bot.send_message(
                order.customer_telegram_id,
                f"💬 Сообщение от магазина (заказ №{order.id}):\n\n"
                f"{message.text}",
            )
            db.log_action(
                admin_id=message.from_user.id, action="message_client",
                target=str(order.customer_telegram_id),
                payload=(message.text or "")[:200],
            )
            bot.reply_to(message, "✅ Сообщение отправлено клиенту.")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка отправки клиенту: %s", exc)
            bot.reply_to(message, "❌ Не удалось отправить.")

    @bot.message_handler(
        func=lambda m: m.from_user
        and m.from_user.id in _pending_message
        and (m.text or "") == "/cancel")
    @admin_only
    def msg_cancel(message: Message) -> None:
        _pending_message.pop(message.from_user.id, None)
        bot.reply_to(message, "Отменено.")
