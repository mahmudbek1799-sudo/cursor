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
    "<b>Заказы:</b>\n"
    "• /orders [active|done|all|&lt;статус&gt;] — список заказов\n"
    "• /order &lt;id&gt; — карточка заказа (статусы, контакты, чат)\n"
    "• /sync — принудительный приём новых заказов с сайта\n"
    "• /parse_site — спарсить каталог сайта без API\n\n"
    "<b>Товары:</b>\n"
    "• /products — каталог с пагинацией\n"
    "• /product &lt;id|sku&gt; — карточка товара\n"
    "• /add_product — мастер добавления товара\n"
    "• /del_product &lt;id|sku&gt; — удалить товар\n"
    "• /price &lt;id|sku&gt; &lt;цена&gt; — изменить цену\n\n"
    "<b>Скидки:</b>\n"
    "• /discounts — все активные скидки\n"
    "• /discount &lt;sku|id|all&gt; &lt;percent|fixed&gt; &lt;значение&gt; [дней]\n"
    "   Пример: /discount all percent 10 7 — −10% на всё на 7 дней\n\n"
    "<b>Аналитика и аудит:</b>\n"
    "• /stats — сводная статистика\n"
    "• /dashboard — график продаж за 7 дней\n"
    "• /log — последние действия администратора\n\n"
    "<b>Клиенты:</b>\n"
    "• /block &lt;telegram_id&gt; [причина] — добавить в чёрный список\n"
    "• /unblock &lt;telegram_id&gt; — снять блокировку\n"
    "• /blocked — посмотреть чёрный список\n"
    "• /send &lt;telegram_id&gt; &lt;текст&gt; — личное сообщение\n"
    "• /send_all &lt;текст&gt; — массовая рассылка\n\n"
    "<b>Прочее:</b>\n"
    "• /start — главное меню\n"
    "• /help — эта справка"
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
