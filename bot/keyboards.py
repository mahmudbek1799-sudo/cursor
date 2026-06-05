"""Клавиатуры бота: ReplyKeyboardMarkup и InlineKeyboardMarkup."""

from __future__ import annotations

from typing import Iterable

from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from bot.database import ORDER_STATUSES, STATUS_LABELS


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True,
                             input_field_placeholder="Выберите действие")
    kb.row(KeyboardButton("📋 Активные заказы"),
           KeyboardButton("✅ Завершённые"))
    kb.row(KeyboardButton("🛍 Товары"), KeyboardButton("🏷 Скидки"))
    kb.row(KeyboardButton("📊 Статистика"), KeyboardButton("📈 Дашборд"))
    kb.row(KeyboardButton("🚫 Чёрный список"), KeyboardButton("📣 Рассылка"))
    kb.row(KeyboardButton("🔄 Синхронизация"), KeyboardButton("📤 Экспорт"))
    kb.row(KeyboardButton("❓ Помощь"))
    return kb


# ---------------------------------------------------------------------------
# Заказы
# ---------------------------------------------------------------------------
def orders_filter_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Новые", callback_data="orders:f:new"),
        InlineKeyboardButton("Подтв.", callback_data="orders:f:confirmed"),
        InlineKeyboardButton("В доставке",
                             callback_data="orders:f:in_delivery"),
        InlineKeyboardButton("Завершён.",
                             callback_data="orders:f:completed"),
        InlineKeyboardButton("Отменён.",
                             callback_data="orders:f:cancelled"),
        InlineKeyboardButton("Все", callback_data="orders:f:all"),
    )
    return kb


def order_actions_keyboard(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔁 Сменить статус",
                             callback_data=f"order:{order_id}:status"),
        InlineKeyboardButton("📞 Связаться",
                             callback_data=f"order:{order_id}:contact"),
    )
    kb.add(
        InlineKeyboardButton("💬 Написать клиенту",
                             callback_data=f"order:{order_id}:message"),
    )
    kb.add(
        InlineKeyboardButton("« К списку",
                             callback_data="orders:f:new"),
    )
    return kb


def status_change_keyboard(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton(
            STATUS_LABELS[status],
            callback_data=f"order:{order_id}:set:{status}",
        )
        for status in ORDER_STATUSES
    ]
    kb.add(*buttons)
    kb.add(InlineKeyboardButton(
        "« Отмена", callback_data=f"order:{order_id}:open",
    ))
    return kb


# ---------------------------------------------------------------------------
# Товары
# ---------------------------------------------------------------------------
def products_list_keyboard(
    products: Iterable,
    page: int,
    total_pages: int,
    category: str | None = None,
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    for p in products:
        suffix = (f" • {int(p.stock)} шт." if p.stock
                  else " • нет в наличии")
        kb.add(InlineKeyboardButton(
            text=f"{p.title} — {p.price:,.0f} ₽{suffix}".replace(",", " "),
            callback_data=f"product:{p.id}:open",
        ))
    cat_suffix = f"|{category}" if category else ""
    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(InlineKeyboardButton(
            "«", callback_data=f"products:page:{page - 1}{cat_suffix}"))
    nav.append(InlineKeyboardButton(
        f"{page}/{max(total_pages, 1)}",
        callback_data="products:noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(
            "»", callback_data=f"products:page:{page + 1}{cat_suffix}"))
    if nav:
        kb.row(*nav)
    kb.row(
        InlineKeyboardButton("➕ Добавить", callback_data="product:add"),
        InlineKeyboardButton("🏷 Категории",
                             callback_data="products:categories"),
    )
    return kb


def categories_keyboard(categories: list[str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton(
        "📦 Все товары", callback_data="products:page:1"))
    buttons = [
        InlineKeyboardButton(c, callback_data=f"products:page:1|{c}")
        for c in categories
    ]
    if buttons:
        kb.add(*buttons)
    return kb


def product_actions_keyboard(product_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💰 Изменить цену",
                             callback_data=f"product:{product_id}:price"),
        InlineKeyboardButton("📦 Изменить остаток",
                             callback_data=f"product:{product_id}:stock"),
    )
    kb.add(
        InlineKeyboardButton("🏷 Скидка",
                             callback_data=f"product:{product_id}:discount"),
        InlineKeyboardButton("🚫 Снять с продажи",
                             callback_data=f"product:{product_id}:toggle"),
    )
    kb.add(
        InlineKeyboardButton("❌ Удалить",
                             callback_data=f"product:{product_id}:delete"),
        InlineKeyboardButton("« К списку",
                             callback_data="products:page:1"),
    )
    return kb


# ---------------------------------------------------------------------------
# Скидки
# ---------------------------------------------------------------------------
def discount_kind_keyboard(product_id: int | None) -> InlineKeyboardMarkup:
    target = product_id if product_id is not None else 0
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("% Процент",
                             callback_data=f"discount:new:percent:{target}"),
        InlineKeyboardButton("₽ Фиксированная",
                             callback_data=f"discount:new:fixed:{target}"),
    )
    return kb


def discounts_list_keyboard(discounts: Iterable) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    for d in discounts:
        scope = ("Все товары" if d.product_id is None
                 else f"Товар #{d.product_id}")
        kb.row(
            InlineKeyboardButton(
                text=f"#{d.id}  {d.label}  •  {scope}",
                callback_data=f"discount:open:{d.id}",
            ),
            InlineKeyboardButton(
                "🗑", callback_data=f"discount:off:{d.id}",
            ),
        )
    kb.add(InlineKeyboardButton(
        "➕ Новая глобальная скидка",
        callback_data="discount:new_global",
    ))
    return kb


def export_period_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("За сегодня", callback_data="export:1"),
        InlineKeyboardButton("За 7 дней", callback_data="export:7"),
        InlineKeyboardButton("За 30 дней", callback_data="export:30"),
        InlineKeyboardButton("За всё время", callback_data="export:0"),
    )
    return kb
