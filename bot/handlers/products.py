"""Управление каталогом товаров: CRUD, изменение цен и остатков."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from html import escape

from telebot import TeleBot
from telebot.types import CallbackQuery, Message

from bot.database import get_db
from bot.keyboards import (
    categories_keyboard,
    discount_kind_keyboard,
    product_actions_keyboard,
    products_list_keyboard,
)
from bot.utils import admin_only, format_money, format_product_card

logger = logging.getLogger(__name__)

PAGE_SIZE = 8


# Простейший FSM на уровне модуля: по user_id храним состояние.
@dataclass
class AddState:
    step: str = "sku"
    sku: str = ""
    title: str = ""
    category: str = ""
    price: float = 0.0
    stock: int = 0


_add_state: dict[int, AddState] = {}
_edit_price: dict[int, int] = {}   # user_id -> product_id
_edit_stock: dict[int, int] = {}


# ---------------------------------------------------------------------------
def _show_products_page(bot: TeleBot, chat_id: int, page: int,
                        category: str | None,
                        message_id: int | None = None) -> None:
    db = get_db()
    total = db.count_products(category=category)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    products = db.list_products(
        category=category, limit=PAGE_SIZE,
        offset=(page - 1) * PAGE_SIZE,
    )
    text = "🛍 <b>Каталог товаров</b>"
    if category:
        text += f" • категория: <b>{escape(category)}</b>"
    if not products:
        text += ("\n\nКаталог пуст. Добавьте товар через ➕ "
                 "или командой /add_product.")
    else:
        text += f"\nВсего: <b>{total}</b>."
    kb = products_list_keyboard(products, page, total_pages, category)
    if message_id is not None:
        try:
            bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id,
                reply_markup=kb, parse_mode="HTML",
            )
            return
        except Exception:  # noqa: BLE001
            pass
    bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")


def _show_product_card(bot: TeleBot, chat_id: int, product_id: int,
                       message_id: int | None = None) -> None:
    db = get_db()
    product = db.get_product(product_id)
    if product is None:
        bot.send_message(chat_id, "Товар не найден.")
        return
    discount = db.get_active_discount_for_product(product_id)
    text = format_product_card(product, discount)
    kb = product_actions_keyboard(product_id)
    if message_id is not None:
        try:
            bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id,
                reply_markup=kb, parse_mode="HTML",
            )
            return
        except Exception:  # noqa: BLE001
            pass
    bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")


# ---------------------------------------------------------------------------
def register(bot: TeleBot) -> None:

    # ---------------- Список и навигация ----------------
    @bot.message_handler(commands=["products"])
    @admin_only
    def cmd_products(message: Message) -> None:
        _show_products_page(bot, message.chat.id, 1, None)

    @bot.message_handler(func=lambda m: m.text == "🛍 Товары")
    @admin_only
    def kb_products(message: Message) -> None:
        _show_products_page(bot, message.chat.id, 1, None)

    @bot.callback_query_handler(func=lambda c: c.data == "products:noop")
    @admin_only
    def cb_noop(callback: CallbackQuery) -> None:
        bot.answer_callback_query(callback.id)

    @bot.callback_query_handler(
        func=lambda c: c.data and c.data.startswith("products:page:"))
    @admin_only
    def cb_page(callback: CallbackQuery) -> None:
        parts = callback.data.split(":", 2)[2]
        if "|" in parts:
            page_s, category = parts.split("|", 1)
        else:
            page_s, category = parts, None
        _show_products_page(
            bot, callback.message.chat.id, int(page_s), category,
            message_id=callback.message.message_id,
        )
        bot.answer_callback_query(callback.id)

    @bot.callback_query_handler(func=lambda c: c.data == "products:categories")
    @admin_only
    def cb_categories(callback: CallbackQuery) -> None:
        db = get_db()
        cats = db.list_categories()
        try:
            bot.edit_message_text(
                "🏷 <b>Категории товаров</b>\n\n"
                "Выберите категорию или «Все товары».",
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                reply_markup=categories_keyboard(cats),
                parse_mode="HTML",
            )
        except Exception:  # noqa: BLE001
            pass
        bot.answer_callback_query(callback.id)

    # ---------------- Карточка товара ----------------
    @bot.message_handler(commands=["product"])
    @admin_only
    def cmd_product(message: Message) -> None:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message,
                         "Использование: /product &lt;id|sku&gt;",
                         parse_mode="HTML")
            return
        raw = parts[1].strip()
        db = get_db()
        product = (db.get_product(int(raw))
                   if raw.isdigit() else db.get_product_by_sku(raw))
        if product is None:
            bot.reply_to(message, "Товар не найден.")
            return
        _show_product_card(bot, message.chat.id, product.id)

    @bot.callback_query_handler(
        func=lambda c: c.data and c.data.startswith("product:")
        and c.data.endswith(":open"))
    @admin_only
    def cb_open_product(callback: CallbackQuery) -> None:
        pid = int(callback.data.split(":")[1])
        _show_product_card(bot, callback.message.chat.id, pid,
                           message_id=callback.message.message_id)
        bot.answer_callback_query(callback.id)

    # ---------------- Добавление нового товара ----------------
    @bot.callback_query_handler(func=lambda c: c.data == "product:add")
    @admin_only
    def cb_add(callback: CallbackQuery) -> None:
        _add_state[callback.from_user.id] = AddState()
        bot.send_message(
            callback.message.chat.id,
            "🆕 <b>Добавление нового товара</b>\n\n"
            "Введите артикул (SKU). Пример: "
            "<code>SOFA-STOCKHOLM-001</code>.\n"
            "Для отмены — /cancel.",
            parse_mode="HTML",
        )
        bot.answer_callback_query(callback.id)

    @bot.message_handler(commands=["add_product"])
    @admin_only
    def cmd_add_product(message: Message) -> None:
        _add_state[message.from_user.id] = AddState()
        bot.reply_to(
            message,
            "🆕 <b>Добавление нового товара</b>\n\n"
            "Введите артикул (SKU). Для отмены — /cancel.",
            parse_mode="HTML",
        )

    @bot.message_handler(
        func=lambda m: m.from_user and m.from_user.id in _add_state
        and (m.text or "") == "/cancel")
    @admin_only
    def add_cancel(message: Message) -> None:
        _add_state.pop(message.from_user.id, None)
        bot.reply_to(message, "Добавление отменено.")

    @bot.message_handler(
        func=lambda m: m.from_user and m.from_user.id in _add_state)
    @admin_only
    def add_step(message: Message) -> None:
        state = _add_state[message.from_user.id]
        text = (message.text or "").strip()
        db = get_db()
        if state.step == "sku":
            if not text or len(text) > 64:
                bot.reply_to(message, "Артикул от 1 до 64 символов.")
                return
            if db.get_product_by_sku(text):
                bot.reply_to(message, "Такой артикул уже есть.")
                return
            state.sku = text
            state.step = "title"
            bot.reply_to(message, "Введите название товара:")
        elif state.step == "title":
            if not text:
                bot.reply_to(message, "Название не может быть пустым.")
                return
            state.title = text
            state.step = "category"
            bot.reply_to(message,
                         "Введите категорию (диван, кровать и т. п.) "
                         "или «-» для «другое»:")
        elif state.step == "category":
            state.category = "другое" if text in ("", "-") else text.lower()
            state.step = "price"
            bot.reply_to(message, "Введите цену в рублях:")
        elif state.step == "price":
            try:
                price = float(text.replace(",", "."))
                if price < 0:
                    raise ValueError
            except ValueError:
                bot.reply_to(message, "Цена должна быть неотрицательным "
                                      "числом.")
                return
            state.price = price
            state.step = "stock"
            bot.reply_to(message, "Введите количество на складе:")
        elif state.step == "stock":
            try:
                stock = int(text)
                if stock < 0:
                    raise ValueError
            except ValueError:
                bot.reply_to(message,
                             "Остаток — неотрицательное целое.")
                return
            state.stock = stock
            state.step = "description"
            bot.reply_to(message,
                         "Введите описание или «-» чтобы пропустить:")
        elif state.step == "description":
            desc = "" if text == "-" else text
            _add_state.pop(message.from_user.id, None)
            db.upsert_product({
                "sku": state.sku, "title": state.title,
                "category": state.category, "price": state.price,
                "stock": state.stock, "description": desc, "is_active": 1,
            })
            db.log_action(
                admin_id=message.from_user.id, action="add_product",
                target=state.sku,
                payload=f"{state.title} | {format_money(state.price)}",
            )
            product = db.get_product_by_sku(state.sku)
            bot.send_message(
                message.chat.id,
                f"✅ Товар добавлен.\n\n{format_product_card(product)}",
                reply_markup=product_actions_keyboard(product.id),
                parse_mode="HTML",
            )

    # ---------------- Изменение цены / остатка ----------------
    @bot.callback_query_handler(
        func=lambda c: c.data and c.data.startswith("product:")
        and c.data.endswith(":price"))
    @admin_only
    def cb_price(callback: CallbackQuery) -> None:
        pid = int(callback.data.split(":")[1])
        _edit_price[callback.from_user.id] = pid
        bot.send_message(
            callback.message.chat.id,
            "💰 Введите новую цену в рублях (или /cancel):",
        )
        bot.answer_callback_query(callback.id)

    @bot.message_handler(commands=["price"])
    @admin_only
    def cmd_price(message: Message) -> None:
        parts = (message.text or "").split(maxsplit=2)
        if len(parts) != 3:
            bot.reply_to(message,
                         "Использование: /price &lt;sku|id&gt; "
                         "&lt;цена&gt;",
                         parse_mode="HTML")
            return
        _, raw, price_raw = parts
        try:
            new_price = float(price_raw.replace(",", "."))
        except ValueError:
            bot.reply_to(message, "Цена должна быть числом.")
            return
        db = get_db()
        product = (db.get_product(int(raw))
                   if raw.isdigit() else db.get_product_by_sku(raw))
        if product is None:
            bot.reply_to(message, "Товар не найден.")
            return
        db.update_product_price(product.id, new_price)
        db.log_action(
            admin_id=message.from_user.id, action="update_price",
            target=product.sku, payload=format_money(new_price),
        )
        bot.reply_to(
            message,
            f"✅ Цена обновлена: {format_money(product.price)} → "
            f"<b>{format_money(new_price)}</b>",
            parse_mode="HTML",
        )

    @bot.message_handler(
        func=lambda m: m.from_user and m.from_user.id in _edit_price
        and (m.text or "") != "/cancel")
    @admin_only
    def msg_price(message: Message) -> None:
        pid = _edit_price.pop(message.from_user.id)
        try:
            new_price = float((message.text or "").replace(",", ".").strip())
            if new_price < 0:
                raise ValueError
        except ValueError:
            bot.reply_to(message, "Цена должна быть неотрицательным числом.")
            return
        db = get_db()
        product = db.get_product(pid)
        if product is None:
            bot.reply_to(message, "Товар не найден.")
            return
        db.update_product_price(pid, new_price)
        db.log_action(
            admin_id=message.from_user.id, action="update_price",
            target=product.sku, payload=format_money(new_price),
        )
        updated = db.get_product(pid)
        bot.send_message(
            message.chat.id,
            f"✅ Цена обновлена: {format_money(product.price)} → "
            f"<b>{format_money(new_price)}</b>\n\n"
            f"{format_product_card(updated)}",
            reply_markup=product_actions_keyboard(pid),
            parse_mode="HTML",
        )

    @bot.callback_query_handler(
        func=lambda c: c.data and c.data.startswith("product:")
        and c.data.endswith(":stock"))
    @admin_only
    def cb_stock(callback: CallbackQuery) -> None:
        pid = int(callback.data.split(":")[1])
        _edit_stock[callback.from_user.id] = pid
        bot.send_message(callback.message.chat.id,
                         "📦 Введите новый остаток (целое число) или /cancel:")
        bot.answer_callback_query(callback.id)

    @bot.message_handler(
        func=lambda m: m.from_user and m.from_user.id in _edit_stock
        and (m.text or "") != "/cancel")
    @admin_only
    def msg_stock(message: Message) -> None:
        pid = _edit_stock.pop(message.from_user.id)
        try:
            new_stock = int((message.text or "").strip())
            if new_stock < 0:
                raise ValueError
        except ValueError:
            bot.reply_to(message, "Остаток — неотрицательное целое.")
            return
        db = get_db()
        product = db.get_product(pid)
        if product is None:
            bot.reply_to(message, "Товар не найден.")
            return
        db.update_product_stock(pid, new_stock)
        db.log_action(
            admin_id=message.from_user.id, action="update_stock",
            target=product.sku, payload=str(new_stock),
        )
        updated = db.get_product(pid)
        bot.send_message(
            message.chat.id,
            f"✅ Остаток: {product.stock} → <b>{new_stock}</b>\n\n"
            f"{format_product_card(updated)}",
            reply_markup=product_actions_keyboard(pid),
            parse_mode="HTML",
        )

    # /cancel для price/stock
    @bot.message_handler(
        func=lambda m: m.from_user
        and (m.from_user.id in _edit_price
             or m.from_user.id in _edit_stock)
        and (m.text or "") == "/cancel")
    @admin_only
    def edit_cancel(message: Message) -> None:
        _edit_price.pop(message.from_user.id, None)
        _edit_stock.pop(message.from_user.id, None)
        bot.reply_to(message, "Изменение отменено.")

    # ---------------- Активация / удаление ----------------
    @bot.callback_query_handler(
        func=lambda c: c.data and c.data.startswith("product:")
        and c.data.endswith(":toggle"))
    @admin_only
    def cb_toggle(callback: CallbackQuery) -> None:
        pid = int(callback.data.split(":")[1])
        db = get_db()
        product = db.get_product(pid)
        if product is None:
            bot.answer_callback_query(callback.id, "Не найден",
                                      show_alert=True)
            return
        new_active = not bool(product.is_active)
        db.set_product_active(pid, new_active)
        db.log_action(
            admin_id=callback.from_user.id, action="toggle_product",
            target=product.sku,
            payload="active" if new_active else "inactive",
        )
        _show_product_card(bot, callback.message.chat.id, pid,
                           message_id=callback.message.message_id)
        bot.answer_callback_query(callback.id)

    @bot.callback_query_handler(
        func=lambda c: c.data and c.data.startswith("product:")
        and c.data.endswith(":delete"))
    @admin_only
    def cb_delete(callback: CallbackQuery) -> None:
        pid = int(callback.data.split(":")[1])
        db = get_db()
        product = db.get_product(pid)
        if product is None:
            bot.answer_callback_query(callback.id, "Не найден",
                                      show_alert=True)
            return
        db.delete_product(pid)
        db.log_action(
            admin_id=callback.from_user.id, action="delete_product",
            target=product.sku,
        )
        try:
            bot.edit_message_text(
                f"🗑 Товар <b>{escape(product.title)}</b> "
                f"(<code>{escape(product.sku)}</code>) удалён.",
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                parse_mode="HTML",
            )
        except Exception:  # noqa: BLE001
            pass
        bot.answer_callback_query(callback.id, "Удалено")

    @bot.message_handler(commands=["del_product"])
    @admin_only
    def cmd_del_product(message: Message) -> None:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message,
                         "Использование: /del_product &lt;id|sku&gt;",
                         parse_mode="HTML")
            return
        raw = parts[1].strip()
        db = get_db()
        product = (db.get_product(int(raw))
                   if raw.isdigit() else db.get_product_by_sku(raw))
        if product is None:
            bot.reply_to(message, "Товар не найден.")
            return
        db.delete_product(product.id)
        db.log_action(
            admin_id=message.from_user.id, action="delete_product",
            target=product.sku,
        )
        bot.reply_to(message,
                     f"🗑 Товар <b>{escape(product.title)}</b> удалён.",
                     parse_mode="HTML")

    # ---------------- Запуск скидки на конкретный товар ----------------
    @bot.callback_query_handler(
        func=lambda c: c.data and c.data.startswith("product:")
        and c.data.endswith(":discount"))
    @admin_only
    def cb_discount_start(callback: CallbackQuery) -> None:
        pid = int(callback.data.split(":")[1])
        bot.send_message(
            callback.message.chat.id,
            "🏷 Выберите тип скидки для этого товара:",
            reply_markup=discount_kind_keyboard(pid),
        )
        bot.answer_callback_query(callback.id)
