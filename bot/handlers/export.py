"""Экспорт заказов в формат .docx (python-docx)."""

from __future__ import annotations

import logging

from telebot import TeleBot
from telebot.types import CallbackQuery, Message

from bot.database import get_db
from bot.export_docx import export_orders_to_docx
from bot.keyboards import export_period_keyboard
from bot.utils import admin_only

logger = logging.getLogger(__name__)


def register(bot: TeleBot) -> None:

    @bot.message_handler(commands=["export"])
    @admin_only
    def cmd_export(message: Message) -> None:
        bot.send_message(
            message.chat.id,
            "📤 <b>Экспорт заказов в .docx</b>\n\n"
            "Выберите период:",
            reply_markup=export_period_keyboard(),
            parse_mode="HTML",
        )

    @bot.message_handler(func=lambda m: m.text == "📤 Экспорт")
    @admin_only
    def kb_export(message: Message) -> None:
        cmd_export(message)

    @bot.callback_query_handler(
        func=lambda c: c.data and c.data.startswith("export:"))
    @admin_only
    def cb_export(callback: CallbackQuery) -> None:
        days = int(callback.data.split(":")[1])
        bot.answer_callback_query(callback.id, "Готовлю файл…")
        try:
            db = get_db()
            content, filename = export_orders_to_docx(db, days=days)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Не удалось сформировать .docx: %s", exc)
            bot.send_message(
                callback.message.chat.id,
                f"❌ Ошибка при формировании отчёта: {exc}",
            )
            return
        bot.send_document(
            callback.message.chat.id, document=(filename, content),
            caption=(f"📄 Отчёт за {days} дн." if days
                     else "📄 Отчёт за всё время"),
        )
        db = get_db()
        db.log_action(
            admin_id=callback.from_user.id, action="export_docx",
            target=filename, payload=f"days={days}",
        )
