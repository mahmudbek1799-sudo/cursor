"""Принудительная синхронизация заказов и каталога по команде."""

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
    last_run = (sync_service.last_run.strftime("%Y-%m-%d %H:%M:%S")
                if sync_service.last_run else "—")
    await status.edit_text(
        f"✅ Синхронизация выполнена.\nНовых заказов: <b>{created}</b>\n"
        f"Время последней синхронизации: {last_run}",
        parse_mode="HTML",
    )


@router.message(Command("parse_site"))
async def cmd_parse_site(message: Message, sync_service: OrderSyncService) -> None:
    """Скачать страницу каталога и обновить товары."""

    status = await message.answer("⏳ Загружаю и парсю каталог сайта…")
    created, updated = await sync_service.sync_products()
    await status.edit_text(
        f"✅ Парсинг каталога завершён.\n"
        f"Новых товаров: <b>{created}</b>\n"
        f"Обновлено: <b>{updated}</b>",
        parse_mode="HTML",
    )
