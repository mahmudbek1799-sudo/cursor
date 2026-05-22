"""Команды рассылки сообщений клиентам."""

from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from bot.database.db import get_db

logger = logging.getLogger(__name__)
router = Router(name="broadcast")


class Broadcast(StatesGroup):
    waiting_text = State()


@router.message(Command("send"))
async def cmd_send(message: Message, command: CommandObject) -> None:
    parts = (command.args or "").strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[0].lstrip("-").isdigit():
        await message.answer(
            "Использование: /send &lt;telegram_id&gt; &lt;текст&gt;",
            parse_mode="HTML",
        )
        return
    user_id = int(parts[0])
    text = parts[1]
    db = get_db()
    if await db.is_blocked(user_id):
        await message.answer("Пользователь в чёрном списке — отправка запрещена.")
        return
    try:
        await message.bot.send_message(user_id, f"💬 Сообщение от магазина:\n\n{text}")
        await db.log_action(
            admin_id=message.from_user.id,
            action="send_personal",
            target=str(user_id),
            payload=text[:200],
        )
        await message.answer("✅ Сообщение отправлено.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ошибка отправки сообщения %s: %s", user_id, exc)
        await message.answer(f"❌ Не удалось отправить сообщение: {exc}")


@router.message(Command("send_all"))
async def cmd_send_all(message: Message, command: CommandObject, state: FSMContext) -> None:
    text = (command.args or "").strip()
    if text:
        await _perform_broadcast(message, text)
        return
    await state.set_state(Broadcast.waiting_text)
    await message.answer(
        "✏️ Введите текст для массовой рассылки всем клиентам.\n"
        "Команда /cancel прервёт рассылку."
    )


@router.message(F.text == "📣 Рассылка")
async def kb_broadcast(message: Message, state: FSMContext) -> None:
    await state.set_state(Broadcast.waiting_text)
    await message.answer("✏️ Введите текст для массовой рассылки (или /cancel).")


@router.message(Broadcast.waiting_text, Command("cancel"))
async def broadcast_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Рассылка отменена.")


@router.message(Broadcast.waiting_text)
async def broadcast_text(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _perform_broadcast(message, message.text or "")


async def _perform_broadcast(message: Message, text: str) -> None:
    if not text.strip():
        await message.answer("Пустой текст рассылки.")
        return
    db = get_db()
    ids = await db.list_client_ids()
    if not ids:
        await message.answer(
            "Нет клиентов для рассылки. Клиенты регистрируются, когда впервые "
            "пишут боту, или импортируются вместе с заказами с сайта."
        )
        return
    sent, failed = 0, 0
    status = await message.answer(f"⏳ Рассылка запущена ({len(ids)} получателей)…")
    for uid in ids:
        try:
            await message.bot.send_message(uid, f"💬 Сообщение от магазина:\n\n{text}")
            sent += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            logger.warning("Не удалось отправить %s: %s", uid, exc)
        await asyncio.sleep(0.05)  # Telegram rate-limit friendly
    await db.log_action(
        admin_id=message.from_user.id,
        action="broadcast",
        target=f"sent={sent},failed={failed}",
        payload=text[:200],
    )
    await status.edit_text(
        f"✅ Рассылка завершена.\nДоставлено: {sent}\nОшибки: {failed}"
    )
