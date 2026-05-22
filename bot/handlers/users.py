"""Управление клиентами и чёрным списком."""

from __future__ import annotations

import logging
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.database.db import get_db

logger = logging.getLogger(__name__)
router = Router(name="users")


@router.message(Command("block"))
async def cmd_block(message: Message, command: CommandObject) -> None:
    args = (command.args or "").strip().split(maxsplit=1)
    if not args or not args[0].lstrip("-").isdigit():
        await message.answer("Использование: /block &lt;telegram_id&gt; [причина]", parse_mode="HTML")
        return
    user_id = int(args[0])
    reason = args[1] if len(args) > 1 else "без указания причины"
    db = get_db()
    await db.block_user(user_id, reason)
    await db.log_action(
        admin_id=message.from_user.id,
        action="block_user",
        target=str(user_id),
        payload=reason,
    )
    await message.answer(
        f"🚫 Пользователь <code>{user_id}</code> заблокирован.\nПричина: {escape(reason)}",
        parse_mode="HTML",
    )


@router.message(Command("unblock"))
async def cmd_unblock(message: Message, command: CommandObject) -> None:
    arg = (command.args or "").strip()
    if not arg.lstrip("-").isdigit():
        await message.answer("Использование: /unblock &lt;telegram_id&gt;", parse_mode="HTML")
        return
    user_id = int(arg)
    db = get_db()
    ok = await db.unblock_user(user_id)
    if ok:
        await db.log_action(
            admin_id=message.from_user.id,
            action="unblock_user",
            target=str(user_id),
        )
        await message.answer(f"✅ Пользователь <code>{user_id}</code> разблокирован.",
                             parse_mode="HTML")
    else:
        await message.answer("Пользователь не найден в чёрном списке.")


@router.message(Command("blocked"))
@router.message(F.text == "🚫 Чёрный список")
async def cmd_blocked(message: Message) -> None:
    db = get_db()
    blocked = await db.list_blocked()
    if not blocked:
        await message.answer("Чёрный список пуст.")
        return
    lines = ["<b>🚫 Чёрный список:</b>", ""]
    for item in blocked:
        lines.append(
            f"• <code>{item.user_id}</code> — {escape(item.reason or 'без причины')} "
            f"({item.blocked_at})"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("log"))
async def cmd_log(message: Message) -> None:
    db = get_db()
    actions = await db.recent_actions(limit=20)
    if not actions:
        await message.answer("Журнал пуст.")
        return
    lines = ["<b>🗂 Последние действия:</b>", ""]
    for a in actions:
        lines.append(
            f"{escape(a['created_at'])} | <code>{a['admin_id']}</code> | "
            f"{escape(a['action'])} | {escape(a['target'])} {escape(a['payload'])}"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")
