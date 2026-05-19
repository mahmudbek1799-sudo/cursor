"""Команда /setup и обработка inline-меню настроек группы.

Меню позволяет администратору группы:

* включать/выключать модули антиспама, антимата и антиссылок;
* менять лимит варнов;
* редактировать список запрещённых слов и доверенных доменов
  (значения вводятся одним сообщением, через запятую) — используется
  механизм FSM aiogram.
"""

from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from database import db
from keyboards import back_kb, setup_menu, toggle_kb
from utils import admin_only, group_only

router = Router(name="setup")


class SetupStates(StatesGroup):
    waiting_words = State()
    waiting_domains = State()
    waiting_warns = State()


def _status_text(cfg) -> str:
    return (
        "⚙️ <b>Настройки группы</b>\n"
        f"Антиспам: {'✅' if cfg.antispam_on else '❌'} "
        f"(<code>{cfg.antispam_msgs}/{cfg.antispam_seconds}c</code>)\n"
        f"Антиссылки: {'✅' if cfg.antilinks_on else '❌'}\n"
        f"Антимат: {'✅' if cfg.antibadwords_on else '❌'}\n"
        f"Лимит варнов: <b>{cfg.warn_limit}</b> → мут на {cfg.mute_hours} ч.\n"
        f"Слов в чёрном списке: {len(cfg.bad_words)}\n"
        f"Доверенных доменов: {len(cfg.trusted_domains)}"
    )


@router.message(Command("setup"))
@group_only
@admin_only
async def cmd_setup(message: Message, bot: Bot) -> None:
    cfg = await db.get_settings(message.chat.id, message.chat.title or "")
    await message.reply(_status_text(cfg), reply_markup=setup_menu())


@router.callback_query(F.data == "setup:close")
async def cb_close(cb: CallbackQuery) -> None:
    try:
        await cb.message.delete()
    except Exception:
        pass
    await cb.answer()


@router.callback_query(F.data == "setup:back")
async def cb_back(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    cfg = await db.get_settings(cb.message.chat.id, cb.message.chat.title or "")
    await cb.message.edit_text(_status_text(cfg), reply_markup=setup_menu())
    await cb.answer()


@router.callback_query(F.data.startswith("setup:"))
async def cb_section(cb: CallbackQuery, state: FSMContext) -> None:
    section = cb.data.split(":", 1)[1]
    cfg = await db.get_settings(cb.message.chat.id, cb.message.chat.title or "")

    if section == "antispam":
        await cb.message.edit_text(
            f"Антиспам сейчас: {'включен' if cfg.antispam_on else 'выключен'}.\n"
            f"Лимит: {cfg.antispam_msgs} сообщ. / {cfg.antispam_seconds} c.",
            reply_markup=toggle_kb("antispam_on", cfg.antispam_on),
        )
    elif section == "antilinks":
        await cb.message.edit_text(
            f"Антиссылки: {'включены' if cfg.antilinks_on else 'выключены'}.",
            reply_markup=toggle_kb("antilinks_on", cfg.antilinks_on),
        )
    elif section == "antibadwords":
        await cb.message.edit_text(
            f"Антимат: {'включен' if cfg.antibadwords_on else 'выключен'}.",
            reply_markup=toggle_kb("antibadwords_on", cfg.antibadwords_on),
        )
    elif section == "warns":
        await state.set_state(SetupStates.waiting_warns)
        await cb.message.edit_text(
            f"Текущий лимит варнов: <b>{cfg.warn_limit}</b>.\n"
            "Введите новое целое число (1..10):",
            reply_markup=back_kb(),
        )
    elif section == "words":
        await state.set_state(SetupStates.waiting_words)
        await cb.message.edit_text(
            "Введите список запрещённых слов через запятую.\n"
            f"Сейчас: <code>{', '.join(cfg.bad_words) or '—'}</code>",
            reply_markup=back_kb(),
        )
    elif section == "domains":
        await state.set_state(SetupStates.waiting_domains)
        await cb.message.edit_text(
            "Введите список доверенных доменов через запятую (например: "
            "<code>t.me, youtube.com</code>).\n"
            f"Сейчас: <code>{', '.join(cfg.trusted_domains) or '—'}</code>",
            reply_markup=back_kb(),
        )
    await cb.answer()


@router.callback_query(F.data.startswith("toggle:"))
async def cb_toggle(cb: CallbackQuery) -> None:
    _, field, raw = cb.data.split(":")
    await db.update_setting(cb.message.chat.id, field, int(raw))
    await db.log(
        "settings_change", chat_id=cb.message.chat.id,
        admin_id=cb.from_user.id, details=f"{field}={raw}",
    )
    cfg = await db.get_settings(cb.message.chat.id, cb.message.chat.title or "")
    await cb.message.edit_text(_status_text(cfg), reply_markup=setup_menu())
    await cb.answer("Сохранено.")


@router.message(SetupStates.waiting_warns)
async def st_warns(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit() or not (1 <= int(text) <= 10):
        await message.reply("Нужно целое число от 1 до 10.")
        return
    await db.update_setting(message.chat.id, "warn_limit", int(text))
    await db.log(
        "settings_change", chat_id=message.chat.id,
        admin_id=message.from_user.id, details=f"warn_limit={text}",
    )
    await state.clear()
    cfg = await db.get_settings(message.chat.id, message.chat.title or "")
    await message.reply(_status_text(cfg), reply_markup=setup_menu())


@router.message(SetupStates.waiting_words)
async def st_words(message: Message, state: FSMContext) -> None:
    items = [w.strip().lower() for w in (message.text or "").split(",") if w.strip()]
    await db.update_setting(message.chat.id, "bad_words", items)
    await db.log(
        "settings_change", chat_id=message.chat.id,
        admin_id=message.from_user.id, details=f"bad_words={len(items)}",
    )
    await state.clear()
    cfg = await db.get_settings(message.chat.id, message.chat.title or "")
    await message.reply(_status_text(cfg), reply_markup=setup_menu())


@router.message(SetupStates.waiting_domains)
async def st_domains(message: Message, state: FSMContext) -> None:
    items = [w.strip().lower().lstrip("@") for w in (message.text or "").split(",") if w.strip()]
    await db.update_setting(message.chat.id, "trusted_domains", items)
    await db.log(
        "settings_change", chat_id=message.chat.id,
        admin_id=message.from_user.id, details=f"trusted_domains={len(items)}",
    )
    await state.clear()
    cfg = await db.get_settings(message.chat.id, message.chat.title or "")
    await message.reply(_status_text(cfg), reply_markup=setup_menu())
