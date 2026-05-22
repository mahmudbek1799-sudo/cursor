"""Обработчики событий Telegram-бота.

Каждый модуль регистрирует свой :class:`aiogram.Router`, что позволяет
изолировать логику и легко покрывать её модульными тестами.
"""

from aiogram import Router

from bot.handlers import (
    broadcast,
    common,
    discounts,
    orders,
    products,
    stats,
    sync_cmd,
    users,
)

router = Router(name="root")
router.include_router(common.router)
router.include_router(orders.router)
router.include_router(products.router)
router.include_router(discounts.router)
router.include_router(broadcast.router)
router.include_router(stats.router)
router.include_router(users.router)
router.include_router(sync_cmd.router)

__all__ = ["router"]
