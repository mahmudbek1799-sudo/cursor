"""Просмотр заказов, изменение статуса, связь с клиентом."""

from __future__ import annotations

import logging
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.database.db import ORDER_STATUSES, STATUS_LABELS, get_db
from bot.keyboards.admin import (
    order_actions_keyboard,
    orders_filter_keyboard,
    status_change_keyboard,
)
from bot.utils.formatting import format_order_card

logger = logging.getLogger(__name__)
router = Router(name="orders")


class OrderMessage(StatesGroup):
    waiting_text = State()


_ACTIVE_STATUSES = ("new", "confirmed", "in_delivery")
_DONE_STATUSES = ("completed", "cancelled")


def _orders_list_text(orders, title: str) -> str:
    if not orders:
        return f"<b>{escape(title)}</b>\n\nНет заказов в выбранной категории."
    lines = [f"<b>{escape(title)}</b>", ""]
    for order in orders:
        lines.append(
            f"#{order.id} | {escape(order.status_label)} | "
            f"{escape(order.customer_name)} | {order.total:,.0f} ₽ | "
            f"/order_{order.id}".replace(",", " ")
        )
    lines.append("")
    lines.append("Откройте карточку командой /order_&lt;id&gt;.")
    return "\n".join(lines)


@router.message(Command("orders"))
async def cmd_orders(message: Message, command: CommandObject) -> None:
    arg = (command.args or "").strip().lower()
    db = get_db()
    if arg in ("", "active"):
        orders = await db.list_orders(statuses=_ACTIVE_STATUSES, limit=20)
        title = "📋 Активные заказы"
    elif arg in ("done", "completed", "finished"):
        orders = await db.list_orders(statuses=_DONE_STATUSES, limit=20)
        title = "✅ Завершённые заказы"
    elif arg == "all":
        orders = await db.list_orders(limit=20)
        title = "📦 Все заказы (последние 20)"
    elif arg in ORDER_STATUSES:
        orders = await db.list_orders(statuses=(arg,), limit=20)
        title = f"Заказы: {STATUS_LABELS[arg]}"
    else:
        await message.answer(
            "Неизвестный фильтр. Используйте: active, done, all или один из статусов: "
            + ", ".join(ORDER_STATUSES)
        )
        return
    await message.answer(
        _orders_list_text(orders, title),
        reply_markup=orders_filter_keyboard(),
        parse_mode="HTML",
    )


@router.message(F.text == "📋 Активные заказы")
async def kb_active(message: Message) -> None:
    db = get_db()
    orders = await db.list_orders(statuses=_ACTIVE_STATUSES, limit=20)
    await message.answer(
        _orders_list_text(orders, "📋 Активные заказы"),
        reply_markup=orders_filter_keyboard(),
        parse_mode="HTML",
    )


@router.message(F.text == "✅ Завершённые")
async def kb_done(message: Message) -> None:
    db = get_db()
    orders = await db.list_orders(statuses=_DONE_STATUSES, limit=20)
    await message.answer(
        _orders_list_text(orders, "✅ Завершённые заказы"),
        reply_markup=orders_filter_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("orders:f:"))
async def cb_filter(callback: CallbackQuery) -> None:
    key = callback.data.split(":")[-1]
    db = get_db()
    if key == "all":
        orders = await db.list_orders(limit=20)
        title = "📦 Все заказы"
    else:
        orders = await db.list_orders(statuses=(key,), limit=20)
        title = f"Заказы: {STATUS_LABELS.get(key, key)}"
    await callback.message.edit_text(
        _orders_list_text(orders, title),
        reply_markup=orders_filter_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(Command("order"))
@router.message(F.text.regexp(r"^/order[_ ](\d+)$").as_("m"))
async def cmd_order(message: Message, command: CommandObject | None = None, m=None) -> None:
    raw: str | None = None
    if command and command.args:
        raw = command.args.strip()
    elif m is not None:
        raw = m.group(1)
    if not raw or not raw.isdigit():
        await message.answer("Использование: /order &lt;id&gt;", parse_mode="HTML")
        return
    db = get_db()
    order = await db.get_order(int(raw))
    if order is None:
        await message.answer("Заказ не найден.")
        return
    await message.answer(
        format_order_card(order),
        reply_markup=order_actions_keyboard(order.id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.regexp(r"^order:(\d+):open$"))
async def cb_open(callback: CallbackQuery) -> None:
    order_id = int(callback.data.split(":")[1])
    db = get_db()
    order = await db.get_order(order_id)
    if order is None:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    await callback.message.edit_text(
        format_order_card(order),
        reply_markup=order_actions_keyboard(order.id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^order:(\d+):status$"))
async def cb_status(callback: CallbackQuery) -> None:
    order_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup(
        reply_markup=status_change_keyboard(order_id)
    )
    await callback.answer("Выберите новый статус")


@router.callback_query(F.data.regexp(r"^order:(\d+):set:(\w+)$"))
async def cb_set_status(callback: CallbackQuery) -> None:
    _, order_id, _, status = callback.data.split(":")
    order_id_int = int(order_id)
    if status not in ORDER_STATUSES:
        await callback.answer("Недопустимый статус", show_alert=True)
        return
    db = get_db()
    updated = await db.set_order_status(order_id_int, status)
    if not updated:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    await db.log_action(
        admin_id=callback.from_user.id,
        action="set_status",
        target=str(order_id_int),
        payload=status,
    )
    order = await db.get_order(order_id_int)
    await callback.message.edit_text(
        format_order_card(order),
        reply_markup=order_actions_keyboard(order_id_int),
        parse_mode="HTML",
    )
    await callback.answer(f"Статус: {STATUS_LABELS[status]}")
    # Уведомим клиента (если он связан через Telegram).
    if order and order.customer_telegram_id and not await db.is_blocked(order.customer_telegram_id):
        try:
            await callback.bot.send_message(
                order.customer_telegram_id,
                f"📦 Статус вашего заказа №{order.id} изменён на: "
                f"<b>{STATUS_LABELS[status]}</b>.",
                parse_mode="HTML",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Клиент %s недоступен: %s", order.customer_telegram_id, exc)


@router.callback_query(F.data.regexp(r"^order:(\d+):contact$"))
async def cb_contact(callback: CallbackQuery) -> None:
    order_id = int(callback.data.split(":")[1])
    db = get_db()
    order = await db.get_order(order_id)
    if order is None:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    text = (
        f"<b>Контактные данные клиента (заказ №{order.id})</b>\n\n"
        f"ФИО: {escape(order.customer_name)}\n"
        f"Телефон: <code>{escape(order.customer_phone)}</code>\n"
        f"Telegram ID: <code>{order.customer_telegram_id or '—'}</code>\n"
        f"Адрес: {escape(order.address)}"
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.regexp(r"^order:(\d+):message$"))
async def cb_message_start(callback: CallbackQuery, state: FSMContext) -> None:
    order_id = int(callback.data.split(":")[1])
    db = get_db()
    order = await db.get_order(order_id)
    if order is None or not order.customer_telegram_id:
        await callback.answer(
            "У клиента нет связанного Telegram-аккаунта", show_alert=True
        )
        return
    await state.update_data(order_id=order_id)
    await state.set_state(OrderMessage.waiting_text)
    await callback.message.answer(
        "✏️ Введите текст сообщения для клиента (или /cancel для отмены)."
    )
    await callback.answer()


@router.message(OrderMessage.waiting_text, Command("cancel"))
async def msg_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.")


@router.message(OrderMessage.waiting_text)
async def msg_send(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    order_id = int(data.get("order_id", 0))
    await state.clear()
    db = get_db()
    order = await db.get_order(order_id)
    if order is None or not order.customer_telegram_id:
        await message.answer("Клиент недоступен для отправки.")
        return
    if await db.is_blocked(order.customer_telegram_id):
        await message.answer("Этот клиент находится в чёрном списке.")
        return
    try:
        await message.bot.send_message(
            order.customer_telegram_id,
            f"💬 Сообщение от магазина (заказ №{order.id}):\n\n{message.text}",
        )
        await db.log_action(
            admin_id=message.from_user.id,
            action="message_client",
            target=str(order.customer_telegram_id),
            payload=message.text[:200],
        )
        await message.answer("✅ Сообщение отправлено клиенту.")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка отправки сообщения клиенту: %s", exc)
        await message.answer("❌ Не удалось отправить сообщение клиенту.")
