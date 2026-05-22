"""Статистика и аналитические дашборды."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from bot.database.db import get_db
from bot.services.analytics import build_orders_chart
from bot.utils.formatting import format_money

router = Router(name="stats")


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


@router.message(Command("stats"))
@router.message(F.text == "📊 Статистика")
async def cmd_stats(message: Message) -> None:
    db = get_db()
    data = await db.stats_summary()
    await message.answer(_format_stats(data), parse_mode="HTML")


@router.message(Command("dashboard"))
@router.message(F.text == "📈 Дашборд")
async def cmd_dashboard(message: Message) -> None:
    db = get_db()
    points = await db.orders_per_day(days=7)
    image = build_orders_chart(points)
    data = await db.stats_summary()
    await message.answer_photo(
        BufferedInputFile(image, filename="orders_dashboard.png"),
        caption=_format_stats(data),
        parse_mode="HTML",
    )
