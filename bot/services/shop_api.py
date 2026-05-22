"""Источники данных о заказах и каталоге мебельного магазина.

В модуле реализовано несколько источников, объединённых общим
интерфейсом ``BaseShopAPI``:

* ``ShopAPIClient`` — реальный REST-клиент (если у магазина есть API);
* ``HTMLShopParser`` — резервный режим «без API»: бот периодически
  скачивает HTML-страницы каталога и админки и извлекает данные с
  помощью ``BeautifulSoup4``. Селекторы настраиваются параметрами;
  значения по умолчанию подобраны под типовой шаблон интернет-магазина
  мебели (OpenCart/Bootstrap-разметка);
* ``MockShopAPI`` — генератор тестовых заказов для демонстрации
  и защиты ВКР без реального магазина.

Переход между источниками выполняется в одной строке ``bot/main.py``.
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


@dataclass(slots=True)
class ExternalProduct:
    """DTO товара, извлечённого со страницы каталога."""

    sku: str
    title: str
    category: str
    price: float
    stock: int = 1
    description: str = ""

    def as_dict(self) -> dict:
        return {
            "sku": self.sku,
            "title": self.title,
            "category": self.category,
            "price": self.price,
            "stock": self.stock,
            "description": self.description,
            "is_active": 1,
        }


class BaseShopAPI(abc.ABC):
    """Интерфейс источника заказов."""

    @abc.abstractmethod
    async def fetch_new_orders(self) -> List[ExternalOrder]:
        ...

    async def fetch_products(self) -> List[ExternalProduct]:
        """Получить каталог товаров. По умолчанию — пусто."""

        return []

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


class HTMLShopParser(BaseShopAPI):
    """Парсер интернет-магазина без публичного API.

    Скачивает HTML-страницы (каталог товаров и список заказов в админке)
    при помощи ``aiohttp`` и извлекает данные с помощью ``BeautifulSoup4``.
    Селекторы можно переопределять — это позволяет подстраиваться под
    любой типовой шаблон CMS (OpenCart, WooCommerce, Bitrix, Tilda).

    Аутентификация в админке — через переданные cookies (рекомендуется
    скопировать `PHPSESSID` или `Cookie: admin_session=...` из браузера).
    """

    # Селекторы для типового шаблона интернет-магазина мебели.
    DEFAULT_PRODUCT_SELECTORS = {
        "card":        ".product-card, .product-item, .product-layout",
        "title":       ".product-title, .product-name, h3, h4",
        "price":       ".product-price, .price, .price-new",
        "category":    ".product-category, .category",
        "sku":         "[data-sku], .product-sku",
        "stock":       ".stock, .availability",
        "description": ".product-description, .description",
    }

    DEFAULT_ORDER_SELECTORS = {
        "row":      "table.orders tbody tr, table.admin-orders tbody tr",
        "id":       ".order-id, td.col-id",
        "name":     ".customer-name, td.col-name",
        "phone":    ".customer-phone, td.col-phone",
        "address":  ".address, td.col-address",
        "items":    ".items, td.col-items",
        "total":    ".total, td.col-total",
        "status":   ".status, td.col-status",
    }

    def __init__(
        self,
        catalog_url: str,
        orders_url: Optional[str] = None,
        cookies: Optional[dict] = None,
        user_agent: Optional[str] = None,
        product_selectors: Optional[dict] = None,
        order_selectors: Optional[dict] = None,
    ) -> None:
        self._catalog_url = catalog_url
        self._orders_url = orders_url
        self._cookies = cookies or {}
        self._user_agent = (
            user_agent
            or "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        self._product_sel = {**self.DEFAULT_PRODUCT_SELECTORS,
                             **(product_selectors or {})}
        self._order_sel = {**self.DEFAULT_ORDER_SELECTORS,
                           **(order_selectors or {})}
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            jar = aiohttp.CookieJar()
            self._session = aiohttp.ClientSession(
                headers={"User-Agent": self._user_agent},
                cookies=self._cookies,
                cookie_jar=jar,
                timeout=aiohttp.ClientTimeout(total=20),
            )
        return self._session

    async def _fetch(self, url: str) -> Optional[str]:
        try:
            session = await self._ensure_session()
            async with session.get(url) as resp:
                resp.raise_for_status()
                return await resp.text()
        except Exception as exc:  # noqa: BLE001
            logger.error("HTMLShopParser: ошибка GET %s — %s", url, exc)
            return None

    async def fetch_products(self) -> List[ExternalProduct]:
        """Скачать страницу каталога и извлечь карточки товаров."""

        html = await self._fetch(self._catalog_url)
        if not html:
            return []
        return self.parse_products_html(html, self._product_sel)

    async def fetch_new_orders(self) -> List[ExternalOrder]:
        """Скачать список заказов из админки и распарсить таблицу."""

        if not self._orders_url:
            return []
        html = await self._fetch(self._orders_url)
        if not html:
            return []
        return self.parse_orders_html(html, self._order_sel)

    # ------------------------------------------------------------------
    # Чистые функции парсинга (легко тестируются модульно)
    # ------------------------------------------------------------------
    @staticmethod
    def parse_products_html(html: str, sel: dict) -> List[ExternalProduct]:
        soup = BeautifulSoup(html, "html.parser")
        result: List[ExternalProduct] = []
        for card in soup.select(sel["card"]):
            title_el = card.select_one(sel["title"])
            price_el = card.select_one(sel["price"])
            if title_el is None or price_el is None:
                continue
            title = title_el.get_text(strip=True)
            try:
                price = HTMLShopParser._parse_price(price_el.get_text())
            except ValueError:
                continue
            sku = ""
            if card.has_attr("data-sku"):
                sku = str(card["data-sku"]).strip()
            if not sku:
                sku_el = card.select_one(sel["sku"])
                if sku_el is not None:
                    sku = (sku_el.get("data-sku") or "").strip() \
                        if sku_el.has_attr("data-sku") \
                        else sku_el.get_text(strip=True)
            if not sku:
                # Если артикул отсутствует — генерируем из названия.
                sku = "SKU-" + "".join(c for c in title.lower() if c.isalnum())[:24]
            cat_el = card.select_one(sel["category"])
            category = cat_el.get_text(strip=True) if cat_el else "other"
            stock_el = card.select_one(sel["stock"])
            stock = 1
            if stock_el is not None:
                txt = stock_el.get_text().lower()
                if any(w in txt for w in ("нет", "не в нал", "out")):
                    stock = 0
                else:
                    digits = "".join(c for c in txt if c.isdigit())
                    if digits:
                        stock = int(digits)
            desc_el = card.select_one(sel["description"])
            description = desc_el.get_text(" ", strip=True) if desc_el else ""
            result.append(
                ExternalProduct(
                    sku=sku,
                    title=title,
                    category=category or "other",
                    price=price,
                    stock=stock,
                    description=description[:500],
                )
            )
        return result

    @staticmethod
    def parse_orders_html(html: str, sel: dict) -> List[ExternalOrder]:
        soup = BeautifulSoup(html, "html.parser")
        orders: List[ExternalOrder] = []
        for row in soup.select(sel["row"]):
            try:
                ext_id = row.select_one(sel["id"]).get_text(strip=True)
                name = row.select_one(sel["name"]).get_text(strip=True)
                phone = row.select_one(sel["phone"]).get_text(strip=True)
                address = row.select_one(sel["address"]).get_text(strip=True)
                items = row.select_one(sel["items"]).get_text("\n", strip=True)
                total = HTMLShopParser._parse_price(
                    row.select_one(sel["total"]).get_text()
                )
                status_el = row.select_one(sel["status"])
                status = (status_el.get_text(strip=True).lower()
                          if status_el else "new")
                status_map = {
                    "новый": "new", "new": "new",
                    "подтверждён": "confirmed", "confirmed": "confirmed",
                    "в доставке": "in_delivery", "in_delivery": "in_delivery",
                    "завершён": "completed", "completed": "completed",
                    "отменён": "cancelled", "cancelled": "cancelled",
                }
                orders.append(
                    ExternalOrder(
                        external_id=ext_id,
                        customer_name=name,
                        customer_phone=phone,
                        customer_telegram_id=None,
                        address=address,
                        items=items,
                        total=total,
                        status=status_map.get(status, "new"),
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("HTMLShopParser: пропуск строки заказа: %s", exc)
        return orders

    @staticmethod
    def _parse_price(raw: str) -> float:
        """Преобразовать строку с ценой («65 990 ₽», «65,990.00») в float."""

        cleaned = "".join(
            ch for ch in raw if ch.isdigit() or ch in (",", ".", "-")
        )
        cleaned = cleaned.replace(" ", "")
        if not cleaned:
            raise ValueError(f"Не удалось разобрать цену: {raw!r}")
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", ".")
        return float(cleaned)

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

    async def fetch_products(self) -> List[ExternalProduct]:
        result: List[ExternalProduct] = []
        for title, price in self._CATALOG:
            sku = "MOCK-" + "".join(
                c for c in title.lower() if c.isalnum()
            )[:24]
            category = "диван" if "Диван" in title else (
                "кровать" if "Кров" in title else (
                    "стол" if "Стол" in title else (
                        "кресло" if "Кресло" in title else (
                            "комод" if "Комод" in title else (
                                "стул" if "Стул" in title else (
                                    "шкаф" if "Шкаф" in title else (
                                        "тумба" if "Тумба" in title else "другое"
                                    )
                                )
                            )
                        )
                    )
                )
            )
            result.append(
                ExternalProduct(
                    sku=sku,
                    title=title,
                    category=category,
                    price=float(price),
                    stock=random.randint(2, 12),
                    description=f"{title} — современная модель из коллекции 2026 года.",
                )
            )
        return result

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
