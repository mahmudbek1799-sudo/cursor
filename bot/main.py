"""Точка входа Telegram-бота администратора мебельного магазина.

Реализована на ``pyTelegramBotAPI`` (telebot) в синхронном режиме
с polling. Поддерживается работа через SOCKS5-прокси для обхода
ограничений Telegram на территории РФ. Источник данных (REST API,
HTML-парсер или mock) выбирается переменной окружения ``SHOP_SOURCE``.

Запуск:

    python -m bot.main
"""

from __future__ import annotations

import logging
import sys

import telebot
from telebot import TeleBot, apihelper

from bot.config import settings
from bot.database import get_db
from bot.handlers import register_handlers
from bot.services import OrderSyncService, build_shop_source
from bot.utils import setup_logging

logger = logging.getLogger(__name__)


def _apply_proxy() -> None:
    """Настроить SOCKS5-прокси для telebot, если задан в .env.

    В условиях периодических ограничений работы Telegram на территории
    РФ это обеспечивает непрерывность администрирования.
    """

    proxy_url = settings.proxy_url()
    if not proxy_url:
        return
    apihelper.proxy = {"http": proxy_url, "https": proxy_url}
    logger.info("Telegram-клиент настроен через прокси: %s",
                proxy_url.split("@")[-1])


def main() -> int:
    setup_logging(settings.log_level)
    logger.info("Запуск Telegram-бота администратора мебельного магазина")

    if not settings.bot_token:
        logger.error("BOT_TOKEN не задан. Запуск невозможен.")
        return 1
    if not settings.admin_ids:
        logger.warning(
            "ADMIN_IDS пуст — никто не сможет пользоваться ботом. "
            "Заполните переменную окружения ADMIN_IDS."
        )

    db = get_db()
    db.init_schema()

    _apply_proxy()
    bot = TeleBot(settings.bot_token, parse_mode="HTML", threaded=True)

    shop_api = build_shop_source()
    sync_service = OrderSyncService(bot=bot, db=db, api=shop_api)

    register_handlers(bot, sync_service)

    try:
        me = bot.get_me()
        logger.info("Бот @%s запущен (id=%s)", me.username, me.id)
    except Exception as exc:  # noqa: BLE001
        logger.error("Не удалось получить информацию о боте: %s", exc)
        return 1

    sync_service.start()
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=30,
                             skip_pending=False)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Завершение по сигналу.")
    finally:
        sync_service.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
