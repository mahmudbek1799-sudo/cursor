"""Клавиатуры административной панели бота."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from bot.database.db import ORDER_STATUSES, STATUS_LABELS


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню в виде reply-клавиатуры."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Активные заказы"),
             KeyboardButton(text="✅ Завершённые")],
            [KeyboardButton(text="📊 Статистика"),
             KeyboardButton(text="📈 Дашборд")],
            [KeyboardButton(text="🚫 Чёрный список"),
             KeyboardButton(text="📣 Рассылка")],
            [KeyboardButton(text="🔄 Синхронизация"),
             KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def orders_filter_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="Новые", callback_data="orders:f:new"),
            InlineKeyboardButton(text="Подтв.", callback_data="orders:f:confirmed"),
        ],
        [
            InlineKeyboardButton(text="В доставке", callback_data="orders:f:in_delivery"),
            InlineKeyboardButton(text="Завершён.", callback_data="orders:f:completed"),
        ],
        [
            InlineKeyboardButton(text="Отменён.", callback_data="orders:f:cancelled"),
            InlineKeyboardButton(text="Все", callback_data="orders:f:all"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def order_actions_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Действия над конкретным заказом."""

    rows = [
        [
            InlineKeyboardButton(
                text="🔁 Сменить статус",
                callback_data=f"order:{order_id}:status",
            ),
            InlineKeyboardButton(
                text="📞 Связаться",
                callback_data=f"order:{order_id}:contact",
            ),
        ],
        [
            InlineKeyboardButton(
                text="💬 Написать клиенту",
                callback_data=f"order:{order_id}:message",
            ),
        ],
        [
            InlineKeyboardButton(
                text="« К списку",
                callback_data="orders:f:new",
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def status_change_keyboard(order_id: int) -> InlineKeyboardMarkup:
    rows = []
    line: list[InlineKeyboardButton] = []
    for status in ORDER_STATUSES:
        line.append(
            InlineKeyboardButton(
                text=STATUS_LABELS[status],
                callback_data=f"order:{order_id}:set:{status}",
            )
        )
        if len(line) == 2:
            rows.append(line)
            line = []
    if line:
        rows.append(line)
    rows.append(
        [
            InlineKeyboardButton(
                text="« Отмена",
                callback_data=f"order:{order_id}:open",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"confirm:{action}:yes"),
                InlineKeyboardButton(text="✖️ Нет", callback_data=f"confirm:{action}:no"),
            ]
        ]
    )
