"""Принудительная синхронизация заказов по команде."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.services.sync import OrderSyncService

router = Router(name="sync")


@router.message(Command("sync"))
@router.message(F.text == "🔄 Синхронизация")
async def cmd_sync(message: Message, sync_service: OrderSyncService) -> None:
    status = await message.answer("⏳ Запускаю синхронизацию с сайтом магазина…")
    created = await sync_service.run_once()
    last_run = sync_service.last_run.strftime("%Y-%m-%d %H:%M:%S") if sync_service.last_run else "—"
    await status.edit_text(
        f"✅ Синхронизация выполнена.\nНовых заказов: <b>{created}</b>\n"
        f"Время последней синхронизации: {last_run}",
        parse_mode="HTML",
    )
