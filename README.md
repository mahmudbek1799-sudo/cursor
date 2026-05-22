# Telegram-бот администратора мебельного магазина

ВКР: «Разработка Telegram-бота для администратора типового мебельного
магазина» (Гафуров М. М., направление 09.03.04 «Программная инженерия»,
ВоГУ, 2026 г.).

Бот выполняет обязанности администратора сайта мебельного магазина:
принимает заказы с сайта, уведомляет администратора, ведёт каталог
заказов, меняет их статус, отправляет сообщения клиентам, ведёт чёрный
список, формирует аналитические дашборды и журнал действий.

## Технологический стек

| Назначение        | Технология              |
|-------------------|-------------------------|
| Язык              | Python 3.11+            |
| Telegram          | aiogram 3.x (асинхронный) |
| База данных       | SQLite (aiosqlite)      |
| Аналитика         | Matplotlib              |
| Парсинг сайта     | aiohttp + BeautifulSoup4 |
| Документация ВКР  | python-docx             |
| Контроль версий   | Git                     |

## Структура проекта

```
.
├── bot/
│   ├── config.py              # настройки из .env (Pydantic Settings)
│   ├── main.py                # точка входа (asyncio + aiogram Dispatcher)
│   ├── database/db.py         # асинхронный слой SQLite (orders, products,
│   │                            discounts, clients, blocked_users, admin_actions)
│   ├── keyboards/admin.py     # reply- и inline-клавиатуры
│   ├── middlewares/access.py  # контроль доступа администратора
│   ├── handlers/              # common, orders, products, discounts,
│   │                            stats, users, broadcast, sync_cmd
│   ├── services/
│   │   ├── shop_api.py        # ShopAPIClient (REST) + HTMLShopParser (без API)
│   │   │                        + MockShopAPI (демо)
│   │   ├── sync.py            # фоновая синхронизация заказов и каталога
│   │   └── analytics.py       # дашборды на Matplotlib
│   └── utils/                 # логирование, форматирование (orders + products)
├── scripts/
│   ├── seed_demo.py           # наполнение БД демо-данными (заказы, товары, скидки)
│   ├── build_vkr.py           # сборка пояснительной записки ВКР по ГОСТ
│   └── build_otchet.py        # сборка отчёта по проектно-технологической практике
├── docs/
│   ├── Gafurov_VKR.docx
│   └── Gafurov_Otchet_PTP.docx
├── requirements.txt
├── .env.example
└── README.md
```

## Установка

```bash
git clone <repo_url>
cd <repo_dir>

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

## Настройка

1. Получите токен у [@BotFather](https://t.me/BotFather).
2. Узнайте свой Telegram-ID у [@userinfobot](https://t.me/userinfobot).
3. Скопируйте `.env.example` в `.env` и заполните значения:

```bash
cp .env.example .env
```

```ini
BOT_TOKEN=123456:AA...
ADMIN_IDS=111111111,222222222
DB_PATH=data/furniture_bot.sqlite3
SHOP_API_URL=https://shop.example.com/api/orders
SHOP_API_TOKEN=secret
SYNC_INTERVAL=60
LOG_LEVEL=INFO
```

## Запуск

```bash
python -m bot.main
```

При первом запуске будет создана БД `data/furniture_bot.sqlite3`, в
консоль и в файл `logs/bot.log` начнёт выводиться диагностика. После
этого администратор пишет боту `/start`.

## Демонстрационные данные

Чтобы наполнить БД фиктивными заказами и клиентами (полезно для
демонстрации статистики и дашбордов):

```bash
python scripts/seed_demo.py
```

## Сборка пояснительной записки ВКР

Для сборки `docs/Gafurov_VKR.docx` (ГОСТ, Times New Roman 14, поля 30/15/20/20,
полуторный интервал, автоматическое содержание):

```bash
python scripts/build_vkr.py
```

## Сборка отчёта по проектно-технологической практике

Для сборки `docs/Gafurov_Otchet_PTP.docx` (типовой формат отчёта по ПТП ВоГУ):

```bash
python scripts/build_otchet.py
```

## Команды бота

### Заказы
| Команда | Назначение |
|---------|------------|
| `/orders [active|done|all|<статус>]` | Список заказов |
| `/order <id>` или `/order_<id>` | Карточка заказа |
| `/sync` | Принудительный приём заказов с сайта |
| `/parse_site` | Парсинг каталога сайта без API |

### Товары
| Команда | Назначение |
|---------|------------|
| `/products` | Каталог товаров с пагинацией |
| `/product <id|sku>` | Карточка товара |
| `/add_product` | Мастер добавления товара (FSM) |
| `/del_product <id|sku>` | Удалить товар |
| `/price <id|sku> <цена>` | Изменить цену |

### Скидки
| Команда | Назначение |
|---------|------------|
| `/discounts` | Список активных скидок |
| `/discount <sku|id|all> <percent|fixed> <значение> [дней]` | Создать скидку |

Примеры:
- `/discount all percent 10 7` — −10 % на весь каталог на 7 дней
- `/discount SOFA-001 fixed 5000` — минус 5000 ₽ на конкретный диван

### Клиенты и рассылка
| Команда | Назначение |
|---------|------------|
| `/block <id> [причина]` | Добавить в чёрный список |
| `/unblock <id>` | Снять блокировку |
| `/blocked` | Чёрный список |
| `/send <id> <текст>` | Личное сообщение |
| `/send_all <текст>` | Массовая рассылка |

### Аналитика и общие
| Команда | Назначение |
|---------|------------|
| `/stats` | Сводная статистика |
| `/dashboard` | График заказов за 7 дней |
| `/log` | Журнал действий администратора |
| `/start`, `/help` | Главное меню / справка |

## Интеграция с сайтом магазина

Источник данных выбирается переменной окружения **`SHOP_SOURCE`**
(`mock` | `api` | `html`):

```ini
# .env — выбор источника:
SHOP_SOURCE=html            # парсинг сайта без API
SHOP_CATALOG_URL=https://shop.example.com/catalog/mebel
SHOP_ORDERS_URL=https://shop.example.com/admin/orders
SHOP_COOKIES=PHPSESSID=abcd1234; admin_session=xyz   # авторизация в админке
```

| Значение | Класс | Назначение |
|----------|-------|------------|
| `mock` (по умолчанию) | `MockShopAPI` | Генератор тестовых заказов и каталога для разработки и защиты ВКР |
| `api` | `ShopAPIClient` | Реальный REST-клиент к API CMS магазина |
| `html` | `HTMLShopParser` | Парсинг HTML-страниц каталога и админки без API |

### Режим `api`

`ShopAPIClient` ожидает REST-эндпоинт `GET /api/orders?status=new` с
ответом вида:

```json
{
  "orders": [
    {
      "id": "WEB-128",
      "customer": {"name": "Иванов И. И.", "phone": "+7...", "telegram_id": null},
      "address": "ул. Ленина, 15",
      "items": [{"title": "Диван «Стокгольм»", "qty": 1}],
      "total": 65990,
      "status": "new",
      "comment": ""
    }
  ]
}
```

### Режим `html` (без API)

`HTMLShopParser` сам скачивает HTML-страницы каталога/админки и
извлекает данные при помощи BeautifulSoup4. Селекторы по умолчанию
рассчитаны на типовой шаблон интернет-магазина мебели (OpenCart/Bootstrap):

```python
DEFAULT_PRODUCT_SELECTORS = {
    "card":  ".product-card, .product-item, .product-layout",
    "title": ".product-title, .product-name, h3, h4",
    "price": ".product-price, .price, .price-new",
    "sku":   "[data-sku], .product-sku",
    "stock": ".stock, .availability",
}
```

Селекторы можно переопределить через конструктор `HTMLShopParser`.
Авторизация в админке — через cookies (`SHOP_COOKIES`).

Команда `/parse_site` запускает разовый парсинг каталога и обновляет
таблицу `products` (UPSERT по `sku`).

## Безопасность

* Только Telegram-ID из `ADMIN_IDS` пропускаются `AdminAccessMiddleware`;
  все попытки доступа со стороны посторонних логируются.
* SQL-запросы выполняются параметризовано (`?`-плейсхолдеры), что
  исключает SQL-инъекции.
* Любое действие администратора (смена статуса, блокировка, рассылка)
  фиксируется в журнале `admin_actions`.
* Все секреты (`BOT_TOKEN`, `SHOP_API_TOKEN`) хранятся в `.env` и
  исключены из git через `.gitignore`.

## Лицензия

Учебная разработка. Свободно используется в рамках ВКР.
