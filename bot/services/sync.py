"""Фоновая синхронизация заказов и каталога с сайтом магазина.

Реализована в виде отдельного потока (``threading.Thread``), поскольку
сам telebot работает синхронно с polling. Поток опрашивает источник
данных каждые ``SYNC_INTERVAL`` секунд и при появлении новых заказов
отправляет администраторам push-уведомление.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from html import escape
from typing import Optional

from telebot import TeleBot

from bot.config import settings
from bot.database import Database
from bot.keyboards import order_actions_keyboard
from bot.services.shop_api import BaseShopAPI

logger = logging.getLogger(__name__)


class OrderSyncService:
    """Фоновый сервис синхронизации заказов и каталога."""

    def __init__(self, bot: TeleBot, db: Database, api: BaseShopAPI) -> None:
        self._bot = bot
        self._db = db
        self._api = api
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_run: Optional[datetime] = None
        self._lock = threading.Lock()

    @property
    def last_run(self) -> Optional[datetime]:
        return self._last_run

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_forever,
            name="order-sync", daemon=True,
        )
        self._thread.start()
        logger.info("Сервис синхронизации запущен (интервал %s c)",
                    settings.sync_interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._api.close()

    def run_once(self) -> int:
        """Принудительный запуск одной итерации."""

        with self._lock:
            return self._sync_iteration()

    def sync_products(self) -> tuple[int, int]:
        """Синхронизировать каталог товаров."""

        with self._lock:
            products = self._api.fetch_products()
            created = updated = 0
            for ext in products:
                is_new = self._db.upsert_product(ext.as_dict())
                if is_new:
                    created += 1
                else:
                    updated += 1
            if created or updated:
                logger.info("Каталог: создано %s, обновлено %s",
                            created, updated)
            return created, updated

    # ------------------------------------------------------------------
    def _run_forever(self) -> None:
        product_sync_every = max(1, 600 // max(settings.sync_interval, 1))
        iterations = 0
        while not self._stop_event.is_set():
            try:
                with self._lock:
                    self._sync_iteration()
                iterations += 1
                if iterations % product_sync_every == 0:
                    self.sync_products()
            except Exception:  # noqa: BLE001
                logger.exception("Ошибка в цикле синхронизации")
            self._stop_event.wait(settings.sync_interval)

    def _sync_iteration(self) -> int:
        self._last_run = datetime.now()
        orders = self._api.fetch_new_orders()
        created = 0
        for ext in orders:
            is_new = self._db.upsert_order(ext.as_dict())
            if is_new:
                created += 1
                self._notify_admins(ext)
        if created:
            logger.info("Импортировано новых заказов: %s", created)
        return created

    def _notify_admins(self, ext) -> None:
        text = (
            "🛒 <b>Новый заказ с сайта!</b>\n\n"
            f"Внешний номер: <code>{escape(ext.external_id)}</code>\n"
            f"Клиент: {escape(ext.customer_name)}\n"
            f"Телефон: <code>{escape(ext.customer_phone)}</code>\n"
            f"Адрес: {escape(ext.address)}\n"
            f"Сумма: <b>{ext.total:,.2f} ₽</b>\n\n"
            f"<i>Состав:</i>\n{escape(ext.items)}"
        ).replace(",", " ")
        latest = self._db.list_orders(limit=1, offset=0)
        target = next((o for o in latest
                       if o.external_id == ext.external_id), None)
        kb = order_actions_keyboard(target.id) if target else None
        for admin_id in settings.admin_ids:
            try:
                self._bot.send_message(admin_id, text, parse_mode="HTML",
                                       reply_markup=kb)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Не удалось уведомить администратора %s: %s",
                               admin_id, exc)
