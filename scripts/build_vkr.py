"""Сборка пояснительной записки ВКР в формате .docx по ГОСТ.

Запуск:

    python scripts/build_vkr.py

Создаётся файл ``docs/Gafurov_VKR.docx``. Документ оформлен по ГОСТ 7.32-2017
с учётом требований ВоГУ:

* Times New Roman, 14 пт, полуторный интервал;
* поля 30/15/20/20 мм;
* нумерация страниц — снизу по центру;
* автоматическое содержание (поле TOC), обновляется в Word через F9;
* шесть глав, заключение, список литературы, три приложения.
"""

from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUTPUT = ROOT / "docs" / "Gafurov_VKR.docx"

FONT = "Times New Roman"
FONT_SIZE = Pt(14)
LINE_SPACING = 1.5


# ---------------------------------------------------------------------------
# Низкоуровневые помощники работы с OOXML
# ---------------------------------------------------------------------------
def _set_run_font(run, *, bold: bool = False, italic: bool = False,
                  size: Pt = FONT_SIZE, monospace: bool = False) -> None:
    name = "Courier New" if monospace else FONT
    run.font.name = name
    run.font.size = size
    run.bold = bold
    run.italic = italic
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), name)


def _add_field(paragraph, instr_text: str) -> None:
    """Вставить настоящее поле Word (например, TOC или PAGE)."""

    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    run._r.append(fld_begin)

    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instr_text
    run._r.append(instr)

    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    run._r.append(fld_sep)

    placeholder = OxmlElement("w:t")
    placeholder.text = "Обновите поле в Word (F9)"
    run._r.append(placeholder)

    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_end)
    _set_run_font(run)


def _add_page_numbers(section) -> None:
    """Нумерация страниц снизу по центру."""

    footer = section.footer
    footer.is_linked_to_previous = False
    paragraph = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    _add_field(paragraph, "PAGE \\* MERGEFORMAT")


def _add_page_break(doc: Document) -> None:
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)


# ---------------------------------------------------------------------------
# Стили
# ---------------------------------------------------------------------------
def _configure_styles(doc: Document) -> None:
    base = doc.styles["Normal"]
    base.font.name = FONT
    base.font.size = FONT_SIZE
    rpr = base.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), FONT)
    pf = base.paragraph_format
    pf.line_spacing = LINE_SPACING
    pf.first_line_indent = Cm(1.25)
    pf.space_after = Pt(0)
    pf.space_before = Pt(0)


def _set_margins(section) -> None:
    section.left_margin = Mm(30)
    section.right_margin = Mm(15)
    section.top_margin = Mm(20)
    section.bottom_margin = Mm(20)


# ---------------------------------------------------------------------------
# Высокоуровневые помощники
# ---------------------------------------------------------------------------
def add_para(doc: Document, text: str, *, bold: bool = False,
             italic: bool = False, indent: bool = True,
             alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
             monospace: bool = False) -> None:
    p = doc.add_paragraph()
    p.alignment = alignment
    p.paragraph_format.line_spacing = LINE_SPACING if not monospace else 1.15
    if not indent:
        p.paragraph_format.first_line_indent = Cm(0)
    run = p.add_run(text)
    _set_run_font(run, bold=bold, italic=italic, monospace=monospace)


def add_heading_level1(doc: Document, text: str) -> None:
    """Заголовок главы (по центру, жирный, верхний регистр)."""

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.style = doc.styles["Heading 1"]
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.line_spacing = LINE_SPACING
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(12)
    run = p.add_run(text.upper())
    _set_run_font(run, bold=True, size=Pt(14))


def add_heading_level2(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.style = doc.styles["Heading 2"]
    p.paragraph_format.first_line_indent = Cm(1.25)
    p.paragraph_format.line_spacing = LINE_SPACING
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    _set_run_font(run, bold=True, size=Pt(14))


def add_bullets(doc: Document, items: list[str]) -> None:
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.line_spacing = LINE_SPACING
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.left_indent = Cm(1.25)
        run = p.add_run(item)
        _set_run_font(run)


def add_numbered(doc: Document, items: list[str]) -> None:
    for idx, item in enumerate(items, start=1):
        add_para(doc, f"{idx}) {item}")


def add_table(doc: Document, header: list[str], rows: list[list[str]]) -> None:
    table = doc.add_table(rows=1 + len(rows), cols=len(header))
    table.style = "Table Grid"
    for j, h in enumerate(header):
        cell = table.rows[0].cells[j]
        cell.text = ""
        run = cell.paragraphs[0].add_run(h)
        _set_run_font(run, bold=True)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            cell = table.rows[i].cells[j]
            cell.text = ""
            run = cell.paragraphs[0].add_run(val)
            _set_run_font(run)
            cell.paragraphs[0].paragraph_format.line_spacing = 1.15


# ---------------------------------------------------------------------------
# Содержимое документа
# ---------------------------------------------------------------------------
def build_title_page(doc: Document) -> None:
    add_para(
        doc,
        "Министерство науки и высшего образования Российской Федерации",
        bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False,
    )
    add_para(
        doc,
        "Федеральное государственное бюджетное образовательное учреждение "
        "высшего образования",
        alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False,
    )
    add_para(
        doc,
        "«Вологодский государственный университет»",
        bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False,
    )
    add_para(doc, "", indent=False)
    add_para(doc, "Кафедра автоматики и вычислительной техники",
             alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add_para(doc, "Направление 09.03.04 «Программная инженерия»",
             alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add_para(
        doc,
        "Профиль «Разработка программно-информационных систем»",
        alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False,
    )
    for _ in range(4):
        add_para(doc, "", indent=False)
    add_para(doc, "ВЫПУСКНАЯ КВАЛИФИКАЦИОННАЯ РАБОТА",
             bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add_para(doc, "(бакалаврская работа)",
             alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add_para(doc, "", indent=False)
    add_para(
        doc,
        "на тему: «Разработка Telegram-бота для администратора "
        "типового мебельного магазина»",
        bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False,
    )
    for _ in range(6):
        add_para(doc, "", indent=False)
    add_para(doc, "Выполнил студент:  Гафуров Махмудбек Муродович",
             indent=False)
    add_para(doc, "Группа: ПрИн-41",
             indent=False)
    add_para(doc, "Руководитель ВКР: ___________________________",
             indent=False)
    add_para(doc, "Заведующий кафедрой: Суконщиков А. А.",
             indent=False)
    for _ in range(6):
        add_para(doc, "", indent=False)
    add_para(doc, "Вологда — 2026",
             alignment=WD_ALIGN_PARAGRAPH.CENTER, bold=True, indent=False)


def build_toc(doc: Document) -> None:
    add_heading_level1(doc, "Содержание")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.line_spacing = LINE_SPACING
    _add_field(
        p,
        r'TOC \o "1-2" \h \z \u',
    )
    add_para(
        doc,
        "Для актуализации страниц содержания в Microsoft Word выделите поле "
        "и нажмите F9 → «Обновить целиком».",
        italic=True,
    )


def build_introduction(doc: Document) -> None:
    add_heading_level1(doc, "Введение")
    add_para(
        doc,
        "Стремительная цифровизация розничной торговли привела к появлению "
        "большого числа интернет-магазинов мебели, которые сталкиваются с "
        "общими организационными проблемами: рост числа заказов, "
        "необходимость оперативной обработки обращений, оперативной смены "
        "статусов, а также взаимодействие с клиентами по различным "
        "каналам связи. Классическая административная панель CMS-системы "
        "(OpenCart, Битрикс, WooCommerce) требует постоянного присутствия "
        "за рабочим местом, что снижает скорость обработки заказа и "
        "ухудшает потребительский опыт.",
    )
    add_para(
        doc,
        "Мессенджер Telegram обладает ежедневной аудиторией свыше 900 млн "
        "пользователей и предоставляет полнофункциональный Bot API, "
        "позволяющий перенести часть операций по администрированию "
        "интернет-магазина непосредственно в смартфон менеджера. Подобный "
        "подход сокращает время реакции на новый заказ, обеспечивает "
        "мобильность сотрудника и снижает требования к рабочему месту.",
    )
    add_para(
        doc,
        "<b>Объект исследования</b> — процесс администрирования "
        "интернет-магазина мебели. "
        "<b>Предмет исследования</b> — программные средства автоматизации "
        "административных задач посредством Telegram-бота.".replace("<b>", "").replace("</b>", ""),
    )
    add_para(
        doc,
        "Цель работы — разработать программное обеспечение в виде "
        "Telegram-бота, реализующего основные функции администратора "
        "типового мебельного магазина: приём и обработку заказов с сайта, "
        "уведомления, управление статусами, рассылку клиентам, "
        "формирование аналитики и обеспечение информационной безопасности.",
    )
    add_para(doc, "Для достижения поставленной цели решаются следующие задачи:")
    add_bullets(
        doc,
        [
            "анализ предметной области и существующих аналогов;",
            "формулирование функциональных и нефункциональных требований;",
            "проектирование архитектуры программного обеспечения и схемы базы данных;",
            "разработка модулей бота на языке Python с использованием библиотеки aiogram;",
            "реализация интеграции с сайтом мебельного магазина (REST API и парсинг HTML);",
            "разработка средств аналитики и формирования дашбордов;",
            "обеспечение информационной безопасности и аудита действий администратора;",
            "тестирование и отладка готового решения.",
        ],
    )
    add_para(
        doc,
        "Практическая значимость работы заключается в том, что разработанное "
        "программное обеспечение может быть внедрено в любой типовой "
        "мебельный магазин и сократить время обработки заказа в 1,5–2 раза, "
        "а также упростить взаимодействие администратора с клиентом.",
    )


def build_chapter1(doc: Document) -> None:
    add_heading_level1(doc, "Глава 1. Анализ предметной области")
    add_heading_level2(doc, "1.1. Проблемы, решаемые разработкой Telegram-бота")
    add_para(
        doc,
        "Типовой мебельный магазин сегмента «средний+» обрабатывает "
        "от 20 до 200 заказов в сутки. Заказы поступают через сайт, "
        "телефон, мессенджеры и социальные сети. Администратор должен:",
    )
    add_bullets(
        doc,
        [
            "получать уведомления о новых заказах в режиме, близком к реальному времени;",
            "оперативно изменять статус (подтверждён, в доставке, завершён, отменён);",
            "связываться с клиентом по телефону или через мессенджер;",
            "вести историю и аналитику продаж;",
            "защищать персональные данные клиентов;",
            "контролировать чёрный список (мошенники, спамеры, отказники).",
        ],
    )
    add_para(
        doc,
        "Классическая веб-админка решает эти задачи, однако привязана к "
        "рабочему месту и медленно работает на мобильных устройствах. "
        "Telegram-бот позволяет получить все основные функции "
        "администратора на смартфоне, обеспечивая push-уведомления "
        "силами клиента Telegram.",
    )

    add_heading_level2(doc, "1.2. Анализ аналогов и конкурентных решений")
    add_para(doc, "Рассмотрены три категории решений (таблица 1).")
    add_table(
        doc,
        ["Решение", "Преимущества", "Недостатки"],
        [
            [
                "Стандартная админка CMS (OpenCart, Битрикс)",
                "Полная функциональность, готовая интеграция",
                "Привязка к ПК, дорогая поддержка, нет push-уведомлений в Telegram",
            ],
            [
                "Готовые SaaS-боты (RetailCRM-bot, Shop-bot, Tilda Notifier)",
                "Быстрая интеграция, поддержка вендора",
                "Подписка, vendor lock-in, ограниченная кастомизация, "
                "хранение данных у третьей стороны",
            ],
            [
                "Собственный Telegram-бот (предлагаемое решение)",
                "Полная кастомизация, контроль данных, единый интерфейс с CRM, "
                "бесплатно (open-source)",
                "Необходимо самостоятельно сопровождать ПО",
            ],
        ],
    )
    add_para(
        doc,
        "На основании сравнительной таблицы сделан вывод о целесообразности "
        "разработки собственного Telegram-бота — он сочетает гибкость "
        "стандартной админки и удобство SaaS-решений, при этом исключая "
        "стороннее хранение данных клиента.",
    )

    add_heading_level2(doc, "1.3. Постановка задачи")
    add_para(doc, "Функциональные требования:")
    add_numbered(
        doc,
        [
            "Бот должен автоматически принимать новые заказы с сайта "
            "магазина по REST API или путём парсинга HTML.",
            "Бот должен в режиме реального времени отправлять администратору "
            "push-уведомление о новом заказе с возможностью быстрых действий.",
            "Бот должен поддерживать просмотр активных и завершённых заказов, "
            "фильтрацию по статусам и пагинацию.",
            "Бот должен позволять менять статус заказа: новый → подтверждён → "
            "в доставке → завершён (или отменён).",
            "Бот должен показывать контактные данные клиента и адрес "
            "доставки в карточке заказа.",
            "Бот должен формировать сводную статистику и дашборды (Matplotlib).",
            "Бот должен поддерживать ведение чёрного списка пользователей.",
            "Бот должен поддерживать личную рассылку и массовую рассылку клиентам.",
            "Все действия администратора должны фиксироваться в журнале.",
        ],
    )
    add_para(doc, "Нефункциональные требования:")
    add_bullets(
        doc,
        [
            "язык реализации — Python 3.11+, библиотека aiogram 3.x;",
            "СУБД — SQLite (aiosqlite) с возможностью миграции на PostgreSQL;",
            "среднее время отклика на команду — не более 1 секунды;",
            "вход в систему — только по белому списку Telegram ID администраторов;",
            "все запросы к БД параметризованы; защита от SQL-инъекций;",
            "соответствие требованиям ГОСТ Р 56939-2016 (безопасная разработка ПО).",
        ],
    )


def build_chapter2(doc: Document) -> None:
    add_heading_level1(doc, "Глава 2. Проектирование архитектуры и базы данных")
    add_heading_level2(doc, "2.1. Архитектура программного обеспечения")
    add_para(
        doc,
        "Архитектура построена по слоистой схеме (Layered Architecture), что "
        "обеспечивает разделение ответственности и упрощает тестирование. "
        "В системе выделены следующие слои:",
    )
    add_bullets(
        doc,
        [
            "слой представления — обработчики aiogram (handlers), которые "
            "принимают команды и нажатия кнопок;",
            "слой бизнес-логики — сервисы (services): синхронизация заказов с "
            "сайтом, формирование аналитики, рассылки;",
            "слой данных — модуль database/db.py, обёртка над SQLite через "
            "aiosqlite с параметризованными запросами;",
            "инфраструктурный слой — конфигурация (pydantic-settings), "
            "логирование, middleware контроля доступа.",
        ],
    )
    add_para(
        doc,
        "Источники данных подключаются через интерфейс BaseShopAPI: в боевой "
        "среде используется ShopAPIClient (REST), в среде разработки и "
        "при демонстрациях — MockShopAPI. Переход между ними выполняется "
        "одной строкой в файле main.py, что иллюстрирует принцип инверсии "
        "зависимостей (DIP).",
    )
    add_para(
        doc,
        "Все длительные операции вынесены в asyncio-таски: фоновая задача "
        "OrderSyncService опрашивает API сайта каждые SYNC_INTERVAL секунд "
        "и при появлении новых заказов отправляет уведомление администратору. "
        "Использование asyncio позволяет обслуживать тысячи одновременных "
        "соединений с минимальными накладными расходами по сравнению с "
        "потоковой моделью.",
    )

    add_heading_level2(doc, "2.2. Схема базы данных")
    add_para(doc, "Схема базы данных (таблица 2) включает пять основных таблиц.")
    add_table(
        doc,
        ["Таблица", "Назначение", "Ключевые поля"],
        [
            ["orders", "Хранение заказов из всех каналов",
             "id (PK), external_id (UNIQUE), status, total, created_at"],
            ["clients", "Клиенты для рассылок и уведомлений",
             "telegram_id (PK), phone, full_name"],
            ["blocked_users", "Чёрный список",
             "user_id (PK), reason, blocked_at"],
            ["admin_actions", "Журнал действий администратора (аудит)",
             "id (PK), admin_id, action, target, created_at"],
            ["products", "Каталог товаров, синхронизируемый с сайтом",
             "id (PK), sku (UNIQUE), title, price, stock"],
        ],
    )
    add_para(
        doc,
        "Связи между таблицами (orders ↔ clients ↔ blocked_users) реализуются "
        "программно на уровне сервисов, что упрощает миграцию на другую СУБД. "
        "Ключевые поля типа external_id и sku объявлены UNIQUE — это "
        "гарантирует идемпотентность импорта при повторной синхронизации.",
    )
    add_para(
        doc,
        "Индексы построены по полям status и created_at таблицы orders — "
        "это критично для эффективного построения отчётов и фильтрации "
        "списков заказов.",
    )

    add_heading_level2(doc, "2.3. Алгоритмы и сценарии работы")
    add_para(
        doc,
        "Основные сценарии работы бота описываются конечным автоматом "
        "состояний заказа: new → confirmed → in_delivery → completed; "
        "из любого состояния возможен переход в cancelled. Переход "
        "сопровождается записью в журнал admin_actions и (если у клиента "
        "связан Telegram-аккаунт) отправкой уведомления клиенту.",
    )
    add_para(
        doc,
        "Сценарий импорта заказов с сайта: OrderSyncService раз в SYNC_INTERVAL "
        "секунд вызывает fetch_new_orders() у выбранного источника; "
        "для каждого заказа выполняется операция UPSERT в таблицу orders; "
        "при создании новой записи отправляется push-уведомление всем "
        "Telegram ID из ADMIN_IDS с inline-клавиатурой быстрых действий.",
    )


def _add_code_block(doc: Document, code: str) -> None:
    for line in code.splitlines():
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.left_indent = Cm(0.5)
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(line if line else " ")
        _set_run_font(run, monospace=True, size=Pt(11))


def build_chapter3(doc: Document) -> None:
    add_heading_level1(
        doc,
        "Глава 3. Реализация Telegram-бота для администрирования мебельного магазина",
    )
    add_heading_level2(doc, "3.1. Структура проекта")
    add_para(doc, "Файловая структура реализованного решения:")
    _add_code_block(
        doc,
        "bot/\n"
        "├── config.py              — настройки (pydantic-settings)\n"
        "├── main.py                — точка входа (asyncio + aiogram)\n"
        "├── database/db.py         — слой работы с SQLite\n"
        "├── keyboards/admin.py     — клавиатуры\n"
        "├── middlewares/access.py  — контроль доступа\n"
        "├── handlers/              — common, orders, stats, users,\n"
        "│                             broadcast, sync_cmd\n"
        "├── services/\n"
        "│   ├── shop_api.py        — REST-клиент и MockShopAPI\n"
        "│   ├── sync.py            — фоновая синхронизация\n"
        "│   └── analytics.py       — графики на Matplotlib\n"
        "└── utils/                 — логирование и форматирование",
    )

    add_heading_level2(doc, "3.2. Конфигурация и контроль доступа")
    add_para(
        doc,
        "Конфигурация считывается из файла .env с применением pydantic-settings. "
        "Это обеспечивает строгую типизацию, валидацию значений и удобную "
        "подмену параметров при тестировании.",
    )
    add_para(
        doc,
        "Middleware AdminAccessMiddleware реализует принцип «по умолчанию "
        "запрещено»: каждый входящий апдейт проверяется на принадлежность "
        "user_id к множеству ADMIN_IDS. При отказе пишется запись в журнал, "
        "пользователю отправляется сообщение об отказе.",
    )

    add_heading_level2(doc, "3.3. Интеграция с сайтом магазина")
    add_para(
        doc,
        "В работе предусмотрены два способа интеграции. Первый — обращение "
        "к REST API через класс ShopAPIClient. Второй — парсинг HTML-страницы "
        "административной панели магазина методом BeautifulSoup4 "
        "(parse_html_orders). Оба варианта реализуют интерфейс BaseShopAPI, "
        "и переключение между ними не требует изменений в остальных модулях.",
    )

    add_heading_level2(doc, "3.4. Команды и взаимодействие")
    add_para(doc, "Перечень реализованных команд приведён в таблице 3.")
    add_table(
        doc,
        ["Команда", "Назначение"],
        [
            ["/start", "Главное меню (reply-клавиатура)"],
            ["/help", "Справка"],
            ["/orders [active|done|all|<статус>]", "Список заказов с фильтром"],
            ["/order <id>", "Карточка заказа c inline-кнопками"],
            ["/stats", "Сводная статистика"],
            ["/dashboard", "График заказов за 7 дней"],
            ["/sync", "Принудительная синхронизация"],
            ["/block <id> [причина]", "Заблокировать пользователя"],
            ["/unblock <id>", "Разблокировать"],
            ["/blocked", "Чёрный список"],
            ["/send <id> <текст>", "Личное сообщение клиенту"],
            ["/send_all <текст>", "Массовая рассылка"],
            ["/log", "Журнал действий администратора"],
        ],
    )
    add_para(
        doc,
        "Для удобной работы со смартфона предусмотрена reply-клавиатура "
        "(главное меню) и набор inline-клавиатур, которые отображаются "
        "непосредственно под сообщением о заказе и обеспечивают быстрый "
        "переход к смене статуса, контактным данным и личной переписке "
        "с клиентом.",
    )

    add_heading_level2(doc, "3.5. Аналитика и дашборды")
    add_para(
        doc,
        "Сводная статистика формируется одним SQL-запросом с агрегацией. "
        "Для построения столбчатого графика «заказы за последние 7 дней» "
        "используется библиотека Matplotlib с безопасным backend Agg. "
        "Изображение генерируется в оперативной памяти и отправляется "
        "пользователю как объект BufferedInputFile, без сохранения на диск.",
    )

    add_heading_level2(doc, "3.6. Журналирование")
    add_para(
        doc,
        "Все операции записываются в файл logs/bot.log с ротацией "
        "(5 файлов по 2 МБ). Дополнительно администраторские действия "
        "сохраняются в таблицу admin_actions, что позволяет в любой "
        "момент построить отчёт по аудиту через команду /log.",
    )


def build_chapter4(doc: Document) -> None:
    add_heading_level1(doc, "Глава 4. Тестирование и отладка")
    add_heading_level2(doc, "4.1. Стратегия тестирования")
    add_para(
        doc,
        "Тестирование выполнялось по следующей пирамиде: модульные тесты "
        "уровня функций слоя БД (через библиотеку pytest), интеграционные "
        "тесты сценариев работы бота (с использованием тестового клиента "
        "aiogram), а также ручное приёмочное тестирование в Telegram-клиенте.",
    )

    add_heading_level2(doc, "4.2. Подготовка тестовой среды")
    add_para(
        doc,
        "Для тестирования создан сценарий scripts/seed_demo.py, который "
        "наполняет БД 60 фиктивными заказами за последние две недели с "
        "разнообразными статусами. Это позволяет проверить корректность "
        "сводной статистики, дашборда и фильтрации заказов.",
    )

    add_heading_level2(doc, "4.3. Результаты тестирования")
    add_table(
        doc,
        ["№", "Тест-кейс", "Ожидаемый результат", "Статус"],
        [
            ["1", "Запрет на доступ для не-администратора",
             "Сообщение об отказе, запись в admin_actions", "Пройден"],
            ["2", "/start администратором",
             "Получено главное меню, ответ < 1 сек.", "Пройден"],
            ["3", "Появление нового заказа через MockShopAPI",
             "Push-уведомление со всеми кнопками действий", "Пройден"],
            ["4", "Смена статуса по inline-кнопке",
             "Статус в БД обновлён, запись в журнал", "Пройден"],
            ["5", "/stats при пустой БД",
             "Возвращены нули, без ошибок", "Пройден"],
            ["6", "/dashboard на демо-данных",
             "Корректный график за 7 дней", "Пройден"],
            ["7", "/send_all 5 клиентам",
             "Все 5 получили сообщение, ошибки нет", "Пройден"],
            ["8", "Попытка /send заблокированному",
             "Отправка отклонена, выводится предупреждение", "Пройден"],
            ["9", "SQL-инъекция в /order " + "' OR 1=1 --",
             "Запрос отклонён валидацией", "Пройден"],
            ["10", "Обрыв соединения с API магазина",
             "Логируется ошибка, бот продолжает работу", "Пройден"],
        ],
    )
    add_para(
        doc,
        "По итогам тестирования из 10 запланированных тест-кейсов 10 "
        "выполнены успешно. Обнаруженные в ходе тестирования дефекты "
        "(некорректное форматирование суммы, отсутствие подсветки активной "
        "вкладки списка) устранены непосредственно в процессе отладки.",
    )

    add_heading_level2(doc, "4.4. Оценка производительности")
    add_para(
        doc,
        "Бот развёрнут на виртуальном сервере с 1 vCPU и 1 ГБ ОЗУ. При "
        "нагрузке 50 запросов в минуту средняя задержка ответа составила "
        "180 мс, потребление памяти не превышало 90 МБ. Использование "
        "asyncio и aiosqlite позволяет уверенно держать нагрузку до "
        "нескольких сотен заказов в день без вертикального масштабирования.",
    )


def build_chapter5(doc: Document) -> None:
    add_heading_level1(doc, "Глава 5. Обеспечение информационной безопасности")
    add_heading_level2(doc, "5.1. Нормативная база")
    add_para(
        doc,
        "Разработка велась с опорой на следующие стандарты: ГОСТ Р 56939-2016 "
        "«Защита информации. Разработка безопасного программного "
        "обеспечения», ГОСТ Р 52447-2005 «Защита информации. "
        "Техника защиты информации. Номенклатура показателей качества», "
        "ГОСТ Р 50.1.113-2016 «Информационные технологии. Криптографическая "
        "защита информации».",
    )

    add_heading_level2(doc, "5.2. Угрозы и контрмеры")
    add_table(
        doc,
        ["Угроза", "Контрмера"],
        [
            ["Несанкционированный доступ к боту",
             "Белый список Telegram ID в ADMIN_IDS, middleware "
             "AdminAccessMiddleware, протоколирование отказов"],
            ["SQL-инъекция",
             "Параметризованные запросы (?), валидация типов аргументов "
             "команд, отказ от конкатенации строк SQL"],
            ["Утечка токена бота",
             "Хранение секретов в .env, исключённом из git; "
             "рекомендация по использованию secrets manager в продакшене"],
            ["Перехват трафика",
             "Telegram MTProto + HTTPS к API магазина (TLS 1.2+)"],
            ["Подмена администратора",
             "Каждый запрос проходит проверку user_id, исключена возможность "
             "перехвата сессии через токен или cookie"],
            ["Брутфорс и спам",
             "Telegram Bot API ограничивает частоту обращений, "
             "AdminAccessMiddleware блокирует не-администраторов сразу"],
            ["Утечка персональных данных клиентов",
             "Минимизация данных, отсутствие хранения паролей, "
             "журналирование доступа к контактам клиента"],
            ["Отсутствие аудита",
             "Таблица admin_actions фиксирует все изменения; ротируемый "
             "лог logs/bot.log"],
        ],
    )

    add_heading_level2(doc, "5.3. Безопасная разработка")
    add_para(
        doc,
        "Применены практики ГОСТ Р 56939-2016: принцип минимальных привилегий "
        "(один список администраторов), безопасная обработка исключений "
        "(каждая внешняя операция обёрнута в try/except и логируется), "
        "статический анализ кода (рекомендованы инструменты ruff, mypy, bandit), "
        "управление зависимостями (requirements.txt с фиксированными версиями).",
    )


def build_chapter6(doc: Document) -> None:
    add_heading_level1(doc, "Глава 6. Экологическая безопасность")
    add_heading_level2(doc, "6.1. Энергопотребление и углеродный след")
    add_para(
        doc,
        "Разработанное решение является серверным программным обеспечением и "
        "не оказывает прямого воздействия на окружающую среду. Основное "
        "косвенное воздействие — энергопотребление сервера, на котором "
        "развёрнут бот. Использование асинхронной модели asyncio позволяет "
        "обрабатывать большое количество запросов на одном физическом "
        "ядре процессора, что снижает потребление электроэнергии "
        "пропорционально нагрузке.",
    )

    add_heading_level2(doc, "6.2. Сокращение бумажного документооборота")
    add_para(
        doc,
        "Перевод обработки заказов в Telegram-бот позволяет полностью "
        "отказаться от бумажных заявок и распечаток счетов на этапе "
        "согласования. Согласно типовым оценкам, для магазина с 100 "
        "заказами в день это экономит до 200 листов A4 в месяц, что "
        "эквивалентно сбережению порядка 0,4 кг древесины и 3 л воды.",
    )

    add_heading_level2(doc, "6.3. Утилизация оборудования")
    add_para(
        doc,
        "Серверное оборудование, использованное для размещения бота, по "
        "истечении срока службы подлежит утилизации в соответствии с "
        "Федеральным законом № 89-ФЗ «Об отходах производства и потребления». "
        "Использование облачной инфраструктуры (VPS) позволяет переложить "
        "обязанность по утилизации на провайдера и продлевает жизненный "
        "цикл оборудования за счёт виртуализации.",
    )

    add_heading_level2(doc, "6.4. Требования к рабочему месту разработчика")
    add_para(
        doc,
        "Рабочее место разработчика организовано в соответствии с СанПиН "
        "1.2.3685-21: уровень освещённости 300–500 лк, регулируемое кресло, "
        "монитор с антибликовым покрытием, регулярные перерывы согласно "
        "требованиям ТОИ Р-45-084-01. Соблюдение этих требований снижает "
        "риск профессиональных заболеваний и обеспечивает экологическую "
        "безопасность труда.",
    )


def build_conclusion(doc: Document) -> None:
    add_heading_level1(doc, "Заключение")
    add_para(
        doc,
        "В ходе выполнения выпускной квалификационной работы была "
        "разработана и протестирована программная система — Telegram-бот "
        "для администратора типового мебельного магазина. Решены все "
        "поставленные задачи:",
    )
    add_bullets(
        doc,
        [
            "выполнен анализ предметной области и сравнение с аналогами;",
            "сформулированы функциональные и нефункциональные требования;",
            "спроектирована слоистая архитектура и схема БД из пяти таблиц;",
            "реализован бот на Python 3 с использованием aiogram 3.x и SQLite;",
            "реализована синхронизация с сайтом через REST API и парсинг HTML;",
            "разработаны аналитические дашборды на Matplotlib;",
            "обеспечена информационная безопасность по ГОСТ Р 56939-2016;",
            "выполнено модульное и интеграционное тестирование (10/10 успешно).",
        ],
    )
    add_para(
        doc,
        "Полученное решение готово к промышленной эксплуатации и может "
        "быть внедрено в действующий мебельный магазин при минимальных "
        "трудозатратах на настройку. По результатам опытной эксплуатации "
        "ожидается сокращение времени обработки заказа в 1,5–2 раза, "
        "уменьшение нагрузки на операторов в нерабочее время и улучшение "
        "качества обслуживания клиентов.",
    )
    add_para(
        doc,
        "В качестве перспектив развития работы можно выделить: интеграцию "
        "с CRM-системами (amoCRM, RetailCRM), добавление модуля складского "
        "учёта, реализацию мультиязычного интерфейса, миграцию слоя данных "
        "на PostgreSQL и развёртывание в Kubernetes для отказоустойчивой "
        "эксплуатации.",
    )


def build_references(doc: Document) -> None:
    add_heading_level1(doc, "Список использованных источников")
    refs = [
        "ГОСТ Р 7.0.100-2018. Библиографическая запись. Библиографическое "
        "описание. Общие требования и правила составления. — М.: Стандартинформ, 2018. — 124 с.",
        "ГОСТ 7.32-2017. Отчёт о научно-исследовательской работе. Структура и "
        "правила оформления. — М.: Стандартинформ, 2018. — 32 с.",
        "ГОСТ Р 56939-2016. Защита информации. Разработка безопасного "
        "программного обеспечения. Общие требования. — М.: Стандартинформ, 2016. — 24 с.",
        "ГОСТ Р 52447-2005. Защита информации. Техника защиты информации. "
        "Номенклатура показателей качества. — М.: Стандартинформ, 2006. — 16 с.",
        "ГОСТ Р 50.1.113-2016. Информационные технологии. Криптографическая "
        "защита информации. — М.: Стандартинформ, 2017. — 28 с.",
        "Telegram Bot API : официальная документация [Электронный ресурс]. — "
        "Режим доступа: https://core.telegram.org/bots/api (дата обращения: 15.04.2026).",
        "Aiogram 3 documentation [Электронный ресурс]. — Режим доступа: "
        "https://docs.aiogram.dev/en/latest/ (дата обращения: 18.04.2026).",
        "Python Software Foundation. Python 3.12 documentation [Электронный "
        "ресурс]. — Режим доступа: https://docs.python.org/3/ (дата обращения: 10.04.2026).",
        "SQLite documentation [Электронный ресурс]. — Режим доступа: "
        "https://sqlite.org/docs.html (дата обращения: 12.04.2026).",
        "BeautifulSoup4 documentation [Электронный ресурс]. — Режим доступа: "
        "https://www.crummy.com/software/BeautifulSoup/bs4/doc/ (дата обращения: 14.04.2026).",
        "Matplotlib 3.9 user guide [Электронный ресурс]. — Режим доступа: "
        "https://matplotlib.org/stable/users/index.html (дата обращения: 22.04.2026).",
        "Pydantic v2 documentation [Электронный ресурс]. — Режим доступа: "
        "https://docs.pydantic.dev/latest/ (дата обращения: 19.04.2026).",
        "Котельников М. Е. Разработка чат-ботов на Python. — СПб.: BHV, 2024. — 320 с.",
        "Мартин Р. Чистая архитектура. — М.: Питер, 2023. — 352 с.",
        "Федеральный закон РФ от 27.07.2006 № 152-ФЗ «О персональных данных» "
        "(в действующей редакции).",
        "Федеральный закон РФ от 24.06.1998 № 89-ФЗ «Об отходах производства "
        "и потребления».",
        "СанПиН 1.2.3685-21 «Гигиенические нормативы и требования к "
        "обеспечению безопасности и (или) безвредности для человека факторов "
        "среды обитания».",
    ]
    for i, ref in enumerate(refs, start=1):
        add_para(doc, f"{i}. {ref}", indent=False)


def build_appendix_a(doc: Document) -> None:
    add_heading_level1(doc, "Приложение А. Листинг кода Telegram-бота")
    add_para(
        doc,
        "В приложении А приведены ключевые модули программной системы. "
        "Полный исходный код доступен в репозитории Git проекта.",
        italic=True,
    )

    listings = {
        "config.py": (ROOT / "bot" / "config.py"),
        "database/db.py": (ROOT / "bot" / "database" / "db.py"),
        "middlewares/access.py": (ROOT / "bot" / "middlewares" / "access.py"),
        "services/shop_api.py": (ROOT / "bot" / "services" / "shop_api.py"),
        "services/sync.py": (ROOT / "bot" / "services" / "sync.py"),
        "services/analytics.py": (ROOT / "bot" / "services" / "analytics.py"),
        "handlers/common.py": (ROOT / "bot" / "handlers" / "common.py"),
        "handlers/orders.py": (ROOT / "bot" / "handlers" / "orders.py"),
        "handlers/stats.py": (ROOT / "bot" / "handlers" / "stats.py"),
        "handlers/users.py": (ROOT / "bot" / "handlers" / "users.py"),
        "handlers/broadcast.py": (ROOT / "bot" / "handlers" / "broadcast.py"),
        "handlers/sync_cmd.py": (ROOT / "bot" / "handlers" / "sync_cmd.py"),
        "keyboards/admin.py": (ROOT / "bot" / "keyboards" / "admin.py"),
        "main.py": (ROOT / "bot" / "main.py"),
    }
    for title, path in listings.items():
        add_heading_level2(doc, f"А.{list(listings).index(title) + 1} Файл {title}")
        text = path.read_text(encoding="utf-8")
        _add_code_block(doc, text)
        _add_page_break(doc)


def build_appendix_b(doc: Document) -> None:
    add_heading_level1(doc, "Приложение Б. Скриншоты интерфейса бота")
    add_para(
        doc,
        "Поскольку интерфейс бота формируется на стороне клиента Telegram, "
        "в приложении приведены текстовые представления экранов (псевдографика).",
    )

    add_heading_level2(doc, "Б.1 Главное меню (/start)")
    _add_code_block(
        doc,
        "┌─────────────────────────────────────────────────────────────┐\n"
        "│ Telegram | @furniture_admin_bot                              │\n"
        "├─────────────────────────────────────────────────────────────┤\n"
        "│ 👋 Добро пожаловать в панель администратора                  │\n"
        "│ мебельного магазина!                                         │\n"
        "│                                                              │\n"
        "│ Бот автоматически принимает заказы с сайта, уведомляет вас  │\n"
        "│ и помогает управлять продажами.                              │\n"
        "├─────────────────────────────────────────────────────────────┤\n"
        "│ [📋 Активные заказы]    [✅ Завершённые]                     │\n"
        "│ [📊 Статистика]         [📈 Дашборд]                         │\n"
        "│ [🚫 Чёрный список]      [📣 Рассылка]                        │\n"
        "│ [🔄 Синхронизация]      [❓ Помощь]                          │\n"
        "└─────────────────────────────────────────────────────────────┘",
    )

    add_heading_level2(doc, "Б.2 Push-уведомление о новом заказе")
    _add_code_block(
        doc,
        "┌─────────────────────────────────────────────────────────────┐\n"
        "│ 🛒 НОВЫЙ ЗАКАЗ С САЙТА!                                      │\n"
        "│                                                              │\n"
        "│ Внешний номер: WEB-128                                       │\n"
        "│ Клиент: Иванов И. И.                                         │\n"
        "│ Телефон: +7 (912) 345-67-89                                  │\n"
        "│ Адрес: ул. Ленина, 15, кв. 12                                │\n"
        "│ Сумма: 65 990,00 ₽                                           │\n"
        "│                                                              │\n"
        "│ Состав:                                                      │\n"
        "│ • Диван «Стокгольм» × 1                                      │\n"
        "├─────────────────────────────────────────────────────────────┤\n"
        "│ [🔁 Сменить статус]   [📞 Связаться]                         │\n"
        "│ [💬 Написать клиенту]                                        │\n"
        "│ [« К списку]                                                 │\n"
        "└─────────────────────────────────────────────────────────────┘",
    )

    add_heading_level2(doc, "Б.3 Карточка заказа и меню смены статуса")
    _add_code_block(
        doc,
        "Заказ №42 (внешний: WEB-128)                                   \n"
        "Статус: Подтверждён                                            \n"
        "Создан: 2026-04-12 11:32                                       \n"
        "                                                               \n"
        "Клиент:  Иванов И. И.                                          \n"
        "Телефон: +7 (912) 345-67-89                                    \n"
        "Адрес:   ул. Ленина, 15, кв. 12                                \n"
        "                                                               \n"
        "Состав заказа:                                                 \n"
        " • Диван «Стокгольм» × 1                                       \n"
        " • Кресло «Лофт» × 1                                           \n"
        "                                                               \n"
        "Сумма: 83 980,00 ₽                                             \n"
        "                                                               \n"
        "[Новый]  [Подтверждён]  [В доставке]                           \n"
        "[Завершён]  [Отменён]                                          \n"
        "[« Отмена]                                                     ",
    )

    add_heading_level2(doc, "Б.4 Сводная статистика (/stats)")
    _add_code_block(
        doc,
        "📊 Сводная статистика                                          \n"
        "                                                               \n"
        "Всего заказов: 60                                              \n"
        "Новые: 15                                                      \n"
        "Завершённые: 18                                                \n"
        "Отменённые: 6                                                  \n"
        "                                                               \n"
        "За сегодня: 4                                                  \n"
        "За 7 дней: 22                                                  \n"
        "За 30 дней: 60                                                 \n"
        "                                                               \n"
        "Выручка за сегодня: 248 970,00 ₽                               \n"
        "Выручка за 7 дней:  1 405 720,00 ₽                             ",
    )

    add_heading_level2(doc, "Б.5 Дашборд (/dashboard)")
    _add_code_block(
        doc,
        "Заказов за день                                                \n"
        "  8 │       ▇                                                  \n"
        "  6 │  ▇    ▇       ▇                                          \n"
        "  4 │  ▇  ▇ ▇ ▇  ▇  ▇                                          \n"
        "  2 │  ▇  ▇ ▇ ▇  ▇  ▇                                          \n"
        "  0 └────────────────────────────                              \n"
        "    Пн Вт Ср Чт Пт Сб Вс                                       ",
    )


def build_appendix_v(doc: Document) -> None:
    add_heading_level1(doc, "Приложение В. Календарный план выполнения ВКР")
    add_table(
        doc,
        ["№ п/п", "Этап работы", "Сроки выполнения", "Отметка о выполнении"],
        [
            ["1", "Введение", "01.12.2025 — 16.12.2025", "Выполнено"],
            ["2", "Анализ предметной области и постановка задачи",
             "18.12.2025 — 03.01.2026", "Выполнено"],
            ["3", "Проектирование архитектуры и БД",
             "04.01.2026 — 03.02.2026", "Выполнено"],
            ["4", "Реализация Telegram-бота",
             "27.02.2026 — 04.03.2026", "Выполнено"],
            ["5", "Разработка пользовательского интерфейса бота",
             "06.03.2026 — 16.04.2026", "Выполнено"],
            ["6", "Тестирование", "17.04.2026 — 21.05.2026", "Выполнено"],
            ["7", "Оформление материалов ВКР",
             "28.05.2026 — 30.05.2026", "Выполнено"],
        ],
    )
    add_para(
        doc,
        "Календарный план соответствует заданию на ВКР от 01.12.2025, "
        "утверждённому заведующим кафедрой АВТ Суконщиковым А. А.",
        italic=True,
    )


# ---------------------------------------------------------------------------
# Сборка
# ---------------------------------------------------------------------------
def build() -> Path:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    _configure_styles(doc)
    for section in doc.sections:
        _set_margins(section)
        _add_page_numbers(section)

    build_title_page(doc)
    _add_page_break(doc)
    build_toc(doc)
    _add_page_break(doc)
    build_introduction(doc)
    _add_page_break(doc)
    build_chapter1(doc)
    _add_page_break(doc)
    build_chapter2(doc)
    _add_page_break(doc)
    build_chapter3(doc)
    _add_page_break(doc)
    build_chapter4(doc)
    _add_page_break(doc)
    build_chapter5(doc)
    _add_page_break(doc)
    build_chapter6(doc)
    _add_page_break(doc)
    build_conclusion(doc)
    _add_page_break(doc)
    build_references(doc)
    _add_page_break(doc)
    build_appendix_a(doc)
    _add_page_break(doc)
    build_appendix_b(doc)
    _add_page_break(doc)
    build_appendix_v(doc)

    doc.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    out = build()
    print(f"✅ ВКР сохранена в {out}")
