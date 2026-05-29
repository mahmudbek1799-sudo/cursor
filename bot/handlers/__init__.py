"""Регистрация всех обработчиков telebot."""

from __future__ import annotations

from telebot import TeleBot

from bot.handlers import (
    broadcast,
    common,
    discounts,
    export,
    orders,
    products,
    stats,
    sync,
    users,
)


def register_handlers(bot: TeleBot, sync_service) -> None:
    """Зарегистрировать все хендлеры в переданном экземпляре TeleBot."""

    common.register(bot)
    orders.register(bot)
    products.register(bot)
    discounts.register(bot)
    stats.register(bot)
    users.register(bot)
    broadcast.register(bot)
    sync.register(bot, sync_service)
    export.register(bot)
