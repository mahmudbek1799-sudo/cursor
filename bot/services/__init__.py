"""Сервисный слой: интеграция с сайтом магазина и аналитика."""

from bot.services.shop_api import ShopAPIClient, MockShopAPI
from bot.services.analytics import build_orders_chart
from bot.services.sync import OrderSyncService

__all__ = [
    "ShopAPIClient",
    "MockShopAPI",
    "build_orders_chart",
    "OrderSyncService",
]
