"""Административные команды.

Поддерживаются: /mute, /unmute, /warn, /kick, /ban, /unban, /info,
/stats, /export_logs.

Команды работают только в группах и только от пользователей со статусом
``administrator`` / ``creator`` (см. ``utils.decorators.admin_only``).
Цель действия указывается:
    * ответом на сообщение пользователя (reply), либо
    * первым аргументом @username, либо
    * числовым user_id.

Длительность для /mute и /ban принимается в формате ``10m`` / ``2h`` /
``7d``; если не указана — бессрочно.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, ChatPermissions, Message

from database import db
from utils import admin_only, get_logger, group_only

router = Router(name="admins")
log = get_logger(__name__)

DURATION_RE = re.compile(r"^(\d+)\s*([smhd])$", re.IGNORECASE)
UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_duration(token: str) -> int | None:
    """Преобразует строку «10m» → секунды. Возвращает None при отсутствии."""
    if not token:
        return None
    m = DURATION_RE.match(token)
    if not m:
        return None
    qty, unit = int(m.group(1)), m.group(2).lower()
    return qty * UNIT_SECONDS[unit]


async def resolve_target(
    message: Message, args: str | None, bot: Bot
) -> tuple[int | None, str, str]:
    """Возвращает (user_id, отображаемое_имя, остаток_аргументов).

    Поддерживает три способа указания цели: reply, @username, числовой ID.
    """
    if message.reply_to_message and message.reply_to_message.from_user:
        u = message.reply_to_message.from_user
        return u.id, u.full_name, (args or "").strip()

    if not args:
        return None, "", ""

    tokens = args.split(maxsplit=1)
    head, rest = tokens[0], tokens[1] if len(tokens) > 1 else ""

    if head.startswith("@"):
        username = head.lstrip("@")
        try:
            cur = await db.conn.execute(
                "SELECT user_id, full_name FROM users WHERE username = ?",
                (username,),
            )
            row = await cur.fetchone()
            if row:
                return int(row["user_id"]), row["full_name"], rest
        except Exception:
            pass
        return None, head, rest

    if head.lstrip("-").isdigit():
        uid = int(head)
        cached = await db.get_user(uid)
        return uid, (cached["full_name"] if cached else str(uid)), rest

    return None, head, rest


# ============================================================ /warn
@router.message(Command("warn"))
@group_only
@admin_only
async def cmd_warn(message: Message, command: CommandObject, bot: Bot) -> None:
    uid, name, reason = await resolve_target(message, command.args, bot)
    if uid is None:
        await message.reply("Использование: /warn @user причина (или reply).")
        return
    cfg = await db.get_settings(message.chat.id, message.chat.title or "")
    reason = reason or "—"
    warns = await db.add_warn(message.chat.id, uid, message.from_user.id, reason)
    await db.log(
        "admin_warn",
        chat_id=message.chat.id,
        user_id=uid,
        admin_id=message.from_user.id,
        details=reason,
    )
    if warns >= cfg.warn_limit:
        until = datetime.now(timezone.utc) + timedelta(hours=cfg.mute_hours)
        try:
            await bot.restrict_chat_member(
                message.chat.id, uid,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until,
            )
            await db.add_ban(
                message.chat.id, uid, message.from_user.id, "mute",
                "лимит варнов", int(until.timestamp()),
            )
            await db.clear_warns(message.chat.id, uid)
            await message.reply(
                f"⛔ {name}: достигнут лимит. Мут на {cfg.mute_hours} ч."
            )
        except Exception as exc:
            await message.reply(f"Не удалось замутить: {exc}")
    else:
        await message.reply(
            f"⚠️ {name} получает варн ({warns}/{cfg.warn_limit}). Причина: {reason}"
        )


# ============================================================ /mute
@router.message(Command("mute"))
@group_only
@admin_only
async def cmd_mute(message: Message, command: CommandObject, bot: Bot) -> None:
    uid, name, tail = await resolve_target(message, command.args, bot)
    if uid is None:
        await message.reply("Использование: /mute @user 2h причина (или reply).")
        return

    parts = tail.split(maxsplit=1)
    duration_token = parts[0] if parts else ""
    seconds = parse_duration(duration_token)
    reason = parts[1] if seconds is not None and len(parts) > 1 else tail
    if seconds is None and parts and not DURATION_RE.match(duration_token):
        reason = tail

    until_dt = (
        datetime.now(timezone.utc) + timedelta(seconds=seconds) if seconds else None
    )
    try:
        await bot.restrict_chat_member(
            message.chat.id, uid,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_dt,
        )
    except Exception as exc:
        await message.reply(f"Не удалось замутить: {exc}")
        return
    await db.add_ban(
        message.chat.id, uid, message.from_user.id, "mute",
        reason or "—", int(until_dt.timestamp()) if until_dt else 0,
    )
    await db.log(
        "admin_mute",
        chat_id=message.chat.id, user_id=uid,
        admin_id=message.from_user.id,
        details=f"{seconds or 'inf'}s; {reason or '—'}",
    )
    suffix = f" на {duration_token}" if seconds else " (бессрочно)"
    await message.reply(f"🔇 {name} замучен{suffix}. Причина: {reason or '—'}")


# ============================================================ /unmute
@router.message(Command("unmute"))
@group_only
@admin_only
async def cmd_unmute(message: Message, command: CommandObject, bot: Bot) -> None:
    uid, name, _ = await resolve_target(message, command.args, bot)
    if uid is None:
        await message.reply("Использование: /unmute @user (или reply).")
        return
    try:
        await bot.restrict_chat_member(
            message.chat.id, uid,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
    except Exception as exc:
        await message.reply(f"Не удалось снять мут: {exc}")
        return
    await db.deactivate_bans(message.chat.id, uid, "mute")
    await db.log(
        "admin_unmute", chat_id=message.chat.id, user_id=uid,
        admin_id=message.from_user.id,
    )
    await message.reply(f"🔈 Мут снят с {name}.")


# ============================================================ /kick
@router.message(Command("kick"))
@group_only
@admin_only
async def cmd_kick(message: Message, command: CommandObject, bot: Bot) -> None:
    uid, name, reason = await resolve_target(message, command.args, bot)
    if uid is None:
        await message.reply("Использование: /kick @user причина (или reply).")
        return
    try:
        await bot.ban_chat_member(message.chat.id, uid)
        await bot.unban_chat_member(message.chat.id, uid, only_if_banned=True)
    except Exception as exc:
        await message.reply(f"Не удалось кикнуть: {exc}")
        return
    await db.log(
        "admin_kick", chat_id=message.chat.id, user_id=uid,
        admin_id=message.from_user.id, details=reason or "—",
    )
    await message.reply(f"👢 {name} исключён. Причина: {reason or '—'}")


# ============================================================ /ban
@router.message(Command("ban"))
@group_only
@admin_only
async def cmd_ban(message: Message, command: CommandObject, bot: Bot) -> None:
    uid, name, tail = await resolve_target(message, command.args, bot)
    if uid is None:
        await message.reply("Использование: /ban @user [10m|2h|7d] причина.")
        return

    parts = tail.split(maxsplit=1)
    duration_token = parts[0] if parts else ""
    seconds = parse_duration(duration_token)
    reason = parts[1] if seconds is not None and len(parts) > 1 else tail
    if seconds is None and parts and not DURATION_RE.match(duration_token):
        reason = tail

    until_dt = (
        datetime.now(timezone.utc) + timedelta(seconds=seconds) if seconds else None
    )
    try:
        await bot.ban_chat_member(
            message.chat.id, uid, until_date=until_dt,
        )
    except Exception as exc:
        await message.reply(f"Не удалось забанить: {exc}")
        return
    await db.add_ban(
        message.chat.id, uid, message.from_user.id, "ban",
        reason or "—", int(until_dt.timestamp()) if until_dt else 0,
    )
    await db.log(
        "admin_ban", chat_id=message.chat.id, user_id=uid,
        admin_id=message.from_user.id,
        details=f"{seconds or 'inf'}s; {reason or '—'}",
    )
    suffix = f" на {duration_token}" if seconds else " (навсегда)"
    await message.reply(f"⛔ {name} забанен{suffix}. Причина: {reason or '—'}")


# ============================================================ /unban
@router.message(Command("unban"))
@group_only
@admin_only
async def cmd_unban(message: Message, command: CommandObject, bot: Bot) -> None:
    uid, name, _ = await resolve_target(message, command.args, bot)
    if uid is None:
        await message.reply("Использование: /unban @user (или ID).")
        return
    try:
        await bot.unban_chat_member(message.chat.id, uid, only_if_banned=True)
    except Exception as exc:
        await message.reply(f"Не удалось разбанить: {exc}")
        return
    await db.deactivate_bans(message.chat.id, uid, "ban")
    await db.log(
        "admin_unban", chat_id=message.chat.id, user_id=uid,
        admin_id=message.from_user.id,
    )
    await message.reply(f"✅ {name} разбанен.")


# ============================================================ /info
@router.message(Command("info"))
@group_only
@admin_only
async def cmd_info(message: Message, command: CommandObject, bot: Bot) -> None:
    uid, name, _ = await resolve_target(message, command.args, bot)
    if uid is None:
        await message.reply("Использование: /info @user (или reply).")
        return
    warns = await db.count_warns(message.chat.id, uid)
    cur = await db.conn.execute(
        "SELECT username, first_seen, last_seen FROM users WHERE user_id = ?",
        (uid,),
    )
    row = await cur.fetchone()
    username = ("@" + row["username"]) if row and row["username"] else "—"
    first = (
        datetime.utcfromtimestamp(row["first_seen"]).strftime("%Y-%m-%d")
        if row else "—"
    )

    cur = await db.conn.execute(
        "SELECT kind, until_ts FROM bans WHERE chat_id = ? AND user_id = ? AND active = 1",
        (message.chat.id, uid),
    )
    actives = await cur.fetchall()
    active_str = ", ".join(
        f"{b['kind']}→{datetime.utcfromtimestamp(b['until_ts']).strftime('%Y-%m-%d %H:%M') if b['until_ts'] else '∞'}"
        for b in actives
    ) or "нет"

    await message.reply(
        f"🪪 <b>{name}</b>\n"
        f"ID: <code>{uid}</code>\n"
        f"Username: {username}\n"
        f"Замечен с: {first}\n"
        f"Варны: <b>{warns}</b>\n"
        f"Активные санкции: {active_str}"
    )


# ============================================================ /stats
@router.message(Command("stats"))
@group_only
@admin_only
async def cmd_stats(message: Message, bot: Bot) -> None:
    s = await db.stats(message.chat.id)
    await message.reply(
        "📊 <b>Статистика группы</b>\n"
        f"Нарушения: {s['violations']}\n"
        f"Варны (всего записей): {s['warns']}\n"
        f"Муты: {s['mutes']}\n"
        f"Баны: {s['bans']}"
    )


# ============================================================ /export_logs
@router.message(Command("export_logs"))
@group_only
@admin_only
async def cmd_export(message: Message, bot: Bot) -> None:
    rows = list(await db.fetch_logs(message.chat.id, limit=5000))
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["datetime_utc", "action", "user_id", "admin_id", "details"])
    for r in rows:
        writer.writerow([
            datetime.utcfromtimestamp(r["created"]).isoformat(sep=" "),
            r["action"],
            r["user_id"] or "",
            r["admin_id"] or "",
            (r["details"] or "").replace("\n", " "),
        ])
    data = buf.getvalue().encode("utf-8")
    fname = f"logs_{message.chat.id}_{int(datetime.utcnow().timestamp())}.csv"
    await message.reply_document(
        BufferedInputFile(data, filename=fname),
        caption=f"Журнал из {len(rows)} событий.",
    )
    await db.log(
        "admin_export", chat_id=message.chat.id,
        admin_id=message.from_user.id, details=f"rows={len(rows)}",
    )


# ============================================================ /help
@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.reply(
        "<b>Команды администратора</b>\n"
        "/warn @u причина — варн\n"
        "/mute @u 2h причина — мут\n"
        "/unmute @u — снять мут\n"
        "/ban @u 7d причина — бан\n"
        "/unban @u — разбан\n"
        "/kick @u — исключить\n"
        "/info @u — карточка пользователя\n"
        "/stats — статистика группы\n"
        "/export_logs — выгрузить журнал CSV\n"
        "/setup — меню настроек группы\n"
    )


# ============================================================ /start
@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.reply(
        "Привет! Я бот-администратор группы. Добавьте меня в чат и выдайте "
        "права администратора (удаление сообщений, ограничение участников). "
        "Подробности — /help."
    )
