"""Чёрный список и журнал действий администратора."""

from __future__ import annotations

import logging
from html import escape

from telebot import TeleBot
from telebot.types import Message

from bot.database import get_db
from bot.utils import admin_only

logger = logging.getLogger(__name__)


def register(bot: TeleBot) -> None:

    @bot.message_handler(commands=["block"])
    @admin_only
    def cmd_block(message: Message) -> None:
        parts = (message.text or "").split(maxsplit=2)
        if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
            bot.reply_to(
                message,
                "Использование: /block &lt;telegram_id&gt; [причина]",
                parse_mode="HTML",
            )
            return
        user_id = int(parts[1])
        reason = parts[2] if len(parts) > 2 else "без указания причины"
        db = get_db()
        db.block_user(user_id, reason)
        db.log_action(
            admin_id=message.from_user.id, action="block_user",
            target=str(user_id), payload=reason,
        )
        bot.reply_to(
            message,
            f"🚫 Пользователь <code>{user_id}</code> заблокирован.\n"
            f"Причина: {escape(reason)}",
            parse_mode="HTML",
        )

    @bot.message_handler(commands=["unblock"])
    @admin_only
    def cmd_unblock(message: Message) -> None:
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip().lstrip("-").isdigit():
            bot.reply_to(
                message,
                "Использование: /unblock &lt;telegram_id&gt;",
                parse_mode="HTML",
            )
            return
        user_id = int(parts[1])
        db = get_db()
        if db.unblock_user(user_id):
            db.log_action(
                admin_id=message.from_user.id, action="unblock_user",
                target=str(user_id),
            )
            bot.reply_to(
                message,
                f"✅ Пользователь <code>{user_id}</code> разблокирован.",
                parse_mode="HTML",
            )
        else:
            bot.reply_to(message,
                         "Пользователь не найден в чёрном списке.")

    @bot.message_handler(commands=["blocked"])
    @admin_only
    def cmd_blocked(message: Message) -> None:
        db = get_db()
        blocked = db.list_blocked()
        if not blocked:
            bot.reply_to(message, "Чёрный список пуст.")
            return
        lines = ["<b>🚫 Чёрный список:</b>", ""]
        for item in blocked:
            lines.append(
                f"• <code>{item.user_id}</code> — "
                f"{escape(item.reason or 'без причины')} "
                f"({item.blocked_at})"
            )
        bot.reply_to(message, "\n".join(lines), parse_mode="HTML")

    @bot.message_handler(func=lambda m: m.text == "🚫 Чёрный список")
    @admin_only
    def kb_blocked(message: Message) -> None:
        cmd_blocked(message)

    @bot.message_handler(commands=["log"])
    @admin_only
    def cmd_log(message: Message) -> None:
        db = get_db()
        actions = db.recent_actions(limit=20)
        if not actions:
            bot.reply_to(message, "Журнал пуст.")
            return
        lines = ["<b>🗂 Последние действия:</b>", ""]
        for a in actions:
            lines.append(
                f"{escape(a['created_at'])} | <code>{a['admin_id']}</code> | "
                f"{escape(a['action'])} | {escape(a['target'])} "
                f"{escape(a['payload'])}"
            )
        bot.reply_to(message, "\n".join(lines), parse_mode="HTML")
