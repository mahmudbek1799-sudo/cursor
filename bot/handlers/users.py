"""Хэндлеры для обычных участников группы.

Здесь сосредоточена логика автоматической модерации:
обработка сообщений через фильтры антиспама, антимата и антиссылок,
а также реакции на присоединение / выход участников.

Любое срабатывание фильтра приводит к удалению сообщения,
выдаче варна и записи в журнал ``logs``. При достижении лимита
варнов пользователю автоматически выдаётся мут на ``mute_hours``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.types import ChatPermissions, Message

from database import db
from filters import AntiSpamFilter, BadWordsFilter, LinksFilter
from utils import get_logger

router = Router(name="users")
log = get_logger(__name__)


GROUP_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}


async def _auto_punish(message: Message, bot: Bot, reason: str) -> None:
    """Удалить сообщение, добавить варн, при необходимости мутировать."""
    if message.from_user is None:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    try:
        await message.delete()
    except Exception as exc:
        log.warning("Не удалось удалить сообщение %s: %s", message.message_id, exc)

    cfg = await db.get_settings(chat_id, message.chat.title or "")
    warns = await db.add_warn(chat_id, user_id, bot.id, reason)
    await db.log(
        "violation",
        chat_id=chat_id,
        user_id=user_id,
        admin_id=bot.id,
        details=reason,
    )

    full = message.from_user.full_name
    if warns >= cfg.warn_limit:
        until = datetime.now(timezone.utc) + timedelta(hours=cfg.mute_hours)
        try:
            await bot.restrict_chat_member(
                chat_id,
                user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until,
            )
            await db.add_ban(
                chat_id, user_id, bot.id, "mute", "auto: лимит варнов",
                int(until.timestamp()),
            )
            await db.clear_warns(chat_id, user_id)
            await db.log(
                "auto_mute",
                chat_id=chat_id,
                user_id=user_id,
                admin_id=bot.id,
                details=f"{cfg.mute_hours}h",
            )
            await message.answer(
                f"⛔ {full}: достигнут лимит варнов ({cfg.warn_limit}). "
                f"Мут на {cfg.mute_hours} ч."
            )
        except Exception as exc:
            log.error("restrict_chat_member: %s", exc)
    else:
        await message.answer(
            f"⚠️ {full}, нарушение: {reason}. Варн {warns}/{cfg.warn_limit}."
        )


@router.message(F.chat.type.in_(GROUP_TYPES), AntiSpamFilter())
async def on_spam(message: Message, bot: Bot, reason: str) -> None:
    await _auto_punish(message, bot, reason)


@router.message(F.chat.type.in_(GROUP_TYPES), LinksFilter())
async def on_link(message: Message, bot: Bot, reason: str) -> None:
    await _auto_punish(message, bot, reason)


@router.message(F.chat.type.in_(GROUP_TYPES), BadWordsFilter())
async def on_badword(message: Message, bot: Bot, reason: str) -> None:
    await _auto_punish(message, bot, reason)


@router.message(F.new_chat_members)
async def on_join(message: Message) -> None:
    cfg = await db.get_settings(message.chat.id, message.chat.title or "")
    for m in message.new_chat_members or []:
        await db.upsert_user(m.id, m.username, m.full_name)
        await db.log(
            "join", chat_id=message.chat.id, user_id=m.id, details=m.full_name
        )
        if cfg.welcome_text:
            await message.answer(
                cfg.welcome_text.replace("{name}", m.full_name)
            )


@router.message(F.left_chat_member)
async def on_leave(message: Message) -> None:
    m = message.left_chat_member
    if m is None:
        return
    await db.log("leave", chat_id=message.chat.id, user_id=m.id, details=m.full_name)


@router.message(F.chat.type.in_(GROUP_TYPES))
async def cache_user(message: Message) -> None:
    if message.from_user and not message.from_user.is_bot:
        await db.upsert_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name,
        )
