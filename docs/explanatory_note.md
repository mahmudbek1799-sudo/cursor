# ПОЯСНИТЕЛЬНАЯ ЗАПИСКА

> **Указания к оформлению при копировании в Word.**
> Шрифт основного текста — Times New Roman 14 пт, междустрочный интервал 1,5, абзацный отступ 1,25 см, выравнивание по ширине.
> Шрифт листингов программ — Times New Roman 12 пт, междустрочный интервал 1,0, выравнивание по левому краю, отступ 0.
> Поля страницы: левое 2 см, правое 1,5 см, верхнее 2 см, нижнее 2 см.
> Нумерация страниц — арабскими цифрами, внизу по центру, начиная с введения.
> Заголовки — Times New Roman 14 пт, полужирный, по центру (для разделов) и по левому краю (для подразделов).

---

## ТИТУЛЬНЫЙ ЛИСТ

```
МИНИСТЕРСТВО НАУКИ И ВЫСШЕГО ОБРАЗОВАНИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ
федеральное государственное бюджетное образовательное учреждение
высшего образования
«___________________________ ГОСУДАРСТВЕННЫЙ УНИВЕРСИТЕТ»

Факультет ___________________________________________________
Кафедра ____________________________________________________
Направление подготовки 09.03.04 «Программная инженерия»
Профиль «Разработка программно-информационных систем»



                ВЫПУСКНАЯ КВАЛИФИКАЦИОННАЯ РАБОТА

       на тему: «Разработка Telegram-бота для автоматизации
                  администрирования группы»



Студент          ________________ /  Ф. И. О.            /
                       (подпись)

Руководитель ВКР ________________ /  Ф. И. О.            /
                       (подпись)

Нормоконтролёр   ________________ /  Ф. И. О.            /
                       (подпись)

Зав. кафедрой    ________________ /  Ф. И. О.            /
                       (подпись)


                          Город — 2026
```

---

## РЕФЕРАТ

Пояснительная записка содержит 1 файл программной части и 1 том пояснительной записки.
Ключевые слова: TELEGRAM-БОТ, AIOGRAM, SQLITE, МОДЕРАЦИЯ, АНТИСПАМ, АДМИНИСТРИРОВАНИЕ.

**Цель работы** — разработать программный модуль на языке Python, автоматизирующий обязанности администратора Telegram-группы (модерация сообщений, выдача предупреждений, ограничение участников, ведение журнала действий).
**Объект разработки** — серверное Telegram-приложение на базе библиотеки aiogram 3.x и СУБД SQLite, поддерживающее независимые настройки для нескольких групп.
**Результат** — работающий бот, реализующий все требования технического задания: антиспам (5/10 с), антимат, антиссылки, варны, команды `/mute`, `/unmute`, `/warn`, `/kick`, `/ban`, `/unban`, `/info`, `/stats`, `/setup`, `/export_logs`, журналирование в БД и файл `errors.log`.

---

## СОДЕРЖАНИЕ

| Раздел | Стр. |
| --- | --- |
| Введение | 4 |
| 1. Техническое задание | 5 |
| 2. Обзор аналогов | 7 |
| 3. Описание архитектуры бота | 9 |
| 3.1. Схема модулей | 9 |
| 3.2. Назначение файлов | 10 |
| 3.3. Описание базы данных | 11 |
| 4. Руководство администратора | 13 |
| 4.1. Установка | 13 |
| 4.2. Команды бота | 14 |
| 4.3. Сценарии работы | 15 |
| 5. Листинг программы | 17 |
| 6. Инструкция по развёртыванию | 35 |
| Заключение | 38 |
| Список использованных источников | 39 |

---

## ВВЕДЕНИЕ

Telegram входит в число наиболее популярных мессенджеров в Российской Федерации и странах СНГ; через его групповые чаты ежедневно проходят миллиарды сообщений. С ростом размера сообщества администраторы сталкиваются с типовыми, но трудоёмкими задачами: удаление спама и рекламы, контроль ненормативной лексики, борьба с фишинговыми ссылками, выдача предупреждений и блокировок, ведение журнала действий и формирование статистики. Выполнение этих задач вручную нерационально и приводит к ошибкам, поэтому актуальной становится **автоматизация модерации**.

**Актуальность работы** обусловлена потребностью владельцев Telegram-групп в едином инструменте, который выполнял бы рутинные обязанности модератора круглосуточно, прозрачно фиксировал каждое действие в журнале и позволял настраивать политику модерации индивидуально для каждой группы.

**Цель работы** — разработать Telegram-бота, автоматизирующего обязанности администратора группы в соответствии с требованиями технического задания.

**Задачи работы:**
1. Проанализировать существующие аналоги и сформировать требования к функциональности.
2. Спроектировать модульную архитектуру и схему базы данных.
3. Реализовать механизмы антиспама, антимата, контроля ссылок и систему варнов.
4. Реализовать команды модерации: `/mute`, `/unmute`, `/warn`, `/kick`, `/ban`, `/unban`, `/info`, `/stats`, `/setup`, `/export_logs`.
5. Обеспечить логирование нарушений и действий администраторов в базу данных и файл `errors.log`.
6. Подготовить инструкции по установке локально и на VPS.

**Объект исследования** — процессы администрирования Telegram-групп.
**Предмет исследования** — программные средства автоматизации модерации на базе Bot API Telegram.

---

## 1. ТЕХНИЧЕСКОЕ ЗАДАНИЕ

**1.1. Назначение разработки.** Telegram-бот для автоматизации обязанностей администратора группы. Бот должен заменять ручные операции модерации: фильтрацию сообщений, выдачу предупреждений, ограничение и блокировку участников, ведение журнала событий, формирование статистики.

**1.2. Функциональные требования.**

1. **Поддержка нескольких групп.** Все настройки фильтров и политик модерации хранятся в базе данных и применяются индивидуально для каждой группы.
2. **Антиспам.** Сообщения одного пользователя ограничиваются параметрами `antispam_msgs / antispam_seconds`. По умолчанию — 5 сообщений за 10 секунд. При превышении лимита сообщение удаляется, выдаётся варн.
3. **Антимат.** Список запрещённых слов задаётся администратором. Слово ищется регистронезависимо, по границам слова. При обнаружении сообщение удаляется, выдаётся варн.
4. **Антиссылки.** В сообщениях допускаются только ссылки на домены из белого списка `trusted_domains`. Все остальные ссылки удаляются, выдаётся варн.
5. **Система варнов.** Лимит — 3 варна (настраивается через `warn_limit`). При достижении лимита автоматически выдаётся мут на 24 часа (настраивается через `mute_hours`).
6. **Команды администратора.** `/mute`, `/unmute`, `/warn`, `/kick`, `/ban`, `/unban`, `/info`, `/stats`, `/setup`, `/export_logs`. Команды доступны только пользователям со статусом «administrator» или «creator» в данном чате.
7. **Цель команды.** Указывается reply’ем на сообщение, через `@username` либо числовой ID. Длительность — в формате `10m`, `2h`, `7d`.
8. **Журналирование.** Действия модерации, нарушения и изменения настроек сохраняются в таблицу `logs`, ошибки уровня WARNING/ERROR дублируются в файл `errors.log`. Доступна выгрузка журнала в формате CSV (`/export_logs`).
9. **Конфигурация.** Параметры подключения (токен бота, ID владельца, путь к БД, путь к лог-файлу) хранятся в файле `.env`.

**1.3. Технические требования.**

* Python 3.10 и выше.
* aiogram 3.x — асинхронный фреймворк для Bot API.
* SQLite — встроенная СУБД, доступ через aiosqlite.
* Структура проекта: каталоги `database/`, `handlers/`, `filters/`, `utils/`, `keyboards/`. Точка входа — `main.py`.
* Соответствие PEP 8.

**1.4. Требования к надёжности.** Бот должен корректно обрабатывать ошибки Bot API (`TelegramBadRequest`, `TelegramForbiddenError`), не прекращая работу, и журналировать инциденты.

**1.5. Требования к документации.** В состав поставки входят: исходный код, файл `requirements.txt`, файл-образец `.env.example`, файл `README.md` с пошаговой инструкцией запуска.

---

## 2. ОБЗОР АНАЛОГОВ

Для определения требуемого функционала выполнен анализ двух наиболее распространённых решений.

### 2.1. Group Manager Bot (@GroupManager_bot)

**Назначение.** Универсальный коммерческий бот для модерации Telegram-групп.

**Преимущества:**
* широкий набор команд (warn, mute, ban, captcha, antiflood, antilink);
* поддержка большого числа групп на одной инсталляции;
* встроенная система notes (заметок) и rules;
* мультиязычный интерфейс.

**Недостатки:**
* проприетарный — исходный код закрыт, локальная установка невозможна;
* журнал хранится только на стороне провайдера, выгрузка ограничена;
* настройки белых доменов и списка запрещённых слов — платные расширения в части тарифов;
* при отсутствии связи с сервером владельца группа полностью теряет модерацию.

### 2.2. Rose Bot (@MissRose_bot)

**Назначение.** Один из самых популярных opensource-ориентированных модераторов Telegram, написан на Python.

**Преимущества:**
* модульная архитектура, активное сообщество;
* развитая система фильтров и расширений;
* поддержка ChatPermissions, ограничений по медиа;
* конфигурируемые приветствия и правила.

**Недостатки:**
* написан на устаревшей синхронной библиотеке `python-telegram-bot` 12.x с миграцией на 20.x, что затрудняет сопровождение;
* настройки хранятся в общей реляционной БД, не предусмотрены гибкие переключатели модулей на уровне группы;
* установка тяжёлая (требует Redis, PostgreSQL);
* для разработки требуется глубокое знание Dispatcher-цепочек.

### 2.3. Сводный вывод

Существующие аналоги либо проприетарны, либо чрезмерно тяжелы для развертывания на VPS малого размера. **Разрабатываемое в настоящей ВКР решение** заполняет эту нишу: лёгкая зависимость только от aiogram 3.x и SQLite, поддержка нескольких групп с индивидуальными настройками, простая выгрузка журнала в CSV, открытая модульная архитектура.

---

## 3. ОПИСАНИЕ АРХИТЕКТУРЫ БОТА

### 3.1. Схема модулей

```
                       ┌───────────────────────┐
                       │       main.py         │
                       │  (точка входа, run)   │
                       └──────────┬────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
       ┌──────▼─────┐      ┌──────▼─────┐      ┌──────▼─────┐
       │  config.py │      │  database/ │      │  utils/    │
       │   .env     │      │   db.py    │      │ logger.py  │
       │            │      │  SQLite    │      │decorators  │
       └────────────┘      └─────▲──────┘      └──────▲─────┘
                                 │                    │
                       ┌─────────┴────────────────────┴────────┐
                       │            handlers/                  │
                       │  users.py   admins.py   setup.py      │
                       └────────────────┬──────────────────────┘
                                        │
                              ┌─────────▼─────────┐
                              │     filters/      │
                              │ antispam  links   │
                              │      badwords     │
                              └───────────────────┘
                                        │
                              ┌─────────▼─────────┐
                              │    keyboards/     │
                              │ inline-меню /setup│
                              └───────────────────┘
```

### 3.2. Назначение файлов

**Таблица 1 — Состав исходных файлов**

| Файл | Назначение |
| --- | --- |
| `main.py` | Точка входа: инициализация Bot, Dispatcher, подключение БД, запуск polling. |
| `config.py` | Загрузка переменных окружения из `.env`, значения по умолчанию. |
| `requirements.txt` | Список Python-зависимостей с фиксацией версий. |
| `.env.example` | Образец конфигурации (без секретов). |
| `database/db.py` | Описание схемы SQLite и методов доступа (асинхронные корутины). |
| `handlers/users.py` | Автоматическая модерация: реакция фильтров, приветствие. |
| `handlers/admins.py` | Команды `/warn`, `/mute`, `/unmute`, `/ban`, `/unban`, `/kick`, `/info`, `/stats`, `/export_logs`, `/help`. |
| `handlers/setup.py` | Команда `/setup` и inline-меню настроек группы (FSM). |
| `filters/antispam.py` | Фильтр частоты сообщений (скользящее окно). |
| `filters/links.py` | Фильтр ссылок по белому списку доменов. |
| `filters/badwords.py` | Фильтр запрещённых слов (регулярные выражения). |
| `utils/logger.py` | Настройка stdout + ротация `errors.log`. |
| `utils/decorators.py` | Декораторы `group_only`, `admin_only`. |
| `keyboards/__init__.py` | Inline-клавиатуры меню `/setup`. |
| `README.md` | Краткая инструкция запуска. |

### 3.3. Описание базы данных

База данных — SQLite, файл `bot.db`. Все запросы выполняются асинхронно через `aiosqlite`, при первом запуске схема создаётся автоматически.

**Таблица 2 — Структура таблиц БД**

| Таблица | Поля | Назначение |
| --- | --- | --- |
| `users` | `user_id PK`, `username`, `full_name`, `first_seen`, `last_seen` | Кэш профилей участников групп. |
| `group_settings` | `chat_id PK`, `title`, `antispam_msgs`, `antispam_seconds`, `warn_limit`, `mute_hours`, `bad_words(json)`, `trusted_domains(json)`, `antispam_on`, `antilinks_on`, `antibadwords_on`, `welcome_text` | Индивидуальные настройки каждой группы. |
| `warns` | `id PK`, `chat_id`, `user_id`, `admin_id`, `reason`, `created` | Журнал выданных предупреждений. |
| `bans` | `id PK`, `chat_id`, `user_id`, `admin_id`, `kind (ban\|mute)`, `reason`, `until_ts`, `active`, `created` | История ограничений и блокировок. |
| `logs` | `id PK`, `chat_id`, `user_id`, `admin_id`, `action`, `details`, `created` | Универсальный журнал событий (нарушения, действия админов, изменения настроек). |

**ER-диаграмма (текстовая):**

```
users(user_id) ──< warns(user_id, chat_id) >── group_settings(chat_id)
                ──< bans(user_id, chat_id) ──┘
                ──< logs(user_id, chat_id) ──┘
```

Внешние ключи в SQLite не объявляются жёстко (поля `chat_id`, `user_id` индексируются через `CREATE INDEX`), это упрощает миграцию и не требует ON DELETE CASCADE.

---

## 4. РУКОВОДСТВО АДМИНИСТРАТОРА

### 4.1. Установка

1. Установить Python 3.10+ и Git.
2. Получить токен бота у [@BotFather](https://t.me/BotFather).
3. Клонировать репозиторий и перейти в каталог `bot/`.
4. Создать виртуальное окружение и установить зависимости:
   `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
5. Скопировать `.env.example` → `.env`, указать `BOT_TOKEN` и `OWNER_ID`.
6. Запустить бота: `python main.py`.
7. Добавить бота в Telegram-группу, выдать права администратора (минимум: удаление сообщений, ограничение участников).
8. В чате группы выполнить `/setup`.

[СКРИН 1 — приветствие /start]

### 4.2. Команды бота

**Таблица 3 — Команды бота**

| Команда | Описание | Кто может вызывать |
| --- | --- | --- |
| `/start` | Приветственное сообщение. | Любой пользователь. |
| `/help` | Краткая справка по командам. | Любой пользователь. |
| `/setup` | Открывает inline-меню настроек группы. | Администраторы группы. |
| `/warn @u причина` | Выдать варн. При достижении лимита — автомут. | Администраторы группы. |
| `/mute @u 2h причина` | Запретить писать (по умолчанию — бессрочно). | Администраторы группы. |
| `/unmute @u` | Снять мут. | Администраторы группы. |
| `/ban @u 7d причина` | Забанить пользователя. | Администраторы группы. |
| `/unban @u` | Разбанить. | Администраторы группы. |
| `/kick @u` | Исключить из группы. | Администраторы группы. |
| `/info @u` | Карточка пользователя: ID, варны, активные санкции. | Администраторы группы. |
| `/stats` | Сводная статистика по группе. | Администраторы группы. |
| `/export_logs` | Экспорт журнала в CSV. | Администраторы группы. |

[СКРИН 2 — меню /setup]
[СКРИН 3 — пример карточки /info]
[СКРИН 4 — выгрузка /export_logs]

### 4.3. Сценарии работы

**Сценарий «Спам».** Участник за 10 секунд отправил 6 сообщений. Бот удаляет шестое сообщение, добавляет запись в таблицу `warns`, отправляет в чат предупреждение «Варн 1/3». При накоплении 3 варнов выдаётся `restrict_chat_member` на 24 часа, журнал пополняется записью `auto_mute`.

[СКРИН 5 — срабатывание антиспама]

**Сценарий «Запрещённое слово».** Участник отправил сообщение со словом из списка `bad_words`. Бот удаляет сообщение и фиксирует нарушение.

[СКРИН 6 — срабатывание антимата]

**Сценарий «Ссылка».** Участник отправил ссылку на сторонний домен. Бот извлекает hostname, сравнивает с `trusted_domains`. Если совпадения нет — сообщение удаляется, выдаётся варн.

[СКРИН 7 — срабатывание антиссылок]

---

## 5. ЛИСТИНГ ПРОГРАММЫ

> Все листинги приводятся шрифтом Times New Roman 12 пт. В Word каждый блок кода рекомендуется обернуть в стиль «Code» с обрамлением рамкой.

### Листинг 1 — `main.py`

```python
"""Точка входа в Telegram-бота администрирования группы."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings, validate_settings
from database import db
from handlers import get_root_router
from utils import setup_logging

log = logging.getLogger("bot")


async def main() -> None:
    validate_settings()
    setup_logging(settings.log_file)

    await db.connect()
    log.info("База данных подключена: %s", settings.db_path)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(get_root_router())

    me = await bot.get_me()
    log.info("Бот @%s готов к работе", me.username)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Остановлено пользователем.")
```

**Анализ.** Модуль выполняет последовательную инициализацию: валидирует переменные окружения, настраивает логирование, открывает SQLite-соединение и запускает long-polling. Использование `DefaultBotProperties(parse_mode=HTML)` снимает необходимость указывать `parse_mode` в каждом ответе. Завершение работы корректно закрывает сессию и БД, что предотвращает утечки файловых дескрипторов.

---

### Листинг 2 — `config.py`

```python
"""Глобальная конфигурация проекта."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv

BASE_DIR: Path = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _get_int(name: str, default: int = 0) -> int:
    raw = os.getenv(name, str(default))
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


@dataclass(slots=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    owner_id: int = _get_int("OWNER_ID", 0)
    db_path: Path = BASE_DIR / os.getenv("DB_PATH", "bot.db")
    log_file: Path = BASE_DIR / os.getenv("LOG_FILE", "errors.log")

    default_antispam_messages: int = 5
    default_antispam_seconds: int = 10
    default_warn_limit: int = 3
    default_mute_hours: int = 24
    default_bad_words: List[str] = field(
        default_factory=lambda: ["дурак", "идиот", "придурок", "хрен", "сволочь"]
    )
    default_trusted_domains: List[str] = field(
        default_factory=lambda: ["t.me", "telegram.me", "telegram.org"]
    )


settings = Settings()


def validate_settings() -> None:
    if not settings.bot_token or settings.bot_token.startswith("123456789:"):
        raise RuntimeError("BOT_TOKEN не задан. См. .env.example.")
```

**Анализ.** Конфигурация выделена в отдельный `dataclass(slots=True)` — это экономит память и одновременно явно фиксирует список настраиваемых параметров. Значения по умолчанию для антиспама и списков соответствуют требованиям ТЗ (5/10 секунд, 3 варна → 24 ч).

---

### Листинг 3 — `database/db.py`

```python
"""Слой доступа к данным SQLite (aiosqlite)."""
from __future__ import annotations

import json, time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

import aiosqlite

from config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
    first_seen INTEGER NOT NULL, last_seen INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS group_settings (
    chat_id INTEGER PRIMARY KEY, title TEXT,
    antispam_msgs INTEGER NOT NULL DEFAULT 5,
    antispam_seconds INTEGER NOT NULL DEFAULT 10,
    warn_limit INTEGER NOT NULL DEFAULT 3,
    mute_hours INTEGER NOT NULL DEFAULT 24,
    bad_words TEXT NOT NULL DEFAULT '[]',
    trusted_domains TEXT NOT NULL DEFAULT '[]',
    antispam_on INTEGER NOT NULL DEFAULT 1,
    antilinks_on INTEGER NOT NULL DEFAULT 1,
    antibadwords_on INTEGER NOT NULL DEFAULT 1,
    welcome_text TEXT NOT NULL DEFAULT '');

CREATE TABLE IF NOT EXISTS warns (
    id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL, admin_id INTEGER NOT NULL,
    reason TEXT, created INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS bans (
    id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL, admin_id INTEGER NOT NULL,
    kind TEXT NOT NULL, reason TEXT, until_ts INTEGER,
    active INTEGER NOT NULL DEFAULT 1, created INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, user_id INTEGER,
    admin_id INTEGER, action TEXT NOT NULL, details TEXT,
    created INTEGER NOT NULL);
"""


@dataclass(slots=True)
class GroupSettings:
    chat_id: int; title: str
    antispam_msgs: int; antispam_seconds: int
    warn_limit: int; mute_hours: int
    bad_words: list[str]; trusted_domains: list[str]
    antispam_on: bool; antilinks_on: bool; antibadwords_on: bool
    welcome_text: str


class Database:
    def __init__(self, path: Path | None = None) -> None:
        self._path: Path = path or settings.db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        if self._conn is not None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close(); self._conn = None

    # ... (полный код методов upsert_user / get_settings / update_setting /
    #      add_warn / count_warns / clear_warns / add_ban / deactivate_bans /
    #      log / fetch_logs / stats — см. файл bot/database/db.py в репозитории)


db = Database()
```

**Анализ.** Схема описана единым SQL-блоком и создаётся идемпотентно (`IF NOT EXISTS`). Поля-списки (`bad_words`, `trusted_domains`) хранятся в виде JSON-строк — это компромисс между нормализацией и простотой: списки короткие, отдельная нормализованная таблица переусложнила бы код. Соединение единственное на процесс — это допустимо для SQLite, который сам сериализует записи.

---

### Листинг 4 — `database/__init__.py`

```python
"""Пакет работы с базой данных SQLite."""
from .db import Database, db
__all__ = ["Database", "db"]
```

**Анализ.** Реэкспорт упрощает импорт в остальных модулях: `from database import db`.

---

### Листинг 5 — `filters/antispam.py`

```python
"""Антиспам-фильтр (скользящее окно)."""
from __future__ import annotations
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, Tuple

from aiogram.filters import BaseFilter
from aiogram.types import Message
from database import db


class AntiSpamFilter(BaseFilter):
    _buckets: Dict[Tuple[int, int], Deque[float]] = defaultdict(deque)

    async def __call__(self, message: Message) -> bool | Dict[str, Any]:
        if message.from_user is None or message.from_user.is_bot:
            return False
        cfg = await db.get_settings(message.chat.id, message.chat.title or "")
        if not cfg.antispam_on:
            return False
        key = (message.chat.id, message.from_user.id)
        bucket = self._buckets[key]
        now = time.monotonic()
        while bucket and now - bucket[0] > cfg.antispam_seconds:
            bucket.popleft()
        bucket.append(now)
        if len(bucket) > cfg.antispam_msgs:
            bucket.clear()
            return {"reason": f"флуд: > {cfg.antispam_msgs} сообщ./"
                              f"{cfg.antispam_seconds} c"}
        return False
```

**Анализ.** Хранение «корзин» (deque) в памяти процесса исключает обращение к БД при каждом сообщении и обеспечивает алгоритмическую сложность O(1) на проверку. Когда лимит превышен — корзина очищается, чтобы пользователь не «жил» в состоянии непрерывного нарушения.

---

### Листинг 6 — `filters/links.py`

```python
"""Фильтр ссылок по белому списку доменов."""
from __future__ import annotations
import re
from typing import Any, Dict
from urllib.parse import urlparse

from aiogram.filters import BaseFilter
from aiogram.types import Message
from database import db

URL_RE = re.compile(
    r"(?:(?:https?|tg)://[^\s]+|(?:www\.|t\.me/|@)[^\s]+)",
    re.IGNORECASE,
)


def _extract_host(token: str) -> str:
    token = token.strip().strip(".,;!?)\"'")
    if token.startswith("@"):
        return "t.me"
    if "://" not in token:
        token = "http://" + token
    try:
        host = urlparse(token).hostname or ""
    except ValueError:
        return ""
    return host.lower().removeprefix("www.")


class LinksFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool | Dict[str, Any]:
        if message.from_user is None or message.from_user.is_bot:
            return False
        text = (message.text or message.caption or "").strip()
        if not text:
            return False
        cfg = await db.get_settings(message.chat.id, message.chat.title or "")
        if not cfg.antilinks_on:
            return False
        trusted = {d.lower().removeprefix("www.") for d in cfg.trusted_domains}
        for token in URL_RE.findall(text):
            host = _extract_host(token)
            if not host:
                continue
            if not any(host == t or host.endswith("." + t) for t in trusted):
                return {"reason": f"запрещённая ссылка: {host}"}
        return False
```

**Анализ.** Регулярное выражение охватывает три случая ссылок: HTTP/HTTPS, tg-deeplink и @-упоминание (которое раскрывается в `t.me`). Сопоставление с доверенными доменами поддерживает поддомены (`youtu.be` для домена `youtube.com`), что снижает число ложных срабатываний.

---

### Листинг 7 — `filters/badwords.py`

```python
"""Антимат-фильтр."""
from __future__ import annotations
import re
from functools import lru_cache
from typing import Any, Dict, Tuple

from aiogram.filters import BaseFilter
from aiogram.types import Message
from database import db


@lru_cache(maxsize=64)
def _compile(words_key: Tuple[str, ...]) -> re.Pattern[str] | None:
    if not words_key:
        return None
    escaped = "|".join(re.escape(w) for w in words_key if w)
    if not escaped:
        return None
    return re.compile(rf"(?<!\w)(?:{escaped})(?!\w)",
                      re.IGNORECASE | re.UNICODE)


class BadWordsFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool | Dict[str, Any]:
        if message.from_user is None or message.from_user.is_bot:
            return False
        text = (message.text or message.caption or "")
        if not text:
            return False
        cfg = await db.get_settings(message.chat.id, message.chat.title or "")
        if not cfg.antibadwords_on:
            return False
        pattern = _compile(tuple(sorted(cfg.bad_words)))
        if pattern is None:
            return False
        m = pattern.search(text)
        if m:
            return {"reason": f"нецензурная лексика: «{m.group(0)}»"}
        return False
```

**Анализ.** Регулярное выражение строится один раз и кэшируется через `lru_cache`. Шаблон `(?<!\w)…(?!\w)` исключает ложные срабатывания на подстроках («дурак» сработает, но «дуракан» — нет).

---

### Листинг 8 — `filters/__init__.py`

```python
from .antispam import AntiSpamFilter
from .badwords import BadWordsFilter
from .links import LinksFilter

__all__ = ["AntiSpamFilter", "BadWordsFilter", "LinksFilter"]
```

**Анализ.** Реэкспорт публичных классов фильтров обеспечивает единый импорт `from filters import …` в хэндлерах.

---

### Листинг 9 — `utils/logger.py`

```python
"""Единая точка настройки логирования."""
from __future__ import annotations
import logging, sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_INITIALIZED = False


def setup_logging(log_file: Path) -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    log_file.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger(); root.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")
    stream = logging.StreamHandler(sys.stdout)
    stream.setLevel(logging.INFO); stream.setFormatter(fmt)
    file_h = RotatingFileHandler(log_file, maxBytes=2_000_000,
                                 backupCount=5, encoding="utf-8")
    file_h.setLevel(logging.WARNING); file_h.setFormatter(fmt)
    root.handlers.clear()
    root.addHandler(stream); root.addHandler(file_h)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    _INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
```

**Анализ.** Применена ротация (5 файлов × 2 МБ) — это предохраняет диск VPS от переполнения. Уровень INFO выводится только в stdout, WARNING/ERROR дополнительно дублируются в файл — соответствует требованию ТЗ.

---

### Листинг 10 — `utils/decorators.py`

```python
"""Декораторы доступа."""
from __future__ import annotations
import functools
from typing import Any, Awaitable, Callable

from aiogram import Bot
from aiogram.enums import ChatType
from aiogram.types import Message
from config import settings


def group_only(func):
    @functools.wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        if message.chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP}:
            await message.reply("Команда работает только в группе.")
            return None
        return await func(message, *args, **kwargs)
    return wrapper


def admin_only(func):
    @functools.wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        bot: Bot = kwargs.get("bot") or message.bot
        if message.from_user is None:
            return None
        if message.from_user.id == settings.owner_id:
            return await func(message, *args, **kwargs)
        try:
            member = await bot.get_chat_member(message.chat.id,
                                               message.from_user.id)
        except Exception:
            await message.reply("Не удалось проверить ваши права.")
            return None
        if member.status not in {"administrator", "creator"}:
            await message.reply("Команда доступна только администраторам.")
            return None
        return await func(message, *args, **kwargs)
    return wrapper
```

**Анализ.** Декораторы делают код хэндлеров декларативным: проверка прав отделена от бизнес-логики команды. `OWNER_ID` имеет приоритет над членством в чате — это удобно для отладки.

---

### Листинг 11 — `utils/__init__.py`

```python
from .logger import get_logger, setup_logging
from .decorators import admin_only, group_only

__all__ = ["get_logger", "setup_logging", "admin_only", "group_only"]
```

**Анализ.** Сводный импорт упрощает использование утилит.

---

### Листинг 12 — `keyboards/__init__.py`

```python
"""Inline-клавиатуры бота."""
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup,
)


def setup_menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Антиспам", callback_data="setup:antispam"),
         InlineKeyboardButton(text="Антиссылки", callback_data="setup:antilinks")],
        [InlineKeyboardButton(text="Антимат", callback_data="setup:antibadwords"),
         InlineKeyboardButton(text="Лимит варнов", callback_data="setup:warns")],
        [InlineKeyboardButton(text="Список мата", callback_data="setup:words"),
         InlineKeyboardButton(text="Доверенные домены",
                              callback_data="setup:domains")],
        [InlineKeyboardButton(text="Закрыть", callback_data="setup:close")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def toggle_kb(field: str, value: bool) -> InlineKeyboardMarkup:
    label_on = ("✅ " if value else "") + "Включить"
    label_off = ("✅ " if not value else "") + "Выключить"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label_on, callback_data=f"toggle:{field}:1"),
         InlineKeyboardButton(text=label_off, callback_data=f"toggle:{field}:0")],
        [InlineKeyboardButton(text="« Назад", callback_data="setup:back")],
    ])


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Назад", callback_data="setup:back")]
    ])
```

**Анализ.** Все элементы меню вынесены в отдельный модуль — это позволяет переиспользовать клавиатуры и не дублировать их в хэндлерах.

---

### Листинг 13 — `handlers/__init__.py`

```python
from aiogram import Router
from . import admins, setup, users


def get_root_router() -> Router:
    root = Router(name="root")
    root.include_router(setup.router)
    root.include_router(admins.router)
    root.include_router(users.router)
    return root


__all__ = ["get_root_router"]
```

**Анализ.** Корневой роутер собирает три подмаршрутизатора. Порядок включения важен: `setup` и `admins` стоят перед `users`, иначе catch-all из `users.py` (кэширование пользователей) перехватит сообщение раньше команд.

---

### Листинг 14 — `handlers/users.py`

```python
"""Автоматическая модерация + кэш пользователей."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.types import ChatPermissions, Message

from database import db
from filters import AntiSpamFilter, BadWordsFilter, LinksFilter
from utils import get_logger

router = Router(name="users")
log = get_logger(__name__)
GROUP_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}


async def _auto_punish(message: Message, bot: Bot, reason: str) -> None:
    if message.from_user is None:
        return
    chat_id, user_id = message.chat.id, message.from_user.id
    try:
        await message.delete()
    except Exception as exc:
        log.warning("Не удалось удалить сообщение %s: %s",
                    message.message_id, exc)
    cfg = await db.get_settings(chat_id, message.chat.title or "")
    warns = await db.add_warn(chat_id, user_id, bot.id, reason)
    await db.log("violation", chat_id=chat_id, user_id=user_id,
                 admin_id=bot.id, details=reason)
    full = message.from_user.full_name
    if warns >= cfg.warn_limit:
        until = datetime.now(timezone.utc) + timedelta(hours=cfg.mute_hours)
        try:
            await bot.restrict_chat_member(
                chat_id, user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until)
            await db.add_ban(chat_id, user_id, bot.id, "mute",
                             "auto: лимит варнов", int(until.timestamp()))
            await db.clear_warns(chat_id, user_id)
            await db.log("auto_mute", chat_id=chat_id, user_id=user_id,
                         admin_id=bot.id, details=f"{cfg.mute_hours}h")
            await message.answer(
                f"⛔ {full}: достигнут лимит варнов ({cfg.warn_limit}). "
                f"Мут на {cfg.mute_hours} ч.")
        except Exception as exc:
            log.error("restrict_chat_member: %s", exc)
    else:
        await message.answer(
            f"⚠️ {full}, нарушение: {reason}. Варн {warns}/{cfg.warn_limit}.")


@router.message(F.chat.type.in_(GROUP_TYPES), AntiSpamFilter())
async def on_spam(message: Message, bot: Bot, reason: str) -> None:
    await _auto_punish(message, bot, reason)


@router.message(F.chat.type.in_(GROUP_TYPES), LinksFilter())
async def on_link(message: Message, bot: Bot, reason: str) -> None:
    await _auto_punish(message, bot, reason)


@router.message(F.chat.type.in_(GROUP_TYPES), BadWordsFilter())
async def on_badword(message: Message, bot: Bot, reason: str) -> None:
    await _auto_punish(message, bot, reason)


@router.message(F.new_chat_members)
async def on_join(message: Message) -> None:
    cfg = await db.get_settings(message.chat.id, message.chat.title or "")
    for m in message.new_chat_members or []:
        await db.upsert_user(m.id, m.username, m.full_name)
        await db.log("join", chat_id=message.chat.id, user_id=m.id,
                     details=m.full_name)
        if cfg.welcome_text:
            await message.answer(cfg.welcome_text.replace("{name}", m.full_name))


@router.message(F.left_chat_member)
async def on_leave(message: Message) -> None:
    m = message.left_chat_member
    if m is None:
        return
    await db.log("leave", chat_id=message.chat.id, user_id=m.id,
                 details=m.full_name)


@router.message(F.chat.type.in_(GROUP_TYPES))
async def cache_user(message: Message) -> None:
    if message.from_user and not message.from_user.is_bot:
        await db.upsert_user(message.from_user.id,
                             message.from_user.username,
                             message.from_user.full_name)
```

**Анализ.** Все три фильтра приводят к одной и той же ветке `_auto_punish` — поэтому код наказания не дублируется. Передача `reason` в хэндлеры реализована через возврат словаря из фильтра — стандартный механизм aiogram для проксирования данных.

---

### Листинг 15 — `handlers/admins.py` (фрагмент)

```python
"""Административные команды: /warn /mute /unmute /ban /unban /kick /info
/stats /export_logs."""
from __future__ import annotations
import csv, io, re
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, ChatPermissions, Message

from database import db
from utils import admin_only, get_logger, group_only

router = Router(name="admins")
log = get_logger(__name__)

DURATION_RE = re.compile(r"^(\d+)\s*([smhd])$", re.IGNORECASE)
UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_duration(token: str) -> int | None:
    if not token:
        return None
    m = DURATION_RE.match(token)
    if not m:
        return None
    return int(m.group(1)) * UNIT_SECONDS[m.group(2).lower()]


async def resolve_target(message, args, bot):
    """Reply | @username | numeric ID → (uid, name, tail)."""
    if message.reply_to_message and message.reply_to_message.from_user:
        u = message.reply_to_message.from_user
        return u.id, u.full_name, (args or "").strip()
    if not args:
        return None, "", ""
    tokens = args.split(maxsplit=1)
    head, rest = tokens[0], tokens[1] if len(tokens) > 1 else ""
    if head.startswith("@"):
        cur = await db.conn.execute(
            "SELECT user_id, full_name FROM users WHERE username = ?",
            (head.lstrip("@"),))
        row = await cur.fetchone()
        if row:
            return int(row["user_id"]), row["full_name"], rest
        return None, head, rest
    if head.lstrip("-").isdigit():
        uid = int(head)
        cached = await db.get_user(uid)
        return uid, (cached["full_name"] if cached else str(uid)), rest
    return None, head, rest


@router.message(Command("warn"))
@group_only
@admin_only
async def cmd_warn(message: Message, command: CommandObject, bot: Bot):
    uid, name, reason = await resolve_target(message, command.args, bot)
    if uid is None:
        await message.reply("Использование: /warn @user причина (или reply).")
        return
    cfg = await db.get_settings(message.chat.id, message.chat.title or "")
    warns = await db.add_warn(message.chat.id, uid,
                              message.from_user.id, reason or "—")
    await db.log("admin_warn", chat_id=message.chat.id, user_id=uid,
                 admin_id=message.from_user.id, details=reason or "—")
    if warns >= cfg.warn_limit:
        until = datetime.now(timezone.utc) + timedelta(hours=cfg.mute_hours)
        await bot.restrict_chat_member(
            message.chat.id, uid,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until)
        await db.add_ban(message.chat.id, uid, message.from_user.id,
                         "mute", "лимит варнов", int(until.timestamp()))
        await db.clear_warns(message.chat.id, uid)
        await message.reply(
            f"⛔ {name}: лимит варнов. Мут на {cfg.mute_hours} ч.")
    else:
        await message.reply(
            f"⚠️ {name}: варн {warns}/{cfg.warn_limit}. "
            f"Причина: {reason or '—'}")


# Полный текст /mute /unmute /ban /unban /kick /info /stats /export_logs
# приведён в файле bot/handlers/admins.py репозитория.
```

**Анализ.** Логика всех команд приведена к единой схеме: «разобрать цель → проверить права → выполнить действие → сохранить в БД и в журнал → ответить пользователю». Универсальный парсер `resolve_target` устраняет дублирование. `parse_duration` поддерживает интуитивный формат `10m / 2h / 7d`.

---

### Листинг 16 — `handlers/setup.py` (фрагмент)

```python
"""Команда /setup и обработка inline-меню (FSM)."""
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from database import db
from keyboards import back_kb, setup_menu, toggle_kb
from utils import admin_only, group_only

router = Router(name="setup")


class SetupStates(StatesGroup):
    waiting_words = State()
    waiting_domains = State()
    waiting_warns = State()


@router.message(Command("setup"))
@group_only
@admin_only
async def cmd_setup(message: Message, bot: Bot):
    cfg = await db.get_settings(message.chat.id, message.chat.title or "")
    await message.reply(_status_text(cfg), reply_markup=setup_menu())

# Полностью обработчики callback_query и FSM-состояний см. в bot/handlers/setup.py.
```

**Анализ.** Состояния `waiting_words / waiting_domains / waiting_warns` реализуют пошаговый ввод значений — стандартный для aiogram паттерн Finite State Machine. После сохранения значения состояние очищается, и пользователю снова показывается главное меню.

---

## 6. ИНСТРУКЦИЯ ПО РАЗВЁРТЫВАНИЮ

### 6.1. Локальный запуск

```bash
git clone <URL_репозитория>
cd bot
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
nano .env                            # BOT_TOKEN=..., OWNER_ID=...
python main.py
```

После запуска бот появится «в сети». Добавление в группу и выдача прав администратора описаны в §4.1.

### 6.2. Развёртывание на VPS (Ubuntu 22.04, systemd)

1. Установить системные пакеты:
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-venv python3-pip git
   ```
2. Создать отдельного пользователя:
   ```bash
   sudo useradd -m -s /bin/bash tgbot
   sudo su - tgbot
   ```
3. Клонировать репозиторий и установить зависимости (см. §6.1).
4. Создать unit-файл `sudo nano /etc/systemd/system/tgbot.service`:
   ```ini
   [Unit]
   Description=Telegram group admin bot
   After=network-online.target
   
   [Service]
   Type=simple
   User=tgbot
   WorkingDirectory=/home/tgbot/bot
   Environment=PYTHONUNBUFFERED=1
   ExecStart=/home/tgbot/bot/.venv/bin/python main.py
   Restart=on-failure
   RestartSec=5
   
   [Install]
   WantedBy=multi-user.target
   ```
5. Включить и запустить:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now tgbot.service
   sudo journalctl -u tgbot -f
   ```

### 6.3. Резервное копирование

* База `bot.db` — единственный файл со всеми настройками и журналом, копируется обычным `cp` или `rsync` (предварительно желательно выполнить `sqlite3 bot.db ".backup '/tmp/bot.db.bak'"`).
* Журнал `errors.log` ротируется автоматически (5 файлов × 2 МБ).

---

## ЗАКЛЮЧЕНИЕ

В ходе выполнения выпускной квалификационной работы поставленная цель достигнута: разработан Telegram-бот, автоматизирующий обязанности администратора группы.

**В работе выполнено:**
1. Проанализированы существующие аналоги (GroupManager Bot, Rose Bot), выделены требования к собственной разработке.
2. Спроектирована модульная архитектура: разделение на пакеты `database`, `handlers`, `filters`, `utils`, `keyboards`, единая точка входа `main.py`.
3. Разработана схема SQLite из пяти таблиц (`users`, `group_settings`, `warns`, `bans`, `logs`), реализованы асинхронные методы доступа на базе `aiosqlite`.
4. Реализованы три модуля автоматической модерации (антиспам, антимат, антиссылки) в виде пользовательских фильтров aiogram 3.x.
5. Реализованы все команды модерации, требуемые в ТЗ, с поддержкой указания цели через reply / `@username` / ID и формата длительности `10m / 2h / 7d`.
6. Реализовано меню настроек `/setup` на inline-клавиатурах с использованием FSM aiogram.
7. Реализовано двойное журналирование: в таблицу `logs` для аналитики и в ротируемый файл `errors.log` для технического сопровождения.
8. Подготовлены инструкции по локальной установке и развертыванию на VPS под systemd.

**Приобретённые и развитые навыки:**
* Асинхронное программирование на Python (`asyncio`, корутины).
* Работа с современным фреймворком aiogram 3.x: Router, фильтры, FSM, inline-клавиатуры.
* Проектирование схемы реляционной БД и использование SQLite через aiosqlite.
* Применение принципов модульной декомпозиции, PEP 8, разделения ответственности.
* Подготовка прикладного ПО к развертыванию (виртуальные окружения, systemd, ротация логов).
* Оформление технической документации по требованиям ГОСТ 7.32-2017 и ГОСТ 2.105-95.

**Перспективы развития:**
* Перенос FSM-хранилища с MemoryStorage на Redis для горизонтального масштабирования.
* Добавление веб-панели администратора (FastAPI) для удалённого доступа к настройкам и журналу.
* Подключение captcha-проверки новых участников и проверки фишинговых URL по внешним API.

---

## СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ

1. ГОСТ 7.32-2017. Система стандартов по информации, библиотечному и издательскому делу. Отчёт о научно-исследовательской работе. Структура и правила оформления. — М.: Стандартинформ, 2017. — 27 с.
2. ГОСТ 2.105-95. Единая система конструкторской документации. Общие требования к текстовым документам. — М.: Стандартинформ, 1996. — 38 с.
3. PEP 8 — Style Guide for Python Code [Электронный ресурс]. — URL: https://peps.python.org/pep-0008/ (дата обращения: 10.05.2026).
4. Aiogram 3.x. Official documentation [Электронный ресурс]. — URL: https://docs.aiogram.dev/ (дата обращения: 10.05.2026).
5. SQLite. Documentation [Электронный ресурс]. — URL: https://www.sqlite.org/docs.html (дата обращения: 10.05.2026).
6. Telegram Bot API [Электронный ресурс]. — URL: https://core.telegram.org/bots/api (дата обращения: 10.05.2026).
7. Лутц М. Изучаем Python: в 2 т. — 5-е изд. — М.: ДиалектикаВильямс, 2019. — Т. 1. — 832 с.

---

*Конец пояснительной записки.*
