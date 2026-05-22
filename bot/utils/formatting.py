"""Хелперы форматирования сообщений для Telegram."""

from __future__ import annotations

from html import escape

from bot.database.db import (
    Discount,
    Order,
    Product,
    STATUS_LABELS,
    apply_discount,
)


def format_money(value: float) -> str:
    return f"{value:,.2f} ₽".replace(",", " ")


def format_product_card(product: Product,
                        discount: Discount | None = None) -> str:
    final = apply_discount(product.price, discount)
    lines = [
        f"<b>{escape(product.title)}</b>",
        f"Артикул: <code>{escape(product.sku)}</code>",
        f"Категория: {escape(product.category)}",
        "",
    ]
    if discount and final < product.price:
        lines.append(
            f"Цена: <s>{format_money(product.price)}</s> → "
            f"<b>{format_money(final)}</b>  ({escape(discount.label)})"
        )
    else:
        lines.append(f"Цена: <b>{format_money(product.price)}</b>")
    stock_label = (f"<b>{product.stock}</b> шт. в наличии"
                   if product.stock > 0 else "<b>нет в наличии</b>")
    lines.append(f"Остаток: {stock_label}")
    lines.append(
        "Статус: " + ("<b>в продаже</b>" if product.is_active
                      else "<b>снят с продажи</b>")
    )
    if product.description:
        lines.append("")
        lines.append(f"<i>{escape(product.description)}</i>")
    lines.append("")
    lines.append(f"Обновлён: {escape(product.updated_at)}")
    return "\n".join(lines)


def format_order_card(order: Order) -> str:
    """Сформировать HTML-карточку заказа для отображения администратору."""

    status = STATUS_LABELS.get(order.status, order.status)
    comment = order.comment or "—"
    tg_id = order.customer_telegram_id or "—"
    return (
        f"<b>Заказ №{order.id}</b> (внешний: <code>{escape(order.external_id)}</code>)\n"
        f"Статус: <b>{escape(status)}</b>\n"
        f"Создан: {escape(order.created_at)}\n"
        f"Обновлён: {escape(order.updated_at)}\n"
        f"\n"
        f"<b>Клиент:</b> {escape(order.customer_name)}\n"
        f"<b>Телефон:</b> <code>{escape(order.customer_phone)}</code>\n"
        f"<b>Telegram ID:</b> <code>{tg_id}</code>\n"
        f"<b>Адрес доставки:</b> {escape(order.address)}\n"
        f"\n"
        f"<b>Состав заказа:</b>\n{escape(order.items)}\n"
        f"\n"
        f"<b>Сумма:</b> {format_money(order.total)}\n"
        f"<b>Комментарий:</b> {escape(comment)}"
    )
