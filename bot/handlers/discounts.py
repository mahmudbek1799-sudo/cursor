"""Управление скидками: процентные и фиксированные, на товар или глобальные."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.database.db import get_db
from bot.keyboards.admin import (
    discount_kind_keyboard,
    discounts_list_keyboard,
)
from bot.utils.formatting import format_money

logger = logging.getLogger(__name__)
router = Router(name="discounts")


class NewDiscount(StatesGroup):
    waiting_value = State()
    waiting_days = State()


# ---------------------------------------------------------------------------
# Список скидок
# ---------------------------------------------------------------------------
@router.message(Command("discounts"))
@router.message(F.text == "🏷 Скидки")
async def cmd_discounts(message: Message) -> None:
    db = get_db()
    discounts = await db.list_discounts(only_active=True)
    if not discounts:
        await message.answer(
            "🏷 <b>Активных скидок нет.</b>\n\n"
            "Создайте новую скидку командой\n"
            "<code>/discount &lt;sku|all&gt; &lt;percent|fixed&gt; &lt;значение&gt; [дней]</code>\n\n"
            "Например:\n"
            "• <code>/discount all percent 10 7</code> — −10% на всё на 7 дней\n"
            "• <code>/discount SOFA-001 fixed 5000</code> — минус 5000 ₽ на товар",
            reply_markup=discounts_list_keyboard([]),
            parse_mode="HTML",
        )
        return
    lines = ["🏷 <b>Активные скидки</b>", ""]
    for d in discounts:
        scope = "<i>все товары</i>" if d.product_id is None else f"товар #{d.product_id}"
        period = ""
        if d.valid_to:
            period = f"  до {d.valid_to[:10]}"
        lines.append(f"#{d.id}  •  {d.label}  •  {scope}{period}")
    await message.answer(
        "\n".join(lines),
        reply_markup=discounts_list_keyboard(discounts),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Создание скидки одной командой
# ---------------------------------------------------------------------------
@router.message(Command("discount"))
async def cmd_discount(message: Message, command: CommandObject) -> None:
    parts = (command.args or "").strip().split()
    if len(parts) < 3:
        await message.answer(
            "Использование:\n"
            "<code>/discount &lt;sku|id|all&gt; &lt;percent|fixed&gt; &lt;значение&gt; [дней]</code>",
            parse_mode="HTML",
        )
        return
    target, kind, value_raw, *rest = parts
    if kind not in ("percent", "fixed"):
        await message.answer("Тип скидки должен быть percent или fixed.")
        return
    try:
        value = float(value_raw.replace(",", "."))
    except ValueError:
        await message.answer("Значение скидки должно быть числом.")
        return
    days: int | None = None
    if rest:
        try:
            days = int(rest[0])
            if days < 0:
                raise ValueError
        except ValueError:
            await message.answer("Срок (дней) должен быть неотрицательным целым.")
            return
    db = get_db()
    product_id: int | None
    if target.lower() == "all":
        product_id = None
    elif target.isdigit():
        prod = await db.get_product(int(target))
        if prod is None:
            await message.answer("Товар не найден.")
            return
        product_id = prod.id
    else:
        prod = await db.get_product_by_sku(target)
        if prod is None:
            await message.answer("Товар с таким SKU не найден.")
            return
        product_id = prod.id

    valid_to = None
    if days is not None and days > 0:
        valid_to = (datetime.now() + timedelta(days=days)).isoformat(
            sep=" ", timespec="seconds"
        )
    try:
        did = await db.add_discount(
            kind=kind, value=value, product_id=product_id, valid_to=valid_to
        )
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await db.log_action(
        admin_id=message.from_user.id,
        action="add_discount",
        target=target,
        payload=f"{kind}:{value}:{days or '∞'}",
    )
    scope = "ВСЕ ТОВАРЫ" if product_id is None else f"товар #{product_id}"
    suffix = " (бессрочно)" if not valid_to else f" до {valid_to[:10]}"
    await message.answer(
        f"✅ Создана скидка #{did}: <b>{kind} {value:g}</b> на {scope}{suffix}.",
        parse_mode="HTML",
    )


@router.callback_query(F.data.regexp(r"^discount:off:(\d+)$"))
async def cb_discount_off(callback: CallbackQuery) -> None:
    did = int(callback.data.split(":")[-1])
    db = get_db()
    ok = await db.deactivate_discount(did)
    await db.log_action(
        admin_id=callback.from_user.id,
        action="deactivate_discount",
        target=str(did),
    )
    if ok:
        await callback.answer("Скидка отключена")
    else:
        await callback.answer("Не найдено", show_alert=True)
    # Перерисуем список.
    discounts = await db.list_discounts(only_active=True)
    if not discounts:
        await callback.message.edit_text(
            "🏷 Активных скидок нет.",
            reply_markup=discounts_list_keyboard([]),
            parse_mode="HTML",
        )
        return
    lines = ["🏷 <b>Активные скидки</b>", ""]
    for d in discounts:
        scope = "все товары" if d.product_id is None else f"товар #{d.product_id}"
        period = f" до {d.valid_to[:10]}" if d.valid_to else ""
        lines.append(f"#{d.id} • {d.label} • {scope}{period}")
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=discounts_list_keyboard(discounts),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Создание глобальной скидки через FSM (кнопка из меню)
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "discount:new_global")
async def cb_discount_new_global(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "🏷 Выберите тип глобальной скидки:",
        reply_markup=discount_kind_keyboard(None),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^discount:new:(percent|fixed):(\d+)$"))
async def cb_discount_new_kind(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, kind, target = callback.data.split(":")
    pid = int(target) or None
    await state.set_state(NewDiscount.waiting_value)
    await state.update_data(kind=kind, product_id=pid)
    unit = "%" if kind == "percent" else "₽"
    scope = "глобально" if pid is None else f"для товара #{pid}"
    await callback.message.answer(
        f"Введите размер скидки в {unit} {scope} (или /cancel):"
    )
    await callback.answer()


@router.message(NewDiscount.waiting_value, Command("cancel"))
async def disc_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.")


@router.message(NewDiscount.waiting_value)
async def disc_value(message: Message, state: FSMContext) -> None:
    try:
        value = float((message.text or "").replace(",", ".").strip())
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Значение скидки должно быть положительным числом.")
        return
    await state.update_data(value=value)
    await state.set_state(NewDiscount.waiting_days)
    await message.answer(
        "На сколько дней действует скидка? Введите число дней или "
        "<code>0</code> для бессрочной (или /cancel).",
        parse_mode="HTML",
    )


@router.message(NewDiscount.waiting_days, Command("cancel"))
async def disc_days_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.")


@router.message(NewDiscount.waiting_days)
async def disc_days(message: Message, state: FSMContext) -> None:
    try:
        days = int((message.text or "").strip())
        if days < 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите целое неотрицательное число.")
        return
    data = await state.get_data()
    await state.clear()
    valid_to = None
    if days > 0:
        valid_to = (datetime.now() + timedelta(days=days)).isoformat(
            sep=" ", timespec="seconds"
        )
    db = get_db()
    try:
        did = await db.add_discount(
            kind=data["kind"],
            value=data["value"],
            product_id=data.get("product_id"),
            valid_to=valid_to,
        )
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await db.log_action(
        admin_id=message.from_user.id,
        action="add_discount",
        target=str(data.get("product_id") or "all"),
        payload=f"{data['kind']}:{data['value']}:{days or '∞'}",
    )
    scope = "все товары" if not data.get("product_id") else f"товар #{data['product_id']}"
    suffix = " бессрочно" if not valid_to else f" до {valid_to[:10]}"
    unit = "%" if data["kind"] == "percent" else "₽"
    await message.answer(
        f"✅ Скидка #{did} создана: <b>−{data['value']:g} {unit}</b> "
        f"({scope}){suffix}.",
        parse_mode="HTML",
    )
