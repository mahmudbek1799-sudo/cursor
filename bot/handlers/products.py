"""Управление каталогом товаров: список, добавление, удаление, изменение
цен/остатков, активация/деактивация.
"""

from __future__ import annotations

import logging
import math
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.database.db import get_db
from bot.keyboards.admin import (
    categories_keyboard,
    discount_kind_keyboard,
    product_actions_keyboard,
    products_list_keyboard,
)
from bot.utils.formatting import format_money, format_product_card

logger = logging.getLogger(__name__)
router = Router(name="products")

PAGE_SIZE = 8


class AddProduct(StatesGroup):
    waiting_sku = State()
    waiting_title = State()
    waiting_category = State()
    waiting_price = State()
    waiting_stock = State()
    waiting_description = State()


class EditPrice(StatesGroup):
    waiting_value = State()


class EditStock(StatesGroup):
    waiting_value = State()


# ---------------------------------------------------------------------------
# Список товаров
# ---------------------------------------------------------------------------
async def _send_products_page(target: Message, page: int,
                              category: str | None) -> None:
    db = get_db()
    total = await db.count_products(category=category)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    products = await db.list_products(
        category=category, limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE
    )
    title = "🛍 <b>Каталог товаров</b>"
    if category:
        title += f" • категория: <b>{escape(category)}</b>"
    if not products:
        text = f"{title}\n\nКаталог пуст. Добавьте товар через ➕ или /add_product."
    else:
        text = f"{title}\nВсего: <b>{total}</b>."
    kb = products_list_keyboard(products, page, total_pages, category)
    if hasattr(target, "edit_text"):
        try:
            await target.edit_text(text, reply_markup=kb, parse_mode="HTML")
            return
        except Exception:  # noqa: BLE001
            pass
    await target.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("products"))
@router.message(F.text == "🛍 Товары")
async def cmd_products(message: Message) -> None:
    await _send_products_page(message, page=1, category=None)


@router.callback_query(F.data == "products:noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.regexp(r"^products:page:(\d+)(?:\|(.+))?$"))
async def cb_page(callback: CallbackQuery) -> None:
    parts = callback.data.split(":", 2)[2]
    if "|" in parts:
        page_s, category = parts.split("|", 1)
    else:
        page_s, category = parts, None
    await _send_products_page(callback.message, int(page_s), category)
    await callback.answer()


@router.callback_query(F.data == "products:categories")
async def cb_categories(callback: CallbackQuery) -> None:
    db = get_db()
    cats = await db.list_categories()
    await callback.message.edit_text(
        "🏷 <b>Категории товаров</b>\n\nВыберите категорию или все товары.",
        reply_markup=categories_keyboard(cats),
        parse_mode="HTML",
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Карточка товара
# ---------------------------------------------------------------------------
async def _show_product(target, product_id: int) -> None:
    db = get_db()
    product = await db.get_product(product_id)
    if product is None:
        if isinstance(target, CallbackQuery):
            await target.answer("Товар не найден", show_alert=True)
        else:
            await target.answer("Товар не найден.")
        return
    discount = await db.get_active_discount_for_product(product_id)
    text = format_product_card(product, discount)
    kb = product_actions_keyboard(product_id)
    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:  # noqa: BLE001
            await target.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await target.answer()
    else:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.regexp(r"^product:(\d+):open$"))
async def cb_open_product(callback: CallbackQuery) -> None:
    pid = int(callback.data.split(":")[1])
    await _show_product(callback, pid)


@router.message(Command("product"))
async def cmd_product(message: Message, command: CommandObject) -> None:
    raw = (command.args or "").strip()
    db = get_db()
    if not raw:
        await message.answer(
            "Использование: /product &lt;id&gt; или /product &lt;sku&gt;",
            parse_mode="HTML",
        )
        return
    if raw.isdigit():
        product = await db.get_product(int(raw))
    else:
        product = await db.get_product_by_sku(raw)
    if product is None:
        await message.answer("Товар не найден.")
        return
    await _show_product(message, product.id)


# ---------------------------------------------------------------------------
# Добавление товара (FSM)
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "product:add")
async def cb_add_product(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddProduct.waiting_sku)
    await callback.message.answer(
        "🆕 <b>Добавление нового товара</b>\n\n"
        "Введите артикул (SKU). Пример: <code>SOFA-STOCKHOLM-001</code>.\n"
        "Для отмены — /cancel.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(Command("add_product"))
async def cmd_add_product(message: Message, state: FSMContext) -> None:
    await state.set_state(AddProduct.waiting_sku)
    await message.answer(
        "🆕 <b>Добавление нового товара</b>\n\n"
        "Введите артикул (SKU). Для отмены — /cancel.",
        parse_mode="HTML",
    )


@router.message(AddProduct.waiting_sku, Command("cancel"))
@router.message(AddProduct.waiting_title, Command("cancel"))
@router.message(AddProduct.waiting_category, Command("cancel"))
@router.message(AddProduct.waiting_price, Command("cancel"))
@router.message(AddProduct.waiting_stock, Command("cancel"))
@router.message(AddProduct.waiting_description, Command("cancel"))
async def add_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Добавление отменено.")


@router.message(AddProduct.waiting_sku)
async def add_sku(message: Message, state: FSMContext) -> None:
    sku = (message.text or "").strip()
    if not sku or len(sku) > 64:
        await message.answer("Артикул должен быть от 1 до 64 символов.")
        return
    db = get_db()
    if await db.get_product_by_sku(sku):
        await message.answer("Такой артикул уже существует. Введите другой.")
        return
    await state.update_data(sku=sku)
    await state.set_state(AddProduct.waiting_title)
    await message.answer("Введите название товара:")


@router.message(AddProduct.waiting_title)
async def add_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не может быть пустым.")
        return
    await state.update_data(title=title)
    await state.set_state(AddProduct.waiting_category)
    await message.answer(
        "Введите категорию (например, диван, кровать, шкаф). "
        "Можно отправить «-» для категории «другое»:"
    )


@router.message(AddProduct.waiting_category)
async def add_category(message: Message, state: FSMContext) -> None:
    cat = (message.text or "").strip().lower()
    if cat in ("", "-"):
        cat = "другое"
    await state.update_data(category=cat)
    await state.set_state(AddProduct.waiting_price)
    await message.answer("Введите цену в рублях (целое или десятичное число):")


@router.message(AddProduct.waiting_price)
async def add_price(message: Message, state: FSMContext) -> None:
    try:
        price = float((message.text or "").replace(",", ".").strip())
        if price < 0:
            raise ValueError
    except ValueError:
        await message.answer("Цена должна быть неотрицательным числом. Повторите.")
        return
    await state.update_data(price=price)
    await state.set_state(AddProduct.waiting_stock)
    await message.answer("Введите количество на складе (целое число):")


@router.message(AddProduct.waiting_stock)
async def add_stock(message: Message, state: FSMContext) -> None:
    try:
        stock = int((message.text or "").strip())
        if stock < 0:
            raise ValueError
    except ValueError:
        await message.answer("Остаток должен быть неотрицательным целым. Повторите.")
        return
    await state.update_data(stock=stock)
    await state.set_state(AddProduct.waiting_description)
    await message.answer(
        "Введите краткое описание (или «-» чтобы пропустить):"
    )


@router.message(AddProduct.waiting_description)
async def add_description(message: Message, state: FSMContext) -> None:
    desc = (message.text or "").strip()
    if desc == "-":
        desc = ""
    data = await state.get_data()
    await state.clear()
    db = get_db()
    payload = {
        "sku": data["sku"],
        "title": data["title"],
        "category": data["category"],
        "price": data["price"],
        "stock": data["stock"],
        "description": desc,
        "is_active": 1,
    }
    await db.upsert_product(payload)
    product = await db.get_product_by_sku(data["sku"])
    await db.log_action(
        admin_id=message.from_user.id,
        action="add_product",
        target=data["sku"],
        payload=f"{data['title']} | {format_money(data['price'])}",
    )
    await message.answer(
        f"✅ Товар добавлен.\n\n{format_product_card(product)}",
        reply_markup=product_actions_keyboard(product.id),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Изменение цены и остатка
# ---------------------------------------------------------------------------
@router.callback_query(F.data.regexp(r"^product:(\d+):price$"))
async def cb_edit_price(callback: CallbackQuery, state: FSMContext) -> None:
    pid = int(callback.data.split(":")[1])
    await state.set_state(EditPrice.waiting_value)
    await state.update_data(product_id=pid)
    await callback.message.answer(
        "💰 Введите новую цену в рублях (или /cancel):"
    )
    await callback.answer()


@router.message(Command("price"))
async def cmd_price(message: Message, command: CommandObject) -> None:
    parts = (command.args or "").strip().split()
    if len(parts) != 2:
        await message.answer(
            "Использование: /price &lt;sku|id&gt; &lt;новая_цена&gt;",
            parse_mode="HTML",
        )
        return
    raw, price_raw = parts
    try:
        new_price = float(price_raw.replace(",", "."))
    except ValueError:
        await message.answer("Цена должна быть числом.")
        return
    db = get_db()
    product = (await db.get_product(int(raw))
               if raw.isdigit() else await db.get_product_by_sku(raw))
    if product is None:
        await message.answer("Товар не найден.")
        return
    await db.update_product_price(product.id, new_price)
    await db.log_action(
        admin_id=message.from_user.id,
        action="update_price",
        target=product.sku,
        payload=format_money(new_price),
    )
    await message.answer(
        f"✅ Цена обновлена: {format_money(product.price)} → "
        f"<b>{format_money(new_price)}</b>",
        parse_mode="HTML",
    )


@router.message(EditPrice.waiting_value, Command("cancel"))
async def price_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Изменение отменено.")


@router.message(EditPrice.waiting_value)
async def price_set(message: Message, state: FSMContext) -> None:
    try:
        new_price = float((message.text or "").replace(",", ".").strip())
        if new_price < 0:
            raise ValueError
    except ValueError:
        await message.answer("Цена должна быть неотрицательным числом.")
        return
    data = await state.get_data()
    await state.clear()
    db = get_db()
    pid = int(data["product_id"])
    product = await db.get_product(pid)
    if product is None:
        await message.answer("Товар не найден.")
        return
    await db.update_product_price(pid, new_price)
    await db.log_action(
        admin_id=message.from_user.id,
        action="update_price",
        target=product.sku,
        payload=format_money(new_price),
    )
    updated = await db.get_product(pid)
    await message.answer(
        f"✅ Цена обновлена: {format_money(product.price)} → "
        f"<b>{format_money(new_price)}</b>\n\n{format_product_card(updated)}",
        reply_markup=product_actions_keyboard(pid),
        parse_mode="HTML",
    )


@router.callback_query(F.data.regexp(r"^product:(\d+):stock$"))
async def cb_edit_stock(callback: CallbackQuery, state: FSMContext) -> None:
    pid = int(callback.data.split(":")[1])
    await state.set_state(EditStock.waiting_value)
    await state.update_data(product_id=pid)
    await callback.message.answer("📦 Введите новый остаток (целое число) или /cancel:")
    await callback.answer()


@router.message(EditStock.waiting_value, Command("cancel"))
async def stock_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Изменение отменено.")


@router.message(EditStock.waiting_value)
async def stock_set(message: Message, state: FSMContext) -> None:
    try:
        new_stock = int((message.text or "").strip())
        if new_stock < 0:
            raise ValueError
    except ValueError:
        await message.answer("Остаток должен быть неотрицательным целым.")
        return
    data = await state.get_data()
    await state.clear()
    db = get_db()
    pid = int(data["product_id"])
    product = await db.get_product(pid)
    if product is None:
        await message.answer("Товар не найден.")
        return
    await db.update_product_stock(pid, new_stock)
    await db.log_action(
        admin_id=message.from_user.id,
        action="update_stock",
        target=product.sku,
        payload=str(new_stock),
    )
    updated = await db.get_product(pid)
    await message.answer(
        f"✅ Остаток обновлён: {product.stock} → <b>{new_stock}</b>\n\n"
        f"{format_product_card(updated)}",
        reply_markup=product_actions_keyboard(pid),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Активация/деактивация и удаление
# ---------------------------------------------------------------------------
@router.callback_query(F.data.regexp(r"^product:(\d+):toggle$"))
async def cb_toggle(callback: CallbackQuery) -> None:
    pid = int(callback.data.split(":")[1])
    db = get_db()
    product = await db.get_product(pid)
    if product is None:
        await callback.answer("Не найден", show_alert=True)
        return
    new_active = not bool(product.is_active)
    await db.set_product_active(pid, new_active)
    await db.log_action(
        admin_id=callback.from_user.id,
        action="toggle_product",
        target=product.sku,
        payload="active" if new_active else "inactive",
    )
    await _show_product(callback, pid)


@router.callback_query(F.data.regexp(r"^product:(\d+):delete$"))
async def cb_delete(callback: CallbackQuery) -> None:
    pid = int(callback.data.split(":")[1])
    db = get_db()
    product = await db.get_product(pid)
    if product is None:
        await callback.answer("Не найден", show_alert=True)
        return
    await db.delete_product(pid)
    await db.log_action(
        admin_id=callback.from_user.id,
        action="delete_product",
        target=product.sku,
    )
    await callback.message.edit_text(
        f"🗑 Товар <b>{escape(product.title)}</b> "
        f"(<code>{escape(product.sku)}</code>) удалён.",
        parse_mode="HTML",
    )
    await callback.answer("Удалено")


@router.message(Command("del_product"))
async def cmd_del_product(message: Message, command: CommandObject) -> None:
    raw = (command.args or "").strip()
    if not raw:
        await message.answer(
            "Использование: /del_product &lt;sku|id&gt;", parse_mode="HTML"
        )
        return
    db = get_db()
    product = (await db.get_product(int(raw))
               if raw.isdigit() else await db.get_product_by_sku(raw))
    if product is None:
        await message.answer("Товар не найден.")
        return
    await db.delete_product(product.id)
    await db.log_action(
        admin_id=message.from_user.id,
        action="delete_product",
        target=product.sku,
    )
    await message.answer(
        f"🗑 Товар <b>{escape(product.title)}</b> удалён.",
        parse_mode="HTML",
    )


# Старт скидки на конкретный товар — здесь только запуск FSM/клавиатуры,
# вся логика разработана в handlers/discounts.py.
@router.callback_query(F.data.regexp(r"^product:(\d+):discount$"))
async def cb_product_discount(callback: CallbackQuery) -> None:
    pid = int(callback.data.split(":")[1])
    await callback.message.answer(
        "🏷 Выберите тип скидки для этого товара:",
        reply_markup=discount_kind_keyboard(pid),
    )
    await callback.answer()
