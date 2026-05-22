"""Конфигурация приложения.

Параметры считываются из переменных окружения (или из файла .env).
Используется pydantic-settings, что обеспечивает строгую валидацию типов
и автоматическое приведение значений из строкового представления.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Типобезопасная модель настроек бота."""

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: str = Field(..., description="Токен Telegram-бота от @BotFather")
    admin_ids: List[int] = Field(
        default_factory=list,
        description="Список Telegram ID пользователей с правами администратора",
    )
    db_path: str = Field(
        default="data/furniture_bot.sqlite3",
        description="Путь к файлу SQLite-базы данных",
    )
    shop_api_url: str = Field(
        default="http://localhost:8080/api/orders",
        description="URL API сайта мебельного магазина для получения заказов",
    )
    shop_api_token: str = Field(
        default="demo_shop_token",
        description="Токен для авторизации запросов к API магазина",
    )
    sync_interval: int = Field(
        default=60,
        ge=10,
        description="Интервал автоматической синхронизации заказов, секунды",
    )
    log_level: str = Field(default="INFO")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, raw: object) -> List[int]:
        if raw is None or raw == "":
            return []
        if isinstance(raw, list):
            return [int(x) for x in raw]
        # Формат "111,222,333" из переменной окружения.
        return [int(x.strip()) for x in str(raw).split(",") if x.strip()]

    def is_admin(self, user_id: int) -> bool:
        """Проверить, входит ли Telegram-пользователь в список администраторов."""

        return user_id in self.admin_ids


settings = Settings()  # type: ignore[call-arg]
