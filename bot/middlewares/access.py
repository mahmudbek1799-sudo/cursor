"""Middleware контроля доступа.

Реализует принцип «по умолчанию запрещено»: любой апдейт от пользователя,
не входящего в список ``ADMIN_IDS``, отклоняется с дружелюбным сообщением,
а попытка фиксируется в журнале действий администратора.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import settings
from bot.database.db import get_db

logger = logging.getLogger(__name__)


class AdminAccessMiddleware(BaseMiddleware):
    """Пропускает только администраторов; всё остальное — отклоняет."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id: int | None = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        if not settings.is_admin(user_id):
            logger.warning(
                "Запрещённая попытка доступа: user_id=%s, тип события=%s",
                user_id,
                type(event).__name__,
            )
            db = get_db()
            await db.log_action(
                admin_id=user_id,
                action="access_denied",
                target=type(event).__name__,
            )
            if isinstance(event, Message):
                await event.answer(
                    "⛔ Доступ закрыт. Этот бот предназначен только для администраторов магазина."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("Доступ запрещён", show_alert=True)
            return None

        return await handler(event, data)
