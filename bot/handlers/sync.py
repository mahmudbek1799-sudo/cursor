"""Команды принудительной синхронизации с сайтом."""

from __future__ import annotations

import logging

from telebot import TeleBot
from telebot.types import Message

from bot.services.sync import OrderSyncService
from bot.utils import admin_only

logger = logging.getLogger(__name__)


def register(bot: TeleBot, sync_service: OrderSyncService) -> None:

    @bot.message_handler(commands=["sync"])
    @admin_only
    def cmd_sync(message: Message) -> None:
        status = bot.send_message(
            message.chat.id,
            "⏳ Запускаю синхронизацию заказов с сайтом…",
        )
        created = sync_service.run_once()
        last_run = (sync_service.last_run.strftime("%Y-%m-%d %H:%M:%S")
                    if sync_service.last_run else "—")
        bot.edit_message_text(
            f"✅ Синхронизация выполнена.\n"
            f"Новых заказов: <b>{created}</b>\n"
            f"Время последней синхронизации: {last_run}",
            chat_id=status.chat.id, message_id=status.message_id,
            parse_mode="HTML",
        )

    @bot.message_handler(func=lambda m: m.text == "🔄 Синхронизация")
    @admin_only
    def kb_sync(message: Message) -> None:
        cmd_sync(message)

    @bot.message_handler(commands=["parse_site"])
    @admin_only
    def cmd_parse(message: Message) -> None:
        status = bot.send_message(
            message.chat.id,
            "⏳ Загружаю и парсю каталог сайта…",
        )
        created, updated = sync_service.sync_products()
        bot.edit_message_text(
            f"✅ Парсинг каталога завершён.\n"
            f"Новых товаров: <b>{created}</b>\n"
            f"Обновлено: <b>{updated}</b>",
            chat_id=status.chat.id, message_id=status.message_id,
            parse_mode="HTML",
        )
