"""Личные сообщения и массовая рассылка клиентам."""

from __future__ import annotations

import logging
import time

from telebot import TeleBot
from telebot.types import Message

from bot.database import get_db
from bot.utils import admin_only

logger = logging.getLogger(__name__)

_pending_broadcast: dict[int, bool] = {}


def _do_broadcast(bot: TeleBot, message: Message, text: str) -> None:
    if not text.strip():
        bot.reply_to(message, "Пустой текст рассылки.")
        return
    db = get_db()
    ids = db.list_client_ids()
    if not ids:
        bot.reply_to(
            message,
            "Нет клиентов для рассылки. Клиенты регистрируются, "
            "когда впервые пишут боту, либо импортируются с заказами.",
        )
        return
    status = bot.send_message(
        message.chat.id,
        f"⏳ Рассылка запущена ({len(ids)} получателей)…",
    )
    sent = failed = 0
    for uid in ids:
        try:
            bot.send_message(
                uid, f"💬 Сообщение от магазина:\n\n{text}")
            sent += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            logger.warning("Не удалось отправить %s: %s", uid, exc)
        time.sleep(0.05)
    db.log_action(
        admin_id=message.from_user.id, action="broadcast",
        target=f"sent={sent},failed={failed}", payload=text[:200],
    )
    try:
        bot.edit_message_text(
            f"✅ Рассылка завершена.\nДоставлено: {sent}\nОшибки: {failed}",
            chat_id=status.chat.id, message_id=status.message_id,
        )
    except Exception:  # noqa: BLE001
        pass


def register(bot: TeleBot) -> None:

    @bot.message_handler(commands=["send"])
    @admin_only
    def cmd_send(message: Message) -> None:
        parts = (message.text or "").split(maxsplit=2)
        if len(parts) < 3 or not parts[1].lstrip("-").isdigit():
            bot.reply_to(
                message,
                "Использование: /send &lt;telegram_id&gt; &lt;текст&gt;",
                parse_mode="HTML",
            )
            return
        user_id = int(parts[1])
        text = parts[2]
        db = get_db()
        if db.is_blocked(user_id):
            bot.reply_to(message,
                         "Пользователь в чёрном списке — отправка запрещена.")
            return
        try:
            bot.send_message(user_id,
                             f"💬 Сообщение от магазина:\n\n{text}")
            db.log_action(
                admin_id=message.from_user.id, action="send_personal",
                target=str(user_id), payload=text[:200],
            )
            bot.reply_to(message, "✅ Сообщение отправлено.")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ошибка отправки %s: %s", user_id, exc)
            bot.reply_to(message, f"❌ Не удалось отправить: {exc}")

    @bot.message_handler(commands=["send_all"])
    @admin_only
    def cmd_send_all(message: Message) -> None:
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) > 1 and parts[1].strip():
            _do_broadcast(bot, message, parts[1].strip())
            return
        _pending_broadcast[message.from_user.id] = True
        bot.reply_to(
            message,
            "✏️ Введите текст для массовой рассылки всем клиентам.\n"
            "Команда /cancel прервёт рассылку.",
        )

    @bot.message_handler(func=lambda m: m.text == "📣 Рассылка")
    @admin_only
    def kb_broadcast(message: Message) -> None:
        _pending_broadcast[message.from_user.id] = True
        bot.reply_to(message,
                     "✏️ Введите текст для массовой рассылки (или /cancel).")

    @bot.message_handler(
        func=lambda m: m.from_user
        and m.from_user.id in _pending_broadcast
        and (m.text or "") == "/cancel")
    @admin_only
    def cancel(message: Message) -> None:
        _pending_broadcast.pop(message.from_user.id, None)
        bot.reply_to(message, "Рассылка отменена.")

    @bot.message_handler(
        func=lambda m: m.from_user
        and m.from_user.id in _pending_broadcast)
    @admin_only
    def text_broadcast(message: Message) -> None:
        _pending_broadcast.pop(message.from_user.id, None)
        _do_broadcast(bot, message, message.text or "")
