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
│   ├── database/db.py         # асинхронный слой SQLite
│   ├── keyboards/admin.py     # inline- и reply-клавиатуры
│   ├── middlewares/access.py  # контроль доступа администратора
│   ├── handlers/              # роутеры: common, orders, stats, users, broadcast, sync
│   ├── services/
│   │   ├── shop_api.py        # клиент API сайта (+ MockShopAPI)
│   │   ├── sync.py            # фоновая синхронизация заказов
│   │   └── analytics.py       # дашборды на Matplotlib
│   └── utils/                 # логирование, форматирование
├── scripts/
│   ├── seed_demo.py           # наполнение БД демо-данными
│   └── build_vkr.py           # сборка .docx ВКР по ГОСТ
├── docs/                      # сюда сохраняется готовая ВКР (.docx)
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

## Команды бота

| Команда                          | Назначение                                      |
|----------------------------------|--------------------------------------------------|
| `/start`                         | Главное меню                                    |
| `/help`                          | Справка                                         |
| `/orders [active|done|all|<статус>]` | Список заказов                              |
| `/order <id>` или `/order_<id>`  | Карточка заказа                                  |
| `/stats`                         | Сводная статистика                              |
| `/dashboard`                     | График заказов за 7 дней                        |
| `/sync`                          | Принудительная синхронизация с сайтом           |
| `/block <id> [причина]`          | Заблокировать пользователя                      |
| `/unblock <id>`                  | Разблокировать пользователя                     |
| `/blocked`                       | Показать чёрный список                          |
| `/send <id> <текст>`             | Личное сообщение клиенту                        |
| `/send_all <текст>`              | Массовая рассылка                               |
| `/log`                           | Журнал действий администратора                  |

## Интеграция с сайтом магазина

В файле `bot/main.py` источник заказов задаётся одной строкой:

```python
shop_api = MockShopAPI()           # для разработки/демонстрации
# shop_api = ShopAPIClient(
#     settings.shop_api_url,
#     settings.shop_api_token,
# )
```

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

Если у магазина нет API, в том же модуле есть метод
`ShopAPIClient.parse_html_orders`, который вытаскивает заказы из HTML
страницы админки магазина при помощи BeautifulSoup4. Чтобы использовать
его, нужно скачивать HTML через `aiohttp` и передавать в этот метод.

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
