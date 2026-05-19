"""Inline / reply клавиатуры бота."""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def setup_menu() -> InlineKeyboardMarkup:
    """Главное меню команды /setup."""
    rows = [
        [
            InlineKeyboardButton(text="Антиспам", callback_data="setup:antispam"),
            InlineKeyboardButton(text="Антиссылки", callback_data="setup:antilinks"),
        ],
        [
            InlineKeyboardButton(text="Антимат", callback_data="setup:antibadwords"),
            InlineKeyboardButton(text="Лимит варнов", callback_data="setup:warns"),
        ],
        [
            InlineKeyboardButton(text="Список мата", callback_data="setup:words"),
            InlineKeyboardButton(text="Доверенные домены", callback_data="setup:domains"),
        ],
        [InlineKeyboardButton(text="Закрыть", callback_data="setup:close")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def toggle_kb(field: str, value: bool) -> InlineKeyboardMarkup:
    """Клавиатура переключателя on/off."""
    label_on = ("✅ " if value else "") + "Включить"
    label_off = ("✅ " if not value else "") + "Выключить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=label_on, callback_data=f"toggle:{field}:1"),
                InlineKeyboardButton(text=label_off, callback_data=f"toggle:{field}:0"),
            ],
            [InlineKeyboardButton(text="« Назад", callback_data="setup:back")],
        ]
    )


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="« Назад", callback_data="setup:back")]]
    )


__all__ = ["setup_menu", "toggle_kb", "back_kb", "ReplyKeyboardMarkup", "KeyboardButton"]
