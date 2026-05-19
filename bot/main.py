"""Точка входа в Telegram-бота администрирования группы.

Запуск:

    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    # подставьте BOT_TOKEN и OWNER_ID в .env
    python main.py
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings, validate_settings
from database import db
from handlers import get_root_router
from utils import setup_logging

log = logging.getLogger("bot")


async def main() -> None:
    validate_settings()
    setup_logging(settings.log_file)

    await db.connect()
    log.info("База данных подключена: %s", settings.db_path)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(get_root_router())

    me = await bot.get_me()
    log.info("Бот @%s готов к работе", me.username)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Остановлено пользователем.")
