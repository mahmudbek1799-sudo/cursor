"""Источники данных о заказах и каталоге.

Реализованы три варианта интеграции с сайтом магазина (все
синхронные, на стандартной библиотеке ``requests`` и BeautifulSoup4 —
строго по техническому заданию):

* :class:`ShopAPIClient` — REST-клиент, если у магазина есть API;
* :class:`HTMLShopParser` — парсер HTML-страниц «без API»;
* :class:`MockShopAPI` — генератор тестовых заказов для разработки и
  защиты ВКР.

Переключение между ними выполняется функцией :func:`build_shop_source`
в зависимости от значения переменной окружения ``SHOP_SOURCE``.
"""

from __future__ import annotations

import abc
import logging
import random
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from bot.config import settings

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
    """Интерфейс источника данных магазина."""

    @abc.abstractmethod
    def fetch_new_orders(self) -> List[ExternalOrder]:
        ...

    def fetch_products(self) -> List[ExternalProduct]:
        return []

    def close(self) -> None:  # pragma: no cover - default impl
        return None


# ---------------------------------------------------------------------------
# REST-клиент
# ---------------------------------------------------------------------------
class ShopAPIClient(BaseShopAPI):
    """Реальный HTTP-клиент к API магазина.

    Ожидается endpoint ``GET {SHOP_API_URL}?status=new``, возвращающий
    JSON в формате ``{"orders": [...]}``. Авторизация — Bearer-токеном.
    Поддерживается работа через прокси (см. :func:`bot.config.Settings`).
    """

    def __init__(self, base_url: str, token: str,
                 proxy_url: Optional[str] = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {token}",
            "User-Agent": "FurnitureAdminBot/2.0",
        })
        if proxy_url:
            self._session.proxies.update({
                "http": proxy_url, "https": proxy_url,
            })

    def fetch_new_orders(self) -> List[ExternalOrder]:
        try:
            resp = self._session.get(self._base_url,
                                     params={"status": "new"},
                                     timeout=15)
            resp.raise_for_status()
            payload = resp.json()
        except requests.RequestException as exc:
            logger.error("ShopAPIClient: ошибка запроса заказов: %s", exc)
            return []
        return [
            ExternalOrder(
                external_id=str(item["id"]),
                customer_name=item.get("customer", {}).get("name", ""),
                customer_phone=item.get("customer", {}).get("phone", ""),
                customer_telegram_id=item.get("customer", {}).get(
                    "telegram_id"),
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

    def close(self) -> None:
        self._session.close()


# ---------------------------------------------------------------------------
# HTML-парсер «без API»
# ---------------------------------------------------------------------------
class HTMLShopParser(BaseShopAPI):
    """Парсер интернет-магазина без публичного API.

    Скачивает HTML-страницы каталога и админки при помощи
    :mod:`requests` и извлекает данные через :class:`BeautifulSoup`.
    Селекторы можно переопределять — это позволяет подстраиваться под
    любой типовой шаблон CMS (OpenCart, WooCommerce, Bitrix, Tilda).
    Авторизация в админке — через cookies, передаваемые в конструктор.
    """

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
        "row":     "table.orders tbody tr, table.admin-orders tbody tr",
        "id":      ".order-id, td.col-id",
        "name":    ".customer-name, td.col-name",
        "phone":   ".customer-phone, td.col-phone",
        "address": ".address, td.col-address",
        "items":   ".items, td.col-items",
        "total":   ".total, td.col-total",
        "status":  ".status, td.col-status",
    }

    def __init__(
        self,
        catalog_url: str,
        orders_url: Optional[str] = None,
        cookies: Optional[dict] = None,
        user_agent: Optional[str] = None,
        product_selectors: Optional[dict] = None,
        order_selectors: Optional[dict] = None,
        proxy_url: Optional[str] = None,
    ) -> None:
        self._catalog_url = catalog_url
        self._orders_url = orders_url
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": user_agent or (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        })
        if cookies:
            self._session.cookies.update(cookies)
        if proxy_url:
            self._session.proxies.update({
                "http": proxy_url, "https": proxy_url,
            })
        self._product_sel = {**self.DEFAULT_PRODUCT_SELECTORS,
                             **(product_selectors or {})}
        self._order_sel = {**self.DEFAULT_ORDER_SELECTORS,
                           **(order_selectors or {})}

    # ------------------------------------------------------------------
    def _fetch(self, url: str) -> Optional[str]:
        try:
            resp = self._session.get(url, timeout=20)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            logger.error("HTMLShopParser: ошибка GET %s — %s", url, exc)
            return None

    def fetch_products(self) -> List[ExternalProduct]:
        if not self._catalog_url:
            return []
        html = self._fetch(self._catalog_url)
        if not html:
            return []
        return self.parse_products_html(html, self._product_sel)

    def fetch_new_orders(self) -> List[ExternalOrder]:
        if not self._orders_url:
            return []
        html = self._fetch(self._orders_url)
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
                    sku = ((sku_el.get("data-sku") or "").strip()
                           if sku_el.has_attr("data-sku")
                           else sku_el.get_text(strip=True))
            if not sku:
                sku = "SKU-" + "".join(
                    c for c in title.lower() if c.isalnum()
                )[:24]
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
            description = (desc_el.get_text(" ", strip=True)
                           if desc_el else "")
            result.append(ExternalProduct(
                sku=sku, title=title, category=category or "other",
                price=price, stock=stock, description=description[:500],
            ))
        return result

    @staticmethod
    def parse_orders_html(html: str, sel: dict) -> List[ExternalOrder]:
        soup = BeautifulSoup(html, "html.parser")
        status_map = {
            "новый": "new", "new": "new",
            "подтверждён": "confirmed", "confirmed": "confirmed",
            "в доставке": "in_delivery", "in_delivery": "in_delivery",
            "завершён": "completed", "completed": "completed",
            "отменён": "cancelled", "cancelled": "cancelled",
        }
        orders: List[ExternalOrder] = []
        for row in soup.select(sel["row"]):
            try:
                ext_id = row.select_one(sel["id"]).get_text(strip=True)
                name = row.select_one(sel["name"]).get_text(strip=True)
                phone = row.select_one(sel["phone"]).get_text(strip=True)
                address = row.select_one(sel["address"]).get_text(strip=True)
                items = row.select_one(sel["items"]).get_text(
                    "\n", strip=True)
                total = HTMLShopParser._parse_price(
                    row.select_one(sel["total"]).get_text()
                )
                status_el = row.select_one(sel["status"])
                status = (status_el.get_text(strip=True).lower()
                          if status_el else "new")
                orders.append(ExternalOrder(
                    external_id=ext_id, customer_name=name,
                    customer_phone=phone, customer_telegram_id=None,
                    address=address, items=items, total=total,
                    status=status_map.get(status, "new"),
                ))
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "HTMLShopParser: пропуск строки заказа: %s", exc)
        return orders

    @staticmethod
    def _parse_price(raw: str) -> float:
        """Преобразовать строку с ценой в float.

        Поддерживает форматы «65 990 ₽», «65,990.00», «42500».
        """

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

    def close(self) -> None:
        self._session.close()


# ---------------------------------------------------------------------------
# Mock-источник
# ---------------------------------------------------------------------------
class MockShopAPI(BaseShopAPI):
    """Имитатор API магазина для разработки и демонстраций."""

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

    def fetch_products(self) -> List[ExternalProduct]:
        result: List[ExternalProduct] = []
        for title, price in self._CATALOG:
            sku = "MOCK-" + "".join(
                c for c in title.lower() if c.isalnum()
            )[:24]
            category = self._guess_category(title)
            result.append(ExternalProduct(
                sku=sku, title=title, category=category,
                price=float(price), stock=random.randint(2, 12),
                description=f"{title} — современная модель из "
                            f"коллекции 2026 года.",
            ))
        return result

    @staticmethod
    def _guess_category(title: str) -> str:
        title_low = title.lower()
        for key in ("диван", "кровать", "стол", "шкаф",
                    "кресло", "комод", "стул", "тумба"):
            if key in title_low:
                return key
        return "другое"

    def fetch_new_orders(self) -> List[ExternalOrder]:
        n = random.choices([0, 1, 2], weights=[0.5, 0.35, 0.15])[0]
        result: List[ExternalOrder] = []
        for _ in range(n):
            self._counter += 1
            items_sample = random.sample(self._CATALOG,
                                         k=random.randint(1, 3))
            items_lines: list[str] = []
            total = 0.0
            for title, price in items_sample:
                qty = random.randint(1, 2)
                items_lines.append(f"• {title} × {qty}")
                total += price * qty
            result.append(ExternalOrder(
                external_id=f"WEB-{self._counter}",
                customer_name=random.choice(self._NAMES),
                customer_phone=(
                    f"+7 (9{random.randint(10, 99)}) "
                    f"{random.randint(100, 999)}-"
                    f"{random.randint(10, 99)}-"
                    f"{random.randint(10, 99)}"
                ),
                customer_telegram_id=None,
                address=random.choice(self._STREETS),
                items="\n".join(items_lines),
                total=total, status="new", comment="",
            ))
        return result


# ---------------------------------------------------------------------------
# Фабрика источника
# ---------------------------------------------------------------------------
def build_shop_source() -> BaseShopAPI:
    """Выбрать источник данных по значению ``SHOP_SOURCE`` в .env.

    * ``mock`` (по умолчанию) — генератор тестовых заказов;
    * ``api``  — реальный REST-клиент;
    * ``html`` — парсинг HTML-страниц без API.

    Прокси берётся из настроек ``PROXY_*`` (для работы при блокировках
    Telegram на территории РФ).
    """

    proxy = settings.proxy_url()
    source = settings.shop_source.lower()
    if source == "api":
        logger.info("Источник данных: REST API (%s)", settings.shop_api_url)
        return ShopAPIClient(settings.shop_api_url,
                             settings.shop_api_token,
                             proxy_url=proxy)
    if source == "html":
        logger.info(
            "Источник данных: HTML-парсинг (каталог=%s, заказы=%s)",
            settings.shop_catalog_url or "—",
            settings.shop_orders_url or "—",
        )
        return HTMLShopParser(
            catalog_url=settings.shop_catalog_url,
            orders_url=settings.shop_orders_url or None,
            cookies=settings.parsed_cookies(),
            proxy_url=proxy,
        )
    logger.info("Источник данных: MockShopAPI (демо-режим)")
    return MockShopAPI()
