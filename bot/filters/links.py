"""Фильтр запрещённых ссылок.

Проверяет текст и подписи на наличие ссылок и пропускает только те,
домены которых находятся в белом списке ``trusted_domains`` группы.
"""

from __future__ import annotations

import re
from typing import Any, Dict
from urllib.parse import urlparse

from aiogram.filters import BaseFilter
from aiogram.types import Message

from database import db


URL_RE = re.compile(
    r"(?:(?:https?|tg)://[^\s]+|(?:www\.|t\.me/|@)[^\s]+)",
    re.IGNORECASE,
)


def _extract_host(token: str) -> str:
    token = token.strip().strip(".,;!?)\"'")
    if token.startswith("@"):
        return "t.me"
    if "://" not in token:
        token = "http://" + token
    try:
        host = urlparse(token).hostname or ""
    except ValueError:
        return ""
    return host.lower().removeprefix("www.")


class LinksFilter(BaseFilter):
    """Срабатывает, если в сообщении есть ссылка на «чужой» домен."""

    async def __call__(self, message: Message) -> bool | Dict[str, Any]:
        if message.from_user is None or message.from_user.is_bot:
            return False

        text = (message.text or message.caption or "").strip()
        if not text:
            return False

        cfg = await db.get_settings(message.chat.id, message.chat.title or "")
        if not cfg.antilinks_on:
            return False

        trusted = {d.lower().removeprefix("www.") for d in cfg.trusted_domains}
        found = URL_RE.findall(text)
        if not found:
            return False

        for token in found:
            host = _extract_host(token)
            if not host:
                continue
            if not any(host == t or host.endswith("." + t) for t in trusted):
                return {"reason": f"запрещённая ссылка: {host}"}
        return False
