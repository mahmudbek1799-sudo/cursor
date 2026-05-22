"""Команды /start и /help, обработка кнопки «Помощь»."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.database.db import get_db
from bot.keyboards.admin import main_menu_keyboard

router = Router(name="common")


HELP_TEXT = (
    "<b>Telegram-бот администратора мебельного магазина</b>\n\n"
    "<b>Основные команды:</b>\n"
    "• /start — главное меню\n"
    "• /help — эта справка\n"
    "• /orders [статус] — список заказов (new/confirmed/in_delivery/completed/cancelled/all)\n"
    "• /order &lt;id&gt; — карточка конкретного заказа\n"
    "• /stats — сводная статистика и дашборд\n"
    "• /sync — принудительная синхронизация с сайтом\n"
    "• /block &lt;telegram_id&gt; [причина] — занести пользователя в чёрный список\n"
    "• /unblock &lt;telegram_id&gt; — снять блокировку\n"
    "• /blocked — список заблокированных\n"
    "• /send &lt;telegram_id&gt; &lt;текст&gt; — отправить личное сообщение клиенту\n"
    "• /send_all &lt;текст&gt; — рассылка всем клиентам (кроме заблокированных)\n"
    "• /log — последние действия администратора\n\n"
    "<b>Управление статусом заказа</b> доступно через inline-кнопки "
    "в карточке заказа."
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    db = get_db()
    user = message.from_user
    await db.log_action(
        admin_id=user.id if user else 0,
        action="start",
        target=user.username or "",
    )
    await message.answer(
        "👋 <b>Добро пожаловать в панель администратора мебельного магазина!</b>\n\n"
        "Бот автоматически принимает заказы с сайта, уведомляет вас и помогает управлять "
        "продажами. Выберите нужное действие в меню ниже или используйте команду /help.",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML")
