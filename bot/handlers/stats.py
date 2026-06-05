"""Команды статистики и аналитического дашборда."""

from __future__ import annotations

import logging

from telebot import TeleBot
from telebot.types import Message

from bot.database import get_db
from bot.services.analytics import build_orders_chart
from bot.utils import admin_only, format_money

logger = logging.getLogger(__name__)


def _format_stats(data: dict) -> str:
    return (
        "<b>📊 Сводная статистика</b>\n\n"
        f"Всего заказов: <b>{data['total']}</b>\n"
        f"Новые: <b>{data['new']}</b>\n"
        f"Завершённые: <b>{data['completed']}</b>\n"
        f"Отменённые: <b>{data['cancelled']}</b>\n\n"
        f"За сегодня: <b>{data['today']}</b>\n"
        f"За 7 дней: <b>{data['week']}</b>\n"
        f"За 30 дней: <b>{data['month']}</b>\n\n"
        f"Выручка за сегодня: <b>{format_money(data['revenue_today'])}</b>\n"
        f"Выручка за 7 дней: <b>{format_money(data['revenue_week'])}</b>"
    )


def register(bot: TeleBot) -> None:

    @bot.message_handler(commands=["stats"])
    @admin_only
    def cmd_stats(message: Message) -> None:
        db = get_db()
        bot.send_message(message.chat.id,
                         _format_stats(db.stats_summary()),
                         parse_mode="HTML")

    @bot.message_handler(func=lambda m: m.text == "📊 Статистика")
    @admin_only
    def kb_stats(message: Message) -> None:
        cmd_stats(message)

    @bot.message_handler(commands=["dashboard"])
    @admin_only
    def cmd_dashboard(message: Message) -> None:
        db = get_db()
        points = db.orders_per_day(days=7)
        image = build_orders_chart(points)
        bot.send_photo(
            message.chat.id, photo=image,
            caption=_format_stats(db.stats_summary()),
            parse_mode="HTML",
        )

    @bot.message_handler(func=lambda m: m.text == "📈 Дашборд")
    @admin_only
    def kb_dashboard(message: Message) -> None:
        cmd_dashboard(message)
