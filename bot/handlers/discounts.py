"""Управление скидками: процентные / фиксированные, на товар или глобально."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from telebot import TeleBot
from telebot.types import CallbackQuery, Message

from bot.database import get_db
from bot.keyboards import discount_kind_keyboard, discounts_list_keyboard
from bot.utils import admin_only

logger = logging.getLogger(__name__)


@dataclass
class NewDiscountState:
    step: str = "value"
    kind: str = "percent"
    product_id: int | None = None
    value: float = 0.0


_states: dict[int, NewDiscountState] = {}


def _format_discounts_list(discounts) -> str:
    if not discounts:
        return "🏷 <b>Активных скидок нет.</b>"
    lines = ["🏷 <b>Активные скидки</b>", ""]
    for d in discounts:
        scope = ("<i>все товары</i>" if d.product_id is None
                 else f"товар #{d.product_id}")
        period = f"  до {d.valid_to[:10]}" if d.valid_to else ""
        lines.append(f"#{d.id}  •  {d.label}  •  {scope}{period}")
    return "\n".join(lines)


def register(bot: TeleBot) -> None:

    @bot.message_handler(commands=["discounts"])
    @admin_only
    def cmd_discounts(message: Message) -> None:
        db = get_db()
        discounts = db.list_discounts(only_active=True)
        bot.send_message(
            message.chat.id,
            _format_discounts_list(discounts) + (
                "" if discounts else
                "\n\nСоздайте новую скидку командой\n"
                "<code>/discount &lt;sku|all&gt; "
                "&lt;percent|fixed&gt; &lt;значение&gt; [дней]</code>"
            ),
            reply_markup=discounts_list_keyboard(discounts),
            parse_mode="HTML",
        )

    @bot.message_handler(func=lambda m: m.text == "🏷 Скидки")
    @admin_only
    def kb_discounts(message: Message) -> None:
        cmd_discounts(message)

    @bot.message_handler(commands=["discount"])
    @admin_only
    def cmd_discount(message: Message) -> None:
        parts = (message.text or "").split()[1:]
        if len(parts) < 3:
            bot.reply_to(
                message,
                "Использование:\n<code>/discount &lt;sku|id|all&gt; "
                "&lt;percent|fixed&gt; &lt;значение&gt; [дней]</code>",
                parse_mode="HTML",
            )
            return
        target, kind, value_raw, *rest = parts
        if kind not in ("percent", "fixed"):
            bot.reply_to(message,
                         "Тип скидки должен быть percent или fixed.")
            return
        try:
            value = float(value_raw.replace(",", "."))
        except ValueError:
            bot.reply_to(message, "Значение скидки должно быть числом.")
            return
        days: int | None = None
        if rest:
            try:
                days = int(rest[0])
                if days < 0:
                    raise ValueError
            except ValueError:
                bot.reply_to(message,
                             "Срок (дней) — неотрицательное целое.")
                return
        db = get_db()
        product_id: int | None
        if target.lower() == "all":
            product_id = None
        elif target.isdigit():
            p = db.get_product(int(target))
            if p is None:
                bot.reply_to(message, "Товар не найден.")
                return
            product_id = p.id
        else:
            p = db.get_product_by_sku(target)
            if p is None:
                bot.reply_to(message, "Товар с таким SKU не найден.")
                return
            product_id = p.id

        valid_to = None
        if days is not None and days > 0:
            valid_to = (datetime.now() + timedelta(days=days)).isoformat(
                sep=" ", timespec="seconds")
        try:
            did = db.add_discount(kind=kind, value=value,
                                  product_id=product_id, valid_to=valid_to)
        except ValueError as exc:
            bot.reply_to(message, str(exc))
            return
        db.log_action(
            admin_id=message.from_user.id, action="add_discount",
            target=target, payload=f"{kind}:{value}:{days or '∞'}",
        )
        scope = ("ВСЕ ТОВАРЫ" if product_id is None
                 else f"товар #{product_id}")
        suffix = " (бессрочно)" if not valid_to else f" до {valid_to[:10]}"
        bot.reply_to(
            message,
            f"✅ Создана скидка #{did}: <b>{kind} {value:g}</b> "
            f"на {scope}{suffix}.",
            parse_mode="HTML",
        )

    @bot.callback_query_handler(
        func=lambda c: c.data and c.data.startswith("discount:off:"))
    @admin_only
    def cb_off(callback: CallbackQuery) -> None:
        did = int(callback.data.split(":")[-1])
        db = get_db()
        ok = db.deactivate_discount(did)
        db.log_action(
            admin_id=callback.from_user.id,
            action="deactivate_discount", target=str(did),
        )
        bot.answer_callback_query(callback.id,
                                  "Скидка отключена" if ok else "Не найдено",
                                  show_alert=not ok)
        discounts = db.list_discounts(only_active=True)
        try:
            bot.edit_message_text(
                _format_discounts_list(discounts),
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                reply_markup=discounts_list_keyboard(discounts),
                parse_mode="HTML",
            )
        except Exception:  # noqa: BLE001
            pass

    @bot.callback_query_handler(func=lambda c: c.data == "discount:new_global")
    @admin_only
    def cb_new_global(callback: CallbackQuery) -> None:
        bot.send_message(
            callback.message.chat.id,
            "🏷 Выберите тип глобальной скидки:",
            reply_markup=discount_kind_keyboard(None),
        )
        bot.answer_callback_query(callback.id)

    @bot.callback_query_handler(
        func=lambda c: c.data and c.data.startswith("discount:new:"))
    @admin_only
    def cb_new_kind(callback: CallbackQuery) -> None:
        _, _, kind, target = callback.data.split(":")
        pid = int(target) or None
        _states[callback.from_user.id] = NewDiscountState(
            step="value", kind=kind, product_id=pid)
        unit = "%" if kind == "percent" else "₽"
        scope = "глобально" if pid is None else f"для товара #{pid}"
        bot.send_message(
            callback.message.chat.id,
            f"Введите размер скидки в {unit} {scope} (или /cancel):",
        )
        bot.answer_callback_query(callback.id)

    @bot.message_handler(
        func=lambda m: m.from_user and m.from_user.id in _states
        and (m.text or "") == "/cancel")
    @admin_only
    def cancel(message: Message) -> None:
        _states.pop(message.from_user.id, None)
        bot.reply_to(message, "Отменено.")

    @bot.message_handler(
        func=lambda m: m.from_user and m.from_user.id in _states)
    @admin_only
    def step(message: Message) -> None:
        state = _states[message.from_user.id]
        text = (message.text or "").strip()
        if state.step == "value":
            try:
                value = float(text.replace(",", "."))
                if value <= 0:
                    raise ValueError
            except ValueError:
                bot.reply_to(message, "Значение должно быть > 0.")
                return
            state.value = value
            state.step = "days"
            bot.reply_to(
                message,
                "На сколько дней действует скидка? Введите число дней или "
                "<code>0</code> для бессрочной (или /cancel).",
                parse_mode="HTML",
            )
            return
        if state.step == "days":
            try:
                days = int(text)
                if days < 0:
                    raise ValueError
            except ValueError:
                bot.reply_to(message, "Введите неотрицательное целое.")
                return
            _states.pop(message.from_user.id, None)
            valid_to = None
            if days > 0:
                valid_to = (datetime.now() + timedelta(days=days)).isoformat(
                    sep=" ", timespec="seconds")
            db = get_db()
            try:
                did = db.add_discount(
                    kind=state.kind, value=state.value,
                    product_id=state.product_id, valid_to=valid_to,
                )
            except ValueError as exc:
                bot.reply_to(message, str(exc))
                return
            db.log_action(
                admin_id=message.from_user.id, action="add_discount",
                target=str(state.product_id or "all"),
                payload=f"{state.kind}:{state.value}:{days or '∞'}",
            )
            scope = ("все товары" if state.product_id is None
                     else f"товар #{state.product_id}")
            suffix = " бессрочно" if not valid_to else f" до {valid_to[:10]}"
            unit = "%" if state.kind == "percent" else "₽"
            bot.send_message(
                message.chat.id,
                f"✅ Скидка #{did} создана: "
                f"<b>−{state.value:g} {unit}</b> ({scope}){suffix}.",
                parse_mode="HTML",
            )
