"""Сервисный слой: интеграция с сайтом магазина и аналитика."""

from bot.services.shop_api import (
    BaseShopAPI,
    ExternalOrder,
    ExternalProduct,
    HTMLShopParser,
    MockShopAPI,
    ShopAPIClient,
)
from bot.services.analytics import build_orders_chart
from bot.services.sync import OrderSyncService

__all__ = [
    "BaseShopAPI",
    "ExternalOrder",
    "ExternalProduct",
    "HTMLShopParser",
    "MockShopAPI",
    "ShopAPIClient",
    "build_orders_chart",
    "OrderSyncService",
]
