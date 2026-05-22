"""Клиент API сайта мебельного магазина.

В реальной эксплуатации модуль ходит на REST API CMS (например, OpenCart,
Bitrix, 1С-Битрикс, WooCommerce и т. п.). Для целей разработки и защиты
ВКР предоставлен MockShopAPI — генератор тестовых заказов, имитирующий
ответы реального бэкенда. Замена на «боевой» источник производится в одну
строку — достаточно при инициализации передать ShopAPIClient вместо
MockShopAPI.

Если у магазина нет API, аналогичный слой можно собрать поверх
BeautifulSoup4/Requests, парся HTML страницы /admin/orders. Пример такой
реализации приведён в методе ``ShopAPIClient.parse_html_orders``.
"""

from __future__ import annotations

import abc
import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ExternalOrder:
    external_id: str
    customer_name: str
    customer_phone: str
    customer_telegram_id: Optional[int]
    address: str
    items: str
    total: float
    status: str = "new"
    comment: str = ""

    def as_dict(self) -> dict:
        return {
            "external_id": self.external_id,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "customer_telegram_id": self.customer_telegram_id,
            "address": self.address,
            "items": self.items,
            "total": self.total,
            "status": self.status,
            "comment": self.comment,
        }


class BaseShopAPI(abc.ABC):
    """Интерфейс источника заказов."""

    @abc.abstractmethod
    async def fetch_new_orders(self) -> List[ExternalOrder]:
        ...

    async def close(self) -> None:  # pragma: no cover - default impl
        return None


class ShopAPIClient(BaseShopAPI):
    """Реальный HTTP-клиент к API магазина.

    Ожидается endpoint ``GET {SHOP_API_URL}?status=new``, возвращающий JSON
    в формате ``{"orders": [{...}]}``. Авторизация — Bearer-токеном.
    """

    def __init__(self, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=aiohttp.ClientTimeout(total=15),
            )
        return self._session

    async def fetch_new_orders(self) -> List[ExternalOrder]:
        try:
            session = await self._ensure_session()
            async with session.get(self._base_url, params={"status": "new"}) as resp:
                resp.raise_for_status()
                payload = await resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.error("Не удалось получить заказы с сайта: %s", exc)
            return []
        return [
            ExternalOrder(
                external_id=str(item["id"]),
                customer_name=item.get("customer", {}).get("name", ""),
                customer_phone=item.get("customer", {}).get("phone", ""),
                customer_telegram_id=item.get("customer", {}).get("telegram_id"),
                address=item.get("address", ""),
                items="\n".join(
                    f"• {p['title']} × {p['qty']}"
                    for p in item.get("items", [])
                ),
                total=float(item.get("total", 0)),
                status=item.get("status", "new"),
                comment=item.get("comment", ""),
            )
            for item in payload.get("orders", [])
        ]

    @staticmethod
    def parse_html_orders(html: str) -> List[ExternalOrder]:
        """Резервный сценарий — парсинг страницы админки сайта.

        Используется, если у магазина нет публичного API. Структура DOM
        приведена для типового движка интернет-магазина мебели.
        """

        soup = BeautifulSoup(html, "html.parser")
        orders: List[ExternalOrder] = []
        for row in soup.select("table.orders tbody tr"):
            try:
                orders.append(
                    ExternalOrder(
                        external_id=row.select_one(".order-id").get_text(strip=True),
                        customer_name=row.select_one(".customer-name").get_text(strip=True),
                        customer_phone=row.select_one(".customer-phone").get_text(strip=True),
                        customer_telegram_id=None,
                        address=row.select_one(".address").get_text(strip=True),
                        items=row.select_one(".items").get_text("\n", strip=True),
                        total=float(
                            row.select_one(".total").get_text(strip=True)
                            .replace("₽", "").replace(" ", "").replace(",", ".")
                        ),
                        status=row.select_one(".status").get_text(strip=True) or "new",
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Пропускаю строку заказа из-за ошибки парсинга: %s", exc)
        return orders

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()


class MockShopAPI(BaseShopAPI):
    """Имитатор API магазина для разработки и демонстраций.

    Каждый второй вызов «находит» 0-2 новых заказа, чтобы было удобно
    наблюдать поведение бота вживую. Чтобы переключиться на реальный API
    магазина, достаточно в ``main.py`` поменять ``MockShopAPI()`` на
    ``ShopAPIClient(settings.shop_api_url, settings.shop_api_token)``.
    """

    _CATALOG = [
        ("Диван «Стокгольм»", 65990),
        ("Кровать «Норд» 160×200", 42990),
        ("Стол обеденный «Орегон»", 24990),
        ("Шкаф-купе «Капри» 2.0м", 38990),
        ("Кресло «Лофт»", 17990),
        ("Комод «Прованс»", 21990),
        ("Стул «Венский» (2 шт.)", 9990),
        ("Тумба ТВ «Бергамо»", 15990),
    ]
    _NAMES = ["Иванов И. И.", "Петрова А. С.", "Сидоров К. В.",
              "Козлов М. Д.", "Орлова Е. П.", "Лебедев Д. Н."]
    _STREETS = ["ул. Ленина, 15, кв. 12", "пр. Победы, 87, кв. 4",
                "ул. Мира, 3, кв. 56", "ул. Гагарина, 21, кв. 99"]

    def __init__(self) -> None:
        self._counter = int(datetime.now().timestamp())

    async def fetch_new_orders(self) -> List[ExternalOrder]:
        await asyncio.sleep(0.05)
        n = random.choices([0, 1, 2], weights=[0.5, 0.35, 0.15])[0]
        result: List[ExternalOrder] = []
        for _ in range(n):
            self._counter += 1
            items_sample = random.sample(self._CATALOG, k=random.randint(1, 3))
            items_lines = []
            total = 0.0
            for title, price in items_sample:
                qty = random.randint(1, 2)
                items_lines.append(f"• {title} × {qty}")
                total += price * qty
            result.append(
                ExternalOrder(
                    external_id=f"WEB-{self._counter}",
                    customer_name=random.choice(self._NAMES),
                    customer_phone=f"+7 (9{random.randint(10, 99)}) "
                                   f"{random.randint(100, 999)}-"
                                   f"{random.randint(10, 99)}-"
                                   f"{random.randint(10, 99)}",
                    customer_telegram_id=None,
                    address=random.choice(self._STREETS),
                    items="\n".join(items_lines),
                    total=total,
                    status="new",
                    comment="",
                )
            )
        return result
