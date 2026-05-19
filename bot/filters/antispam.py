"""Антиспам-фильтр.

Считает количество сообщений каждого (chat_id, user_id) в скользящем окне.
По умолчанию допускается 5 сообщений за 10 секунд — лимит можно изменить
для каждой группы через ``/setup`` (поля ``antispam_msgs`` / ``antispam_seconds``).

Хранение — в памяти процесса: deque фиксированной длины с метками времени.
Этого достаточно для одной реплики бота и не нагружает БД.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, Tuple

from aiogram.filters import BaseFilter
from aiogram.types import Message

from database import db


class AntiSpamFilter(BaseFilter):
    """Срабатывает, если пользователь превысил частоту сообщений."""

    _buckets: Dict[Tuple[int, int], Deque[float]] = defaultdict(deque)

    async def __call__(self, message: Message) -> bool | Dict[str, Any]:
        if message.from_user is None or message.chat is None:
            return False
        if message.from_user.is_bot:
            return False

        cfg = await db.get_settings(message.chat.id, message.chat.title or "")
        if not cfg.antispam_on:
            return False

        key = (message.chat.id, message.from_user.id)
        bucket = self._buckets[key]
        now = time.monotonic()

        window = cfg.antispam_seconds
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        bucket.append(now)

        if len(bucket) > cfg.antispam_msgs:
            bucket.clear()
            return {"reason": f"флуд: > {cfg.antispam_msgs} сообщ./{window} c"}
        return False
