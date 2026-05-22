"""Точка входа Telegram-бота.

Запускается командой ``python -m bot.main`` (или ``python bot/main.py``).
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.database.db import get_db
from bot.handlers import router as root_router
from bot.middlewares import AdminAccessMiddleware
from bot.services.shop_api import MockShopAPI
from bot.services.sync import OrderSyncService
from bot.utils.logging_setup import setup_logging

logger = logging.getLogger(__name__)


async def on_startup(bot: Bot, sync_service: OrderSyncService) -> None:
    me = await bot.get_me()
    logger.info("Бот @%s запущен (id=%s)", me.username, me.id)
    logger.info("Администраторы: %s", settings.admin_ids)
    await sync_service.start()


async def on_shutdown(bot: Bot, sync_service: OrderSyncService) -> None:
    logger.info("Остановка бота…")
    await sync_service.stop()
    await bot.session.close()


async def main() -> None:
    setup_logging(settings.log_level)
    logger.info("Запуск приложения «Бот администратора мебельного магазина»")

    if not settings.admin_ids:
        logger.warning(
            "Список ADMIN_IDS пуст — никто не сможет пользоваться ботом. "
            "Заполните переменную окружения ADMIN_IDS."
        )

    db = get_db()
    await db.init_schema()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Источник заказов: для демонстрации — mock, для прод — ShopAPIClient.
    shop_api = MockShopAPI()
    sync_service = OrderSyncService(bot=bot, db=db, api=shop_api)

    dp = Dispatcher(storage=MemoryStorage())
    dp["sync_service"] = sync_service
    dp.update.outer_middleware(AdminAccessMiddleware())
    dp.include_router(root_router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(
            bot,
            sync_service=sync_service,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        await sync_service.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Завершение работы по сигналу.")
