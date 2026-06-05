# Telegram-бот администратора мебельного магазина

ВКР: «Разработка Telegram-бота для администратора типового мебельного
магазина» (Гафуров М. М., направление 09.03.04 «Программная инженерия»,
ВоГУ, 2026 г.).

Бот выполняет обязанности администратора сайта мебельного магазина:
принимает заказы с сайта (REST API или парсинг HTML без API), уведомляет
администратора, ведёт каталог товаров (CRUD), систему скидок, чёрный
список, формирует аналитические дашборды, экспортирует заказы в .docx
и журналирует все действия администратора.

## Технологический стек (строго по ТЗ)

| Назначение         | Технология                  |
|--------------------|------------------------------|
| Язык               | Python 3.11+                 |
| Telegram           | pyTelegramBotAPI (telebot)   |
| База данных        | SQLite (модуль `sqlite3`)    |
| Аналитика          | Matplotlib                   |
| Парсинг сайта      | Requests + BeautifulSoup4    |
| Экспорт документов | python-docx                  |
| Прокси             | PySocks (SOCKS5)             |
| Контроль версий    | Git                          |

## Структура проекта

```
.
├── bot/
│   ├── config.py              # настройки из .env (os.getenv)
│   ├── main.py                # точка входа (polling, SOCKS5)
│   ├── database.py            # синхронный слой SQLite
│   ├── keyboards.py           # ReplyKeyboardMarkup, InlineKeyboardMarkup
│   ├── utils.py               # admin_only декоратор, форматирование
│   ├── export_docx.py         # экспорт заказов в .docx (python-docx)
│   ├── handlers/
│   │   ├── common.py          # /start, /help
│   │   ├── orders.py          # заказы, статусы, чат с клиентом
│   │   ├── products.py        # CRUD каталога товаров
│   │   ├── discounts.py       # скидки (процент / фикс, на товар / глобально)
│   │   ├── stats.py           # /stats, /dashboard
│   │   ├── users.py           # чёрный список, журнал
│   │   ├── broadcast.py       # /send, /send_all
│   │   ├── sync.py            # /sync, /parse_site
│   │   └── export.py          # /export → .docx
│   └── services/
│       ├── shop_api.py        # ShopAPIClient | HTMLShopParser | MockShopAPI
│       ├── sync.py            # фоновая синхронизация (threading.Thread)
│       └── analytics.py       # дашборды на Matplotlib
├── scripts/
│   ├── seed_demo.py           # наполнение БД демо-данными
│   └── build_vkr.py           # сборка .docx ВКР по ГОСТ
├── docs/
│   └── Gafurov_VKR.docx
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
2. Узнайте свой Telegram ID у [@userinfobot](https://t.me/userinfobot).
3. Скопируйте `.env.example` в `.env` и заполните:

```ini
BOT_TOKEN=123456:AA...
ADMIN_IDS=111111111,222222222
DB_PATH=data/furniture_bot.sqlite3

# Источник данных сайта: mock | api | html
SHOP_SOURCE=mock

# === SOCKS5-прокси (на случай блокировок Telegram в РФ) ===
PROXY_HOST=
PROXY_PORT=1080
PROXY_USER=
PROXY_PASSWORD=
```

### Работа через SOCKS5-прокси

В условиях периодических ограничений работы Telegram на территории РФ
бот поддерживает подключение через SOCKS5-прокси. Достаточно указать
`PROXY_HOST` и `PROXY_PORT` в `.env` — бот автоматически направит весь
трафик к Telegram через прокси (используется `telebot.apihelper.proxy`).

## Запуск

```bash
python -m bot.main
```

## Демонстрационные данные

```bash
python scripts/seed_demo.py
```

Создаёт 60 заказов, 8 товаров и 2 скидки.

## Сборка пояснительной записки ВКР

```bash
python scripts/build_vkr.py
# → docs/Gafurov_VKR.docx
```

## Команды бота

### Заказы
| Команда | Назначение |
|---------|------------|
| `/orders [active|done|all|<статус>]` | Список заказов |
| `/order <id>` или `/order_<id>` | Карточка заказа |
| `/sync` | Принудительный приём заказов с сайта |
| `/parse_site` | Парсинг каталога сайта без API |
| `/export` | Экспорт заказов в .docx |

### Товары
| Команда | Назначение |
|---------|------------|
| `/products` | Каталог товаров с пагинацией |
| `/product <id|sku>` | Карточка товара |
| `/add_product` | Мастер добавления товара |
| `/del_product <id|sku>` | Удалить товар |
| `/price <id|sku> <цена>` | Изменить цену |

### Скидки
| Команда | Назначение |
|---------|------------|
| `/discounts` | Активные скидки |
| `/discount <sku|id|all> <percent|fixed> <значение> [дней]` | Создать скидку |

Примеры:
- `/discount all percent 10 7` — −10 % на весь каталог на 7 дней
- `/discount SOFA-001 fixed 5000` — минус 5000 ₽ на конкретный диван

### Прочее
| Команда | Назначение |
|---------|------------|
| `/stats`, `/dashboard` | Сводка и график продаж |
| `/block`, `/unblock`, `/blocked` | Чёрный список |
| `/send`, `/send_all` | Сообщения и рассылка клиентам |
| `/log` | Журнал действий администратора |
| `/start`, `/help` | Главное меню / справка |

## Безопасность

* Только Telegram ID из `ADMIN_IDS` пропускаются декоратором `admin_only`.
* Все SQL-запросы выполняются параметризовано (`?`-плейсхолдеры).
* Любое действие администратора сохраняется в таблице `admin_actions`.
* Все секреты (`BOT_TOKEN`, `SHOP_API_TOKEN`, `PROXY_PASSWORD`) хранятся
  в `.env`, исключённом из git через `.gitignore`.
* Соответствие требованиям ГОСТ Р 56939-2016 и 152-ФЗ «О персональных
  данных»: персональные данные клиентов минимизированы, доступ к ним
  возможен только с правами администратора, журналирование по аудит-трейлу.

## Лицензия

Учебная разработка. Свободно используется в рамках ВКР.
