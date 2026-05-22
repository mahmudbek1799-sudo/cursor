"""Фоновая синхронизация заказов с сайтом магазина.

Каждые ``settings.sync_interval`` секунд опрашивает источник заказов
(реальный или mock) и сохраняет новые позиции в БД. Каждый вновь
появившийся заказ инициирует push-уведомление администраторам.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from html import escape

from aiogram import Bot

from bot.config import settings
from bot.database.db import Database
from bot.keyboards.admin import order_actions_keyboard
from bot.services.shop_api import BaseShopAPI

logger = logging.getLogger(__name__)


class OrderSyncService:
    """Долгоживущая задача-демон, синхронизирующая заказы."""

    def __init__(self, bot: Bot, db: Database, api: BaseShopAPI) -> None:
        self._bot = bot
        self._db = db
        self._api = api
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._last_run: datetime | None = None

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run_forever(), name="order-sync")
        logger.info(
            "Сервис синхронизации заказов запущен (интервал %s c)",
            settings.sync_interval,
        )

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await asyncio.gather(self._task, return_exceptions=True)
        await self._api.close()

    @property
    def last_run(self) -> datetime | None:
        return self._last_run

    async def run_once(self) -> int:
        """Принудительный запуск одной итерации. Возвращает число новых заказов."""

        return await self._sync_iteration()

    async def sync_products(self) -> tuple[int, int]:
        """Синхронизировать каталог товаров. Возвращает (создано, обновлено)."""

        products = await self._api.fetch_products()
        created = updated = 0
        for ext in products:
            is_new = await self._db.upsert_product(ext.as_dict())
            if is_new:
                created += 1
            else:
                updated += 1
        if created or updated:
            logger.info(
                "Каталог синхронизирован: создано %s, обновлено %s",
                created, updated,
            )
        return created, updated

    async def _run_forever(self) -> None:
        product_sync_every = max(1, 600 // max(settings.sync_interval, 1))
        iterations = 0
        while not self._stop.is_set():
            try:
                await self._sync_iteration()
                iterations += 1
                if iterations % product_sync_every == 0:
                    await self.sync_products()
            except Exception:  # noqa: BLE001
                logger.exception("Ошибка в цикле синхронизации")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=settings.sync_interval)
            except asyncio.TimeoutError:
                pass

    async def _sync_iteration(self) -> int:
        self._last_run = datetime.now()
        orders = await self._api.fetch_new_orders()
        created = 0
        for ext in orders:
            is_new = await self._db.upsert_order(ext.as_dict())
            if is_new:
                created += 1
                await self._notify_admins(ext)
        if created:
            logger.info("Импортировано новых заказов: %s", created)
        return created

    async def _notify_admins(self, ext) -> None:
        text = (
            "🛒 <b>Новый заказ с сайта!</b>\n\n"
            f"Внешний номер: <code>{escape(ext.external_id)}</code>\n"
            f"Клиент: {escape(ext.customer_name)}\n"
            f"Телефон: <code>{escape(ext.customer_phone)}</code>\n"
            f"Адрес: {escape(ext.address)}\n"
            f"Сумма: <b>{ext.total:,.2f} ₽</b>\n\n"
            f"<i>Состав:</i>\n{escape(ext.items)}"
        ).replace(",", " ")
        # Получим только что созданный заказ, чтобы использовать его внутренний id
        for admin_id in settings.admin_ids:
            try:
                # Находим заказ по external_id, чтобы прикрепить кнопки управления.
                orders = await self._db.list_orders(limit=1, offset=0)
                target = next((o for o in orders if o.external_id == ext.external_id), None)
                kb = order_actions_keyboard(target.id) if target else None
                await self._bot.send_message(
                    admin_id,
                    text,
                    reply_markup=kb,
                    parse_mode="HTML",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Не удалось уведомить администратора %s: %s", admin_id, exc
                )
