"""Антимат-фильтр: ищет в тексте слова из чёрного списка группы.

Сравнение регистронезависимое, по границе слова, чтобы «дурак» матчился,
а «дурака́н» — нет. Список ведётся через ``/setup`` и хранится в БД.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Dict, Tuple

from aiogram.filters import BaseFilter
from aiogram.types import Message

from database import db


@lru_cache(maxsize=64)
def _compile(words_key: Tuple[str, ...]) -> re.Pattern[str] | None:
    if not words_key:
        return None
    escaped = "|".join(re.escape(w) for w in words_key if w)
    if not escaped:
        return None
    return re.compile(rf"(?<!\w)(?:{escaped})(?!\w)", re.IGNORECASE | re.UNICODE)


class BadWordsFilter(BaseFilter):
    """Срабатывает, если найдено хотя бы одно слово из ``bad_words``."""

    async def __call__(self, message: Message) -> bool | Dict[str, Any]:
        if message.from_user is None or message.from_user.is_bot:
            return False
        text = (message.text or message.caption or "")
        if not text:
            return False

        cfg = await db.get_settings(message.chat.id, message.chat.title or "")
        if not cfg.antibadwords_on:
            return False

        pattern = _compile(tuple(sorted(cfg.bad_words)))
        if pattern is None:
            return False
        match = pattern.search(text)
        if match:
            return {"reason": f"нецензурная лексика: «{match.group(0)}»"}
        return False
