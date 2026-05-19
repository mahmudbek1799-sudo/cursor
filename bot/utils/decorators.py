"""Декораторы для хэндлеров команд.

* :func:`group_only` отбрасывает попытки вызвать команду в личке.
* :func:`admin_only` проверяет, что отправитель — администратор чата
  (либо владелец бота, заданный в ``OWNER_ID``).
"""

from __future__ import annotations

import functools
from typing import Any, Awaitable, Callable

from aiogram import Bot
from aiogram.enums import ChatType
from aiogram.types import Message

from config import settings


Handler = Callable[..., Awaitable[Any]]


def group_only(func: Handler) -> Handler:
    @functools.wraps(func)
    async def wrapper(message: Message, *args: Any, **kwargs: Any) -> Any:
        if message.chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP}:
            await message.reply("Команда работает только в группе.")
            return None
        return await func(message, *args, **kwargs)

    return wrapper


def admin_only(func: Handler) -> Handler:
    @functools.wraps(func)
    async def wrapper(message: Message, *args: Any, **kwargs: Any) -> Any:
        bot: Bot = kwargs.get("bot") or message.bot  # type: ignore[assignment]
        if message.from_user is None:
            return None
        if message.from_user.id == settings.owner_id:
            return await func(message, *args, **kwargs)
        try:
            member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        except Exception:
            await message.reply("Не удалось проверить ваши права.")
            return None
        if member.status not in {"administrator", "creator"}:
            await message.reply("Команда доступна только администраторам группы.")
            return None
        return await func(message, *args, **kwargs)

    return wrapper
