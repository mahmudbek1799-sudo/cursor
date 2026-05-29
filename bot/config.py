"""Конфигурация приложения.

Все настройки считываются из переменных окружения (или из файла .env).
Используется стандартная библиотека ``os`` и ``python-dotenv`` — без
дополнительных тяжёлых зависимостей. Такой подход полностью соответствует
требованиям ТЗ (Python 3, sqlite3, pyTelegramBotAPI).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

logger = logging.getLogger(__name__)


def _parse_admin_ids(raw: str) -> List[int]:
    result: List[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            result.append(int(chunk))
        except ValueError:
            logger.warning("Не удалось разобрать ADMIN_ID: %r", chunk)
    return result


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(slots=True)
class Settings:
    """Типобезопасная модель настроек бота."""

    bot_token: str
    admin_ids: List[int] = field(default_factory=list)
    db_path: str = "data/furniture_bot.sqlite3"

    # Источник данных сайта: mock | api | html
    shop_source: str = "mock"
    shop_api_url: str = ""
    shop_api_token: str = ""
    shop_catalog_url: str = ""
    shop_orders_url: str = ""
    shop_cookies: str = ""

    sync_interval: int = 60
    log_level: str = "INFO"

    # SOCKS5-прокси (для работы при блокировках Telegram в РФ).
    proxy_host: str = ""
    proxy_port: int = 0
    proxy_user: str = ""
    proxy_password: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            logger.warning(
                "BOT_TOKEN не задан. Запуск бота будет невозможен — "
                "укажите BOT_TOKEN в файле .env."
            )
        return cls(
            bot_token=token,
            admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
            db_path=os.getenv("DB_PATH", "data/furniture_bot.sqlite3"),
            shop_source=os.getenv("SHOP_SOURCE", "mock").lower(),
            shop_api_url=os.getenv("SHOP_API_URL", ""),
            shop_api_token=os.getenv("SHOP_API_TOKEN", ""),
            shop_catalog_url=os.getenv("SHOP_CATALOG_URL", ""),
            shop_orders_url=os.getenv("SHOP_ORDERS_URL", ""),
            shop_cookies=os.getenv("SHOP_COOKIES", ""),
            sync_interval=_get_int("SYNC_INTERVAL", 60),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            proxy_host=os.getenv("PROXY_HOST", "").strip(),
            proxy_port=_get_int("PROXY_PORT", 0),
            proxy_user=os.getenv("PROXY_USER", ""),
            proxy_password=os.getenv("PROXY_PASSWORD", ""),
        )

    def is_admin(self, user_id: int) -> bool:
        """Проверить, входит ли Telegram-пользователь в список администраторов."""

        return user_id in self.admin_ids

    def proxy_url(self) -> Optional[str]:
        """Сформировать URL SOCKS5-прокси.

        Если хост не задан, возвращает ``None`` и бот работает напрямую.
        В случае ограничений работы Telegram на территории РФ достаточно
        прописать ``PROXY_HOST`` и ``PROXY_PORT`` в файле .env.
        """

        if not self.proxy_host or not self.proxy_port:
            return None
        if self.proxy_user and self.proxy_password:
            return (
                f"socks5h://{self.proxy_user}:{self.proxy_password}"
                f"@{self.proxy_host}:{self.proxy_port}"
            )
        return f"socks5h://{self.proxy_host}:{self.proxy_port}"

    def parsed_cookies(self) -> dict:
        """Разобрать строку ``key1=v1; key2=v2`` в словарь cookies."""

        result: dict = {}
        for chunk in self.shop_cookies.split(";"):
            chunk = chunk.strip()
            if not chunk or "=" not in chunk:
                continue
            key, _, value = chunk.partition("=")
            result[key.strip()] = value.strip()
        return result


settings = Settings.from_env()
