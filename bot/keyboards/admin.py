"""Клавиатуры административной панели бота."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from bot.database.db import ORDER_STATUSES, STATUS_LABELS


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню в виде reply-клавиатуры."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Активные заказы"),
             KeyboardButton(text="✅ Завершённые")],
            [KeyboardButton(text="🛍 Товары"),
             KeyboardButton(text="🏷 Скидки")],
            [KeyboardButton(text="📊 Статистика"),
             KeyboardButton(text="📈 Дашборд")],
            [KeyboardButton(text="🚫 Чёрный список"),
             KeyboardButton(text="📣 Рассылка")],
            [KeyboardButton(text="🔄 Синхронизация"),
             KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def products_list_keyboard(
    products,
    page: int,
    total_pages: int,
    category: str | None = None,
) -> InlineKeyboardMarkup:
    """Inline-клавиатура для списка товаров с пагинацией."""

    rows: list[list[InlineKeyboardButton]] = []
    for p in products:
        suffix = f" • {int(p.stock)} шт." if p.stock else " • нет в наличии"
        rows.append([
            InlineKeyboardButton(
                text=f"{p.title} — {p.price:,.0f} ₽{suffix}".replace(",", " "),
                callback_data=f"product:{p.id}:open",
            )
        ])
    nav: list[InlineKeyboardButton] = []
    cat_suffix = f"|{category}" if category else ""
    if page > 1:
        nav.append(InlineKeyboardButton(
            text="«", callback_data=f"products:page:{page - 1}{cat_suffix}"
        ))
    nav.append(InlineKeyboardButton(
        text=f"{page}/{max(total_pages, 1)}", callback_data="products:noop"
    ))
    if page < total_pages:
        nav.append(InlineKeyboardButton(
            text="»", callback_data=f"products:page:{page + 1}{cat_suffix}"
        ))
    rows.append(nav)
    rows.append([
        InlineKeyboardButton(text="➕ Добавить",
                             callback_data="product:add"),
        InlineKeyboardButton(text="🏷 Категории",
                             callback_data="products:categories"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def categories_keyboard(categories: list[str]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="📦 Все товары",
                              callback_data="products:page:1")]
    ]
    line: list[InlineKeyboardButton] = []
    for c in categories:
        line.append(InlineKeyboardButton(
            text=c, callback_data=f"products:page:1|{c}"
        ))
        if len(line) == 2:
            rows.append(line)
            line = []
    if line:
        rows.append(line)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_actions_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Inline-кнопки управления карточкой товара."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Изменить цену",
                    callback_data=f"product:{product_id}:price",
                ),
                InlineKeyboardButton(
                    text="📦 Изменить остаток",
                    callback_data=f"product:{product_id}:stock",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏷 Скидка",
                    callback_data=f"product:{product_id}:discount",
                ),
                InlineKeyboardButton(
                    text="🚫 Снять с продажи",
                    callback_data=f"product:{product_id}:toggle",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Удалить",
                    callback_data=f"product:{product_id}:delete",
                ),
                InlineKeyboardButton(
                    text="« К списку",
                    callback_data="products:page:1",
                ),
            ],
        ]
    )


def discount_kind_keyboard(product_id: int | None) -> InlineKeyboardMarkup:
    target = product_id if product_id is not None else 0
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="% Процент",
                    callback_data=f"discount:new:percent:{target}",
                ),
                InlineKeyboardButton(
                    text="₽ Фиксированная",
                    callback_data=f"discount:new:fixed:{target}",
                ),
            ]
        ]
    )


def discounts_list_keyboard(discounts) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for d in discounts:
        scope = "Все товары" if d.product_id is None else f"Товар #{d.product_id}"
        rows.append([
            InlineKeyboardButton(
                text=f"#{d.id}  {d.label}  •  {scope}",
                callback_data=f"discount:open:{d.id}",
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"discount:off:{d.id}",
            ),
        ])
    rows.append([
        InlineKeyboardButton(text="➕ Новая глобальная скидка",
                             callback_data="discount:new_global"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def orders_filter_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="Новые", callback_data="orders:f:new"),
            InlineKeyboardButton(text="Подтв.", callback_data="orders:f:confirmed"),
        ],
        [
            InlineKeyboardButton(text="В доставке", callback_data="orders:f:in_delivery"),
            InlineKeyboardButton(text="Завершён.", callback_data="orders:f:completed"),
        ],
        [
            InlineKeyboardButton(text="Отменён.", callback_data="orders:f:cancelled"),
            InlineKeyboardButton(text="Все", callback_data="orders:f:all"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def order_actions_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Действия над конкретным заказом."""

    rows = [
        [
            InlineKeyboardButton(
                text="🔁 Сменить статус",
                callback_data=f"order:{order_id}:status",
            ),
            InlineKeyboardButton(
                text="📞 Связаться",
                callback_data=f"order:{order_id}:contact",
            ),
        ],
        [
            InlineKeyboardButton(
                text="💬 Написать клиенту",
                callback_data=f"order:{order_id}:message",
            ),
        ],
        [
            InlineKeyboardButton(
                text="« К списку",
                callback_data="orders:f:new",
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def status_change_keyboard(order_id: int) -> InlineKeyboardMarkup:
    rows = []
    line: list[InlineKeyboardButton] = []
    for status in ORDER_STATUSES:
        line.append(
            InlineKeyboardButton(
                text=STATUS_LABELS[status],
                callback_data=f"order:{order_id}:set:{status}",
            )
        )
        if len(line) == 2:
            rows.append(line)
            line = []
    if line:
        rows.append(line)
    rows.append(
        [
            InlineKeyboardButton(
                text="« Отмена",
                callback_data=f"order:{order_id}:open",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"confirm:{action}:yes"),
                InlineKeyboardButton(text="✖️ Нет", callback_data=f"confirm:{action}:no"),
            ]
        ]
    )
