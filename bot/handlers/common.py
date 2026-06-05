"""Команды /start, /help."""

from __future__ import annotations

import logging

from telebot import TeleBot
from telebot.types import Message

from bot.database import get_db
from bot.keyboards import main_menu_keyboard
from bot.utils import admin_only

logger = logging.getLogger(__name__)


HELP_TEXT = (
    "<b>Telegram-бот администратора мебельного магазина</b>\n\n"
    "<b>Заказы:</b>\n"
    "• /orders [active|done|all|&lt;статус&gt;] — список заказов\n"
    "• /order &lt;id&gt; — карточка заказа\n"
    "• /sync — принудительный приём заказов с сайта\n"
    "• /parse_site — парсинг каталога без API\n"
    "• /export — экспорт заказов в .docx\n\n"
    "<b>Товары:</b>\n"
    "• /products — каталог с пагинацией\n"
    "• /product &lt;id|sku&gt; — карточка товара\n"
    "• /add_product — мастер добавления товара\n"
    "• /del_product &lt;id|sku&gt; — удалить товар\n"
    "• /price &lt;id|sku&gt; &lt;цена&gt; — изменить цену\n\n"
    "<b>Скидки:</b>\n"
    "• /discounts — все активные скидки\n"
    "• /discount &lt;sku|id|all&gt; &lt;percent|fixed&gt; &lt;значение&gt; [дней]\n\n"
    "<b>Аналитика и аудит:</b>\n"
    "• /stats — сводная статистика\n"
    "• /dashboard — график продаж за 7 дней\n"
    "• /log — последние действия администратора\n\n"
    "<b>Клиенты:</b>\n"
    "• /block &lt;telegram_id&gt; [причина], /unblock &lt;id&gt;, /blocked\n"
    "• /send &lt;telegram_id&gt; &lt;текст&gt; — личное сообщение\n"
    "• /send_all &lt;текст&gt; — массовая рассылка"
)


def register(bot: TeleBot) -> None:

    @bot.message_handler(commands=["start"])
    @admin_only
    def cmd_start(message: Message) -> None:
        db = get_db()
        db.log_action(
            admin_id=message.from_user.id,
            action="start",
            target=message.from_user.username or "",
        )
        bot.send_message(
            message.chat.id,
            "👋 <b>Добро пожаловать в панель администратора мебельного "
            "магазина!</b>\n\nБот автоматически принимает заказы с "
            "сайта, уведомляет вас и помогает управлять продажами. "
            "Выберите нужное действие в меню или используйте /help.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )

    @bot.message_handler(commands=["help"])
    @admin_only
    def cmd_help(message: Message) -> None:
        bot.send_message(message.chat.id, HELP_TEXT, parse_mode="HTML")

    @bot.message_handler(func=lambda m: m.text == "❓ Помощь")
    @admin_only
    def kb_help(message: Message) -> None:
        bot.send_message(message.chat.id, HELP_TEXT, parse_mode="HTML")
