"""Глобальная конфигурация проекта.

Все «секреты» и переменные окружения подгружаются из файла .env с помощью
python-dotenv. Здесь же хранятся значения по умолчанию для параметров,
которые позже могут переопределяться через таблицу ``group_settings``
в базе данных (на уровне каждой группы).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv

BASE_DIR: Path = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


def _get_int(name: str, default: int = 0) -> int:
    raw = os.getenv(name, str(default))
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


@dataclass(slots=True)
class Settings:
    """Контейнер настроек, читаемых при старте."""

    bot_token: str = os.getenv("BOT_TOKEN", "")
    owner_id: int = _get_int("OWNER_ID", 0)
    db_path: Path = BASE_DIR / os.getenv("DB_PATH", "bot.db")
    log_file: Path = BASE_DIR / os.getenv("LOG_FILE", "errors.log")

    # Значения по умолчанию для новых групп.
    default_antispam_messages: int = 5
    default_antispam_seconds: int = 10
    default_warn_limit: int = 3
    default_mute_hours: int = 24
    default_bad_words: List[str] = field(
        default_factory=lambda: [
            "дурак",
            "идиот",
            "придурок",
            "хрен",
            "сволочь",
        ]
    )
    default_trusted_domains: List[str] = field(
        default_factory=lambda: [
            "t.me",
            "telegram.me",
            "telegram.org",
        ]
    )


settings = Settings()


def validate_settings() -> None:
    """Базовая валидация. Падает с понятным сообщением, если токен пуст."""
    if not settings.bot_token or settings.bot_token.startswith("123456789:"):
        raise RuntimeError(
            "BOT_TOKEN не задан. Скопируйте .env.example в .env и подставьте "
            "токен, полученный у @BotFather."
        )
