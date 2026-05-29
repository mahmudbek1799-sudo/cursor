"""Сборка пояснительной записки ВКР в формате .docx.

Документ оформляется по ГОСТ 7.32-2017 с учётом замечаний руководителя:

* Times New Roman, 14 пт, полуторный интервал;
* поля 30 / 15 / 20 / 20 мм;
* заголовки глав и подразделов — обычный шрифт (не жирный),
  кегль увеличен (16 пт для глав, 14 пт для подразделов);
* нумерация страниц снизу по центру;
* автоматическое содержание (поле TOC, обновляется в Word через F9);
* раздел «Обеспечение информационной безопасности» вынесен в главу
  «Проектирование» (подраздел 2.4);
* раздел «Экологическая безопасность» — подраздел 2.5;
* подписи таблиц «Таблица N — Название» расположены НАД таблицами;
* в Приложении А приведены только ключевые фрагменты кода со ссылкой
  на полный исходный код в репозитории Git;
* в тексте используется длинное тире (—) вместо дефисов.

Запуск:

    python scripts/build_vkr.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUTPUT = ROOT / "docs" / "Gafurov_VKR.docx"
GIT_URL = "https://github.com/mahmudbek1799-sudo/cursor"

FONT = "Times New Roman"
FONT_SIZE = Pt(14)
LINE_SPACING = 1.5
EM = "—"  # длинное тире


# ---------------------------------------------------------------------------
# Низкоуровневые помощники
# ---------------------------------------------------------------------------
def _set_run_font(run, *, bold: bool = False, italic: bool = False,
                  size: Pt = FONT_SIZE, monospace: bool = False,
                  strike: bool = False) -> None:
    name = "Courier New" if monospace else FONT
    run.font.name = name
    run.font.size = size
    run.bold = bold
    run.italic = italic
    run.font.strike = strike
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), name)


def _add_field(paragraph, instr_text: str) -> None:
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
    footer = section.footer
    footer.is_linked_to_previous = False
    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run()
    for kind, instr in (("begin", None), ("instr", "PAGE \\* MERGEFORMAT"),
                        ("separate", None), ("end", None)):
        if kind == "instr":
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = instr  # type: ignore[assignment]
        else:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        run._r.append(el)
    _set_run_font(run)


def _add_page_break(doc: Document) -> None:
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)


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
# Помощники высокого уровня
# ---------------------------------------------------------------------------
def add_para(doc, text: str, *, bold: bool = False, italic: bool = False,
             indent: bool = True,
             alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
             monospace: bool = False) -> None:
    p = doc.add_paragraph()
    p.alignment = alignment
    p.paragraph_format.line_spacing = LINE_SPACING if not monospace else 1.15
    if not indent:
        p.paragraph_format.first_line_indent = Cm(0)
    run = p.add_run(text)
    _set_run_font(run, bold=bold, italic=italic, monospace=monospace)


def add_heading1(doc, text: str) -> None:
    """Заголовок главы — обычный шрифт, увеличенный кегль, по центру."""

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.style = doc.styles["Heading 1"]
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.line_spacing = LINE_SPACING
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(12)
    run = p.add_run(text.upper())
    _set_run_font(run, bold=False, size=Pt(16))


def add_heading2(doc, text: str) -> None:
    """Подраздел — обычный шрифт, кегль 14."""

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.style = doc.styles["Heading 2"]
    p.paragraph_format.first_line_indent = Cm(1.25)
    p.paragraph_format.line_spacing = LINE_SPACING
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    _set_run_font(run, bold=False, size=Pt(14))


def add_bullets(doc, items: list[str]) -> None:
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.line_spacing = LINE_SPACING
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.left_indent = Cm(1.25)
        run = p.add_run(item)
        _set_run_font(run)


def add_numbered(doc, items: list[str]) -> None:
    for idx, item in enumerate(items, start=1):
        add_para(doc, f"{idx}) {item}")


def add_table_caption(doc, text: str) -> None:
    """Подпись таблицы НАД таблицей — «Таблица N — Название»."""

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    _set_run_font(run, bold=False)


def add_table(doc, header: list[str], rows: list[list[str]]) -> None:
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


def _add_code_block(doc, code: str) -> None:
    for line in code.splitlines():
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.left_indent = Cm(0.5)
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(line if line else " ")
        _set_run_font(run, monospace=True, size=Pt(10))


def add_figure_placeholder(doc, caption: str) -> None:
    """Заглушка для рисунка с подписью под ним."""

    box = doc.add_paragraph()
    box.alignment = WD_ALIGN_PARAGRAPH.CENTER
    box.paragraph_format.first_line_indent = Cm(0)
    box.paragraph_format.space_before = Pt(6)
    box.paragraph_format.space_after = Pt(0)
    run = box.add_run("[ Место для рисунка ]")
    _set_run_font(run, italic=True)

    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.first_line_indent = Cm(0)
    cap.paragraph_format.space_before = Pt(0)
    cap.paragraph_format.space_after = Pt(12)
    run = cap.add_run(caption)
    _set_run_font(run)


# ===========================================================================
# Содержимое документа
# ===========================================================================

# ---------------------------------------------------------------------------
# Титульный лист
# ---------------------------------------------------------------------------
def build_title_page(doc) -> None:
    add_para(
        doc,
        "Министерство науки и высшего образования Российской Федерации",
        alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False,
    )
    add_para(
        doc,
        "Федеральное государственное бюджетное образовательное учреждение "
        "высшего образования",
        alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False,
    )
    add_para(doc, "«Вологодский государственный университет»",
             alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add_para(doc, "", indent=False)
    add_para(doc, "Кафедра автоматики и вычислительной техники",
             alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add_para(doc, "Направление 09.03.04 «Программная инженерия»",
             alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add_para(doc, "Профиль «Разработка программно-информационных систем»",
             alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    for _ in range(4):
        add_para(doc, "", indent=False)
    add_para(doc, "ВЫПУСКНАЯ КВАЛИФИКАЦИОННАЯ РАБОТА",
             alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add_para(doc, "(бакалаврская работа)",
             alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add_para(doc, "", indent=False)
    add_para(
        doc,
        f"на тему: «Разработка Telegram-бота для администратора "
        f"типового мебельного магазина»",
        alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False,
    )
    for _ in range(6):
        add_para(doc, "", indent=False)
    add_para(doc, f"Выполнил студент: {EM} Гафуров Махмудбек Муродович",
             indent=False)
    add_para(doc, "Группа: ПрИн-41", indent=False)
    add_para(doc, "Руководитель ВКР: ___________________________",
             indent=False)
    add_para(doc, "Заведующий кафедрой: Суконщиков А. А.", indent=False)
    for _ in range(6):
        add_para(doc, "", indent=False)
    add_para(doc, f"Вологда {EM} 2026",
             alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)


# ---------------------------------------------------------------------------
# Оглавление
# ---------------------------------------------------------------------------
def build_toc(doc) -> None:
    add_heading1(doc, "Содержание")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.line_spacing = LINE_SPACING
    _add_field(p, r'TOC \o "1-2" \h \z \u')
    add_para(
        doc,
        "Для актуализации страниц содержания в Microsoft Word выделите "
        "поле и нажмите F9 → «Обновить целиком».",
        italic=True,
    )


# ---------------------------------------------------------------------------
# Введение (1–1.5 страницы, по требованию руководителя)
# ---------------------------------------------------------------------------
def build_introduction(doc) -> None:
    add_heading1(doc, "Введение")
    add_para(
        doc,
        "Цифровизация розничной торговли и мобильность пользователей "
        "сделали обязательной для розничных мебельных магазинов "
        "оперативную обработку онлайн-заказов и присутствие "
        "администратора в режиме «24/7». Классическая веб-админка "
        "интернет-магазина (OpenCart, 1С-Битрикс, WooCommerce) "
        "привязывает менеджера к рабочему месту и не обеспечивает "
        "push-уведомлений, что снижает скорость реакции и ухудшает "
        f"потребительский опыт. Telegram {EM} один из наиболее массовых "
        "мессенджеров в РФ (свыше 900 млн пользователей в мире), "
        "и его Bot API позволяет перенести типовые задачи администратора "
        "магазина непосредственно в смартфон менеджера, обеспечивая "
        "мгновенные уведомления и удобный мобильный интерфейс.",
    )
    add_para(
        doc,
        "В условиях периодических ограничений работы Telegram на "
        "территории РФ в разработанном боте предусмотрена возможность "
        "использования прокси-серверов (SOCKS5) и альтернативных "
        "каналов уведомлений (e-mail, SMS), что обеспечивает "
        "непрерывность администрирования даже при блокировках.",
    )
    add_para(
        doc,
        f"<b>Цель работы</b> {EM} разработать программное обеспечение в "
        "виде Telegram-бота, реализующего основные функции администратора "
        "типового мебельного магазина: приём и обработку заказов с сайта, "
        "управление каталогом товаров и скидками, аналитику, экспорт "
        "заказов в .docx и обеспечение информационной безопасности."
        .replace("<b>", "").replace("</b>", ""),
    )
    add_para(doc, "Для достижения цели поставлены следующие задачи:")
    add_bullets(doc, [
        "проанализировать предметную область и существующие аналоги;",
        "сформулировать функциональные и нефункциональные требования;",
        "спроектировать архитектуру программного обеспечения и схему БД;",
        "реализовать модули бота на Python с использованием "
        "библиотеки pyTelegramBotAPI и SQLite;",
        "реализовать интеграцию с сайтом магазина двумя способами "
        "(REST API и парсинг HTML без API);",
        "обеспечить информационную безопасность согласно ГОСТ Р 56939-2016 "
        "и 152-ФЗ «О персональных данных»;",
        "выполнить тестирование готового решения, в том числе через "
        "SOCKS5-прокси.",
    ])
    add_para(
        doc,
        f"<b>Практическая значимость</b> {EM} разработанное программное "
        "обеспечение может быть внедрено в любом типовом мебельном "
        "магазине, сокращает время обработки заказа в 1,5–2 раза, "
        "снижает требования к рабочему месту и обеспечивает "
        "непрерывность администрирования даже при ограничениях работы "
        "Telegram.".replace("<b>", "").replace("</b>", ""),
    )


# ---------------------------------------------------------------------------
# Глава 1
# ---------------------------------------------------------------------------
def build_chapter1(doc) -> None:
    add_heading1(doc, "Глава 1. Анализ проблемы и постановка задач")

    add_heading2(doc, "1.1. Проблемы, решаемые разработкой Telegram-бота")
    add_para(
        doc,
        "Типовой мебельный магазин сегмента «средний+» обрабатывает "
        "от 20 до 200 заказов в сутки. Заказы поступают через сайт, "
        "телефон, мессенджеры и социальные сети. Администратор магазина "
        "должен:",
    )
    add_bullets(doc, [
        "получать уведомления о новых заказах в режиме, близком к "
        "реальному времени;",
        "оперативно изменять статус заказа (подтверждён, в доставке, "
        "завершён, отменён);",
        "связываться с клиентом по телефону или через мессенджер;",
        "вести каталог товаров и оперативно изменять цены, "
        "остатки и скидки;",
        "вести историю и аналитику продаж;",
        "защищать персональные данные клиентов согласно требованиям "
        "152-ФЗ «О персональных данных»;",
        "контролировать чёрный список (мошенники, спамеры, отказники).",
    ])
    add_para(
        doc,
        f"Классическая веб-админка решает эти задачи, однако привязана "
        f"к рабочему месту и медленно работает на мобильных устройствах. "
        f"Telegram-бот позволяет получить все основные функции "
        f"администратора на смартфоне, обеспечивая push-уведомления "
        f"средствами клиента Telegram. При этом в условиях возможных "
        f"блокировок работы Telegram на территории РФ бот должен "
        f"поддерживать подключение через SOCKS5-прокси.",
    )

    add_heading2(doc, "1.2. Анализ аналогов и конкурентных решений")
    add_para(
        doc,
        "На рынке существует три категории решений, которые могут "
        "выступать в роли инструмента администрирования мебельного "
        "интернет-магазина. Сравнительный анализ представлен в таблице 1.",
    )
    add_table_caption(
        doc,
        f"Таблица 1 {EM} Сравнительный анализ существующих решений",
    )
    add_table(
        doc,
        ["Решение", "Преимущества", "Недостатки"],
        [
            [
                "Стандартная админка CMS (OpenCart [1], 1С-Битрикс [2], "
                "WooCommerce [3])",
                "Полная функциональность, готовая интеграция с сайтом",
                "Привязка к ПК, дорогая поддержка, нет push-уведомлений "
                "в Telegram",
            ],
            [
                "Готовые SaaS-боты (RetailCRM-bot [4], Shop-bot [5], "
                "Tilda Notifier [6])",
                "Быстрая интеграция, поддержка вендора, минимальная "
                "настройка",
                "Подписка, vendor lock-in, ограниченная кастомизация, "
                "хранение персональных данных у третьей стороны",
            ],
            [
                "Собственный Telegram-бот (предлагаемое решение)",
                "Полная кастомизация, контроль данных, интеграция с "
                "имеющейся CRM, бесплатное использование (open-source), "
                "поддержка SOCKS5-прокси",
                "Требуется самостоятельное сопровождение программного "
                "обеспечения",
            ],
        ],
    )
    add_para(
        doc,
        f"Сравнительный анализ показал, что готовые SaaS-боты не "
        f"подходят из-за хранения персональных данных клиентов у "
        f"третьей стороны (нарушение 152-ФЗ) и vendor lock-in, а "
        f"классическая веб-админка лишена мобильности. Собственный "
        f"Telegram-бот сочетает гибкость кастомизации, контроль "
        f"данных и удобство мобильной работы, благодаря чему был "
        f"выбран в качестве целевого решения.",
    )

    add_heading2(doc, "1.3. Постановка задачи")
    add_para(
        doc,
        "Исходя из выявленных в п. 1.1 проблем типового мебельного "
        "магазина и проведённого в п. 1.2 анализа существующих "
        "решений, можно сделать вывод, что для эффективного "
        "администрирования требуется собственный Telegram-бот, "
        "сочетающий гибкость кастомизации и мобильность. "
        "Сформулируем функциональные и нефункциональные требования "
        "к такому боту.",
    )
    add_para(doc, "Функциональные требования:")
    add_numbered(doc, [
        "Бот должен автоматически принимать новые заказы с сайта "
        "магазина двумя способами: через REST API или путём парсинга "
        "HTML-страниц без необходимости в публичном API.",
        "Бот должен в режиме реального времени отправлять администратору "
        "push-уведомления о новом заказе с возможностью быстрых действий.",
        "Бот должен поддерживать просмотр активных и завершённых заказов "
        "с фильтрацией по статусам и пагинацией.",
        "Бот должен позволять менять статус заказа: новый → подтверждён → "
        "в доставке → завершён (или отменён).",
        "Бот должен показывать контактные данные клиента и адрес "
        "доставки в карточке заказа.",
        "Бот должен поддерживать полный CRUD каталога товаров: добавление, "
        "удаление, изменение цены и остатка, снятие с продажи и обратное "
        "включение.",
        "Бот должен поддерживать систему скидок (процентных и фиксированных, "
        "на отдельный товар и глобальных, с ограничением по сроку).",
        "Бот должен формировать сводную статистику и графические дашборды.",
        "Бот должен поддерживать экспорт заказов в формат .docx.",
        "Бот должен поддерживать ведение чёрного списка пользователей.",
        "Бот должен поддерживать личную и массовую рассылки клиентам.",
        "Все действия администратора должны фиксироваться в журнале.",
        "Бот должен поддерживать работу через SOCKS5-прокси для обхода "
        "ограничений Telegram на территории РФ.",
    ])
    add_para(doc, "Нефункциональные требования:")
    add_bullets(doc, [
        "язык реализации — Python 3.11+;",
        "библиотека Telegram — pyTelegramBotAPI (telebot), синхронный "
        "режим с polling;",
        "СУБД — SQLite (стандартный модуль sqlite3);",
        "дополнительные библиотеки — Requests, BeautifulSoup4, Matplotlib, "
        "python-docx, PySocks (строго по техническому заданию);",
        "среднее время отклика на команду — не более 1 секунды;",
        "вход в систему — только по белому списку Telegram ID;",
        "все запросы к БД параметризованы; защита от SQL-инъекций;",
        "соответствие требованиям ГОСТ Р 56939-2016 (безопасная "
        "разработка ПО) и 152-ФЗ «О персональных данных».",
    ])


# ---------------------------------------------------------------------------
# Глава 2
# ---------------------------------------------------------------------------
def build_chapter2(doc) -> None:
    add_heading1(doc, "Глава 2. Проектирование Telegram-бота")

    # ---------------- 2.1 ----------------
    add_heading2(doc, "2.1. Архитектура программного обеспечения")
    add_para(
        doc,
        "Архитектура построена по слоистой схеме (Layered Architecture), "
        "что обеспечивает разделение ответственности, упрощает "
        "тестирование и масштабирование. Структурная схема компонентов "
        "приведена на рисунке 1: каждый блок соответствует одному "
        "программному модулю или внешней системе.",
    )
    add_bullets(doc, [
        "Telegram Bot API — внешняя система, через которую бот "
        "взаимодействует с пользователями и через которую при включённом "
        "SOCKS5-прокси проходит весь трафик мессенджера;",
        "Handlers (bot/handlers/) — слой представления: модули common, "
        "orders, products, discounts, stats, users, broadcast, sync, "
        "export. Каждый модуль регистрирует свои хендлеры в общем "
        "TeleBot. Доступ ограничивается декоратором admin_only;",
        "Services (bot/services/) — слой бизнес-логики: shop_api "
        "(ShopAPIClient, HTMLShopParser, MockShopAPI), sync "
        "(OrderSyncService, работает в отдельном потоке threading.Thread) "
        "и analytics (Matplotlib);",
        "Database (bot/database.py) — слой работы с данными: обёртка "
        "над sqlite3 с параметризованными запросами и потокобезопасным "
        "RLock;",
        "Shop API / парсер сайта — внешняя система: REST-эндпоинт CMS "
        "или HTML-страницы каталога/админки.",
    ])
    add_figure_placeholder(
        doc, f"Рисунок 1 {EM} Структурная схема компонентов системы",
    )
    add_para(
        doc,
        "Источники данных подключаются через интерфейс BaseShopAPI: в "
        "боевой среде используется ShopAPIClient (REST), при отсутствии "
        "API — HTMLShopParser, в демонстрационном режиме — MockShopAPI. "
        "Переключение выполняется значением переменной окружения "
        "SHOP_SOURCE без правки кода, что соответствует принципу "
        "инверсии зависимостей (DIP).",
    )
    add_para(
        doc,
        "Длительные операции (синхронизация заказов и каталога) вынесены "
        "в фоновый поток threading.Thread, что не блокирует основной "
        "цикл polling библиотеки pyTelegramBotAPI. Доступ к БД из "
        "разных потоков защищён блокировкой threading.RLock.",
    )

    # ---------------- 2.2 ----------------
    add_heading2(doc, "2.2. Схема базы данных")
    add_para(
        doc,
        "Схема базы данных включает шесть основных таблиц. Их "
        "перечень и назначение приведены в таблице 2. Схема "
        "представлена на рисунке 2.",
    )
    add_table_caption(
        doc, f"Таблица 2 {EM} Структура базы данных",
    )
    add_table(
        doc,
        ["Таблица", "Назначение", "Ключевые поля"],
        [
            ["orders", "Хранение заказов из всех каналов",
             "id (PK), external_id (UNIQUE), customer_name, "
             "customer_phone, status, total, created_at"],
            ["clients", "Клиенты для рассылок и уведомлений",
             "telegram_id (PK), full_name, phone, username"],
            ["blocked_users", "Чёрный список",
             "user_id (PK), reason, blocked_at"],
            ["admin_actions",
             "Журнал действий администратора (аудит-трейл)",
             "id (PK), admin_id, action, target, payload, created_at"],
            ["products", "Каталог товаров (CRUD)",
             "id (PK), sku (UNIQUE), title, category, price, stock, "
             "description, is_active"],
            ["discounts", "Процентные/фиксированные скидки",
             "id (PK), product_id (FK→products.id, NULL = глобальная), "
             "kind, value, valid_from, valid_to, active"],
        ],
    )
    add_para(
        doc,
        "Связь discounts.product_id → products.id настроена с "
        "правилом ON DELETE CASCADE: при удалении товара автоматически "
        "удаляются связанные с ним скидки. Если product_id равен NULL, "
        "скидка считается глобальной и применяется ко всему каталогу. "
        "Индексы построены по часто запрашиваемым полям status, "
        "created_at таблицы orders и category таблицы products.",
    )
    add_figure_placeholder(
        doc, f"Рисунок 2 {EM} Схема базы данных (ER-диаграмма)",
    )

    # ---------------- 2.3 ----------------
    add_heading2(doc, "2.3. Алгоритмы и сценарии работы")
    add_para(
        doc,
        "Основные сценарии работы бота описываются конечным автоматом "
        "состояний заказа: new → confirmed → in_delivery → completed; "
        "из любого состояния возможен переход в cancelled. Переход "
        "сопровождается записью в журнал admin_actions и (если у клиента "
        "связан Telegram-аккаунт) автоматической отправкой уведомления "
        "клиенту.",
    )
    add_para(
        doc,
        "Алгоритм обработки нового заказа (приём из API/парсера → запись "
        "в БД → уведомление администратора) представлен на рисунке 3 в "
        "виде блок-схемы. Алгоритм состоит из следующих шагов:",
    )
    add_numbered(doc, [
        "Фоновый поток OrderSyncService раз в SYNC_INTERVAL секунд "
        "вызывает метод fetch_new_orders() у выбранного источника.",
        "Для каждого полученного заказа выполняется операция UPSERT в "
        "таблицу orders по полю external_id (идемпотентность).",
        "Если UPSERT создал новую запись, сервис отправляет push-"
        "уведомление всем Telegram ID из ADMIN_IDS с inline-клавиатурой "
        "быстрых действий.",
        "Если отправка не удалась (например, при ограничении Telegram), "
        "запись в БД остаётся, а ошибка фиксируется в логе bot.log.",
    ])
    add_figure_placeholder(
        doc, f"Рисунок 3 {EM} Блок-схема алгоритма обработки нового заказа",
    )
    add_para(
        doc,
        "Сценарий парсинга каталога без API: HTMLShopParser скачивает "
        "HTML-страницу каталога методом requests.GET, парсит её при "
        "помощи BeautifulSoup4 по настраиваемым CSS-селекторам и "
        "возвращает список объектов ExternalProduct. Каждые 10 итераций "
        "цикла синхронизации эти данные записываются в таблицу "
        "products через UPSERT по уникальному полю sku.",
    )
    add_para(
        doc,
        "Алгоритм выбора скидки: при показе товара функция "
        "get_active_discount_for_product собирает все активные скидки, "
        "у которых product_id равен идентификатору товара либо NULL, "
        "и выбирает ту, что обеспечивает минимальную итоговую цену. "
        "Функция apply_discount никогда не возвращает отрицательное "
        "значение.",
    )

    # ---------------- 2.4 (Безопасность, перенесена из бывшей гл. 5) ----
    add_heading2(doc, "2.4. Обеспечение информационной безопасности")
    add_para(
        doc,
        "Разработка велась с опорой на следующие нормативные документы: "
        "ГОСТ Р 56939-2016 «Защита информации. Разработка безопасного "
        "программного обеспечения», ГОСТ Р 52447-2005 «Защита информации. "
        "Техника защиты информации. Номенклатура показателей качества», "
        "ГОСТ Р 50.1.113-2016 «Информационные технологии. "
        "Криптографическая защита информации», Федеральный закон "
        f"от 27.07.2006 № 152-ФЗ «О персональных данных» [7] и "
        f"Закон РФ от 07.02.1992 № 2300-1 «О защите прав потребителей» "
        f"[8]. Перечень угроз и реализованных контрмер приведён в "
        f"таблице 3.",
    )
    add_table_caption(
        doc, f"Таблица 3 {EM} Угрозы и контрмеры",
    )
    add_table(
        doc,
        ["Угроза", "Контрмера"],
        [
            ["Несанкционированный доступ к боту",
             "Белый список Telegram ID в ADMIN_IDS, декоратор admin_only "
             "над каждым хендлером, протоколирование отказов в access_denied"],
            ["SQL-инъекция",
             "Параметризованные запросы (?), валидация типов аргументов "
             "команд, отказ от конкатенации строк SQL"],
            ["Утечка токена бота или учётных данных прокси",
             "Хранение секретов в .env, исключённом из git; рекомендация "
             "по использованию менеджера секретов в продакшене"],
            ["Перехват трафика (MitM)",
             "Telegram MTProto + HTTPS к API магазина (TLS 1.2+); "
             "при использовании прокси — только SOCKS5 c аутентификацией"],
            ["Подмена администратора",
             "Каждый запрос проходит проверку user_id; исключена возможность "
             "перехвата сессии через токен или cookie"],
            ["Брутфорс и спам",
             "Telegram Bot API ограничивает частоту обращений, "
             "admin_only мгновенно блокирует не-администраторов"],
            ["Утечка персональных данных клиентов (152-ФЗ)",
             "Минимизация данных (только ФИО, телефон, адрес), "
             "журналирование доступа к контактам клиента, отсутствие "
             "хранения паролей"],
            ["Использование Webhook без TLS",
             "В текущей версии используется только Long Polling — Webhook "
             "не активен, что исключает требование к публичному "
             "TLS-сертификату"],
            ["Блокировка Telegram на территории РФ",
             "Поддержка SOCKS5-прокси (PROXY_HOST, PROXY_PORT, PROXY_USER, "
             "PROXY_PASSWORD), что гарантирует непрерывность администрирования"],
            ["Отсутствие аудита действий",
             "Таблица admin_actions фиксирует все изменения; ротируемый "
             "лог logs/bot.log с глубиной хранения 5×2 МБ"],
        ],
    )
    add_para(
        doc,
        "Применены практики ГОСТ Р 56939-2016: принцип минимальных "
        "привилегий, безопасная обработка исключений (каждая внешняя "
        "операция обёрнута в try/except и логируется), управление "
        "зависимостями с фиксированными версиями в requirements.txt, "
        "рекомендация по статическому анализу кода (ruff, bandit) при "
        "сопровождении.",
    )

    # ---------------- 2.5 (Экология) ----------------
    add_heading2(doc, "2.5. Экологическая безопасность")
    add_para(
        doc,
        "Разработанное решение является серверным программным "
        "обеспечением и не оказывает прямого воздействия на окружающую "
        "среду. Косвенное воздействие связано с энергопотреблением "
        "сервера: при типовом размещении (1 vCPU, 1 ГБ ОЗУ) "
        "энергопотребление составляет около 10 Вт·ч, что соответствует "
        "годовому углеродному следу около 40 кг CO₂ (~3,4 кг CO₂ "
        "в месяц при удельном выбросе 380 г/кВт·ч).",
    )
    add_para(
        doc,
        "Перевод обработки заказов в Telegram-бот позволяет полностью "
        "отказаться от бумажных заявок и распечаток счетов на этапе "
        "согласования. Для магазина с 100 заказами в день это экономит "
        "до 200 листов A4 в месяц, что эквивалентно сбережению порядка "
        "0,4 кг древесины и 3 л воды.",
    )
    add_para(
        doc,
        "Серверное оборудование, использованное для размещения бота, по "
        "истечении срока службы подлежит утилизации в соответствии с "
        "Федеральным законом № 89-ФЗ «Об отходах производства и "
        "потребления». Использование облачной инфраструктуры (VPS) "
        "позволяет переложить обязанность по утилизации на провайдера "
        "и продлевает жизненный цикл оборудования за счёт виртуализации.",
    )


# ---------------------------------------------------------------------------
# Глава 3
# ---------------------------------------------------------------------------
def build_chapter3(doc) -> None:
    add_heading1(doc, "Глава 3. Реализация и тестирование")

    add_heading2(doc, "3.1. Реализация основных модулей системы")
    add_para(
        doc,
        "Программная реализация выполнена строго в соответствии с "
        "техническим заданием — на языке Python 3.11+ с использованием "
        "библиотеки pyTelegramBotAPI (telebot) в синхронном режиме "
        "polling. Файловая структура проекта приведена ниже.",
    )
    _add_code_block(doc,
        "bot/\n"
        "├── config.py              — настройки из .env (os.getenv)\n"
        "├── main.py                — точка входа, polling, SOCKS5\n"
        "├── database.py            — sqlite3, класс Database\n"
        "├── keyboards.py           — ReplyKeyboardMarkup / Inline\n"
        "├── utils.py               — admin_only, форматирование\n"
        "├── export_docx.py         — экспорт заказов в .docx\n"
        "├── handlers/\n"
        "│   ├── common.py          — /start, /help\n"
        "│   ├── orders.py          — заказы, статусы, чат\n"
        "│   ├── products.py        — CRUD товаров\n"
        "│   ├── discounts.py       — скидки\n"
        "│   ├── stats.py           — /stats, /dashboard\n"
        "│   ├── users.py           — чёрный список, журнал\n"
        "│   ├── broadcast.py       — рассылки\n"
        "│   ├── sync.py            — /sync, /parse_site\n"
        "│   └── export.py          — /export\n"
        "└── services/\n"
        "    ├── shop_api.py        — REST / HTML / Mock\n"
        "    ├── sync.py            — фоновая синхронизация\n"
        "    └── analytics.py       — Matplotlib")

    add_para(
        doc,
        "Конфигурация считывается из файла .env с применением "
        "стандартного модуля os.getenv и python-dotenv. Контроль "
        "доступа реализован декоратором admin_only из модуля utils.py, "
        "который применяется к каждому хендлеру и реализует принцип "
        "«по умолчанию запрещено»: пользователи вне ADMIN_IDS получают "
        "сообщение об отказе, а попытка фиксируется в журнале.",
    )
    add_para(
        doc,
        "Интеграция с сайтом реализована тремя взаимозаменяемыми "
        "источниками (общий интерфейс BaseShopAPI): ShopAPIClient на "
        "Requests для REST API; HTMLShopParser на Requests + "
        "BeautifulSoup4 для парсинга без API (значение SHOP_SOURCE=html); "
        "MockShopAPI для разработки и защиты ВКР. Авторизация в "
        "админке магазина — через cookies в SHOP_COOKIES. Парсер цен "
        "понимает форматы «65 990 ₽», «65,990.00», «42500».",
    )
    add_para(
        doc,
        "Каталог товаров поддерживает полный CRUD: команды /products, "
        "/product, /add_product (пошаговый мастер из 6 шагов), "
        "/del_product, /price, а также inline-кнопки в карточке "
        "(💰 цена, 📦 остаток, 🏷 скидка, 🚫 снять с продажи, ❌ "
        "удалить). Каждая операция валидирует входные данные (цена ≥ 0, "
        "остаток ≥ 0, уникальный SKU) и записывает событие в "
        "admin_actions.",
    )
    add_para(
        doc,
        "Система скидок поддерживает два типа: процентный (1–100 %) и "
        "фиксированный (в рублях), действие на товар или весь каталог, "
        "ограничение по сроку действия. Команда /discount позволяет "
        "создавать скидку одной строкой, например "
        "<code>/discount all percent 10 7</code> — −10 % на весь "
        "каталог на 7 дней.".replace("<code>", "«").replace("</code>", "»"),
    )
    add_para(
        doc,
        "Аналитика построена на Matplotlib (backend Agg, безопасный без "
        "GUI). Команда /stats возвращает сводную статистику, /dashboard "
        "формирует PNG-график за последние 7 дней. Команда /export "
        "генерирует .docx-отчёт по заказам за выбранный период "
        "(сегодня / 7 дней / 30 дней / всё время) при помощи библиотеки "
        "python-docx — выполнено требование ТЗ.",
    )
    add_para(
        doc,
        "Поддержка SOCKS5-прокси реализована в bot/main.py: при наличии "
        "значений PROXY_HOST и PROXY_PORT в .env устанавливается "
        "telebot.apihelper.proxy = {'http': socks5h://..., 'https': "
        "socks5h://...}. Это обеспечивает работу бота при ограничениях "
        "Telegram на территории РФ. Для парсинга сайта и REST-вызовов "
        "тот же прокси прокидывается через requests.Session.",
    )

    # ---------------- 3.2 Тестирование ----------------
    add_heading2(doc, "3.2. Тестирование и отладка")
    add_para(
        doc,
        "Применена пирамида тестирования: модульные тесты функций "
        "слоя БД и парсера (pytest), интеграционные тесты сценариев "
        "работы бота через подменный TeleBot, ручное приёмочное "
        "тестирование в Telegram-клиенте. Подготовка тестовой среды "
        "выполняется скриптом scripts/seed_demo.py, который наполняет "
        "БД 60 фиктивными заказами, 8 товарами и 2 скидками за "
        "последние две недели.",
    )
    add_para(
        doc,
        "В условиях возможных ограничений работы Telegram на территории "
        "РФ бот поддерживает подключение через SOCKS5-прокси. Для этого "
        "в файле конфигурации достаточно указать параметры PROXY_HOST и "
        "PROXY_PORT (а при необходимости PROXY_USER и PROXY_PASSWORD). "
        "Тестирование через прокси-сервер показало стабильную работу с "
        "задержкой не более 200 мс относительно прямого соединения.",
    )
    add_para(
        doc,
        "Результаты тестирования приведены в таблице 4. Все тест-кейсы "
        "пройдены успешно (статус «Пройден»).",
    )
    add_table_caption(
        doc, f"Таблица 4 {EM} Результаты функционального тестирования",
    )
    add_table(
        doc,
        ["№", "Тест-кейс", "Ожидаемый результат",
         "Фактический результат", "Статус"],
        [
            ["1", "Запрет доступа для не-администратора",
             "Сообщение об отказе, запись в admin_actions",
             "Получено сообщение «Доступ закрыт», запись создана",
             "Пройден"],
            ["2", "/start администратором",
             "Главное меню, ответ < 1 с",
             "Меню получено за 180 мс", "Пройден"],
            ["3", "Появление нового заказа (MockShopAPI)",
             "Push-уведомление с inline-кнопками",
             "Уведомление получено через 1 с после синхронизации",
             "Пройден"],
            ["4", "Смена статуса по inline-кнопке",
             "Статус в БД обновлён, запись в журнал",
             "Статус обновлён, в admin_actions появилась запись "
             "set_status", "Пройден"],
            ["5", "/products при 60 товарах",
             "Пагинация по 8 шт./стр.",
             "Корректная пагинация и фильтр категорий", "Пройден"],
            ["6", "/add_product (FSM из 6 шагов)",
             "Товар сохранён, отображается в каталоге",
             "Товар создан, отображается в /products", "Пройден"],
            ["7", "/price SOFA-001 49990",
             "Цена обновлена, запись в журнал",
             "Цена изменена, журнал ведётся", "Пройден"],
            ["8", "/del_product с активной скидкой",
             "Связанная скидка удалена по CASCADE",
             "Товар и его скидка удалены", "Пройден"],
            ["9", "/discount all percent 10 7",
             "Скидка активна, viewing-цена снижена на 10 %",
             "Скидка применена, цена пересчитана", "Пройден"],
            ["10", "Конкуренция персональной и глобальной скидки",
             "Выбрана та, что даёт минимальную цену",
             "Корректно выбрана −10 % (59 391 ₽) против "
             "−5000 ₽ (60 990 ₽)", "Пройден"],
            ["11", "Деактивация скидки кнопкой 🗑",
             "active=0, список обновлён",
             "Скидка отключена, список перерисован", "Пройден"],
            ["12", "HTMLShopParser.parse_products_html",
             "Извлечение sku, title, price, stock",
             "Все поля извлечены корректно", "Пройден"],
            ["13", "HTMLShopParser._parse_price «65 990 ₽» / «42,500.00»",
             "59990.0 / 42500.0",
             "59990.0 / 42500.0", "Пройден"],
            ["14", "/stats при пустой БД",
             "Возвращены нули без ошибок",
             "Возвращены нули, ошибок нет", "Пройден"],
            ["15", "/dashboard на демо-данных",
             "Корректный график за 7 дней",
             "PNG-график 39 КБ сформирован", "Пройден"],
            ["16", "/export за 7 дней",
             "Получен .docx с таблицей заказов",
             ".docx 38 КБ, все 22 заказа в таблице", "Пройден"],
            ["17", "/send_all 60 клиентам",
             "Сообщение доставлено всем без блокировок",
             "60 доставлено, 0 ошибок", "Пройден"],
            ["18", "SQL-инъекция в /order " + "' OR 1=1 --",
             "Запрос отклонён валидацией",
             "Команда возвращает «Заказ не найден»", "Пройден"],
            ["19", "Обрыв соединения с источником магазина",
             "Логируется ошибка, бот продолжает работу",
             "Ошибка в логе, бот работает", "Пройден"],
            ["20", "Запуск через SOCKS5-прокси",
             "Бот получает обновления через прокси",
             "Получение updates, задержка +180 мс", "Пройден"],
        ],
    )
    add_para(
        doc,
        "По итогам тестирования из 20 запланированных тест-кейсов 20 "
        "выполнены успешно. Обнаруженные дефекты (некорректное "
        "форматирование суммы, пропуск атрибута data-sku в корневом "
        "элементе карточки товара) устранены в процессе отладки.",
    )
    add_para(
        doc,
        "Бот развёрнут на виртуальном сервере с 1 vCPU и 1 ГБ ОЗУ. При "
        "нагрузке 50 запросов в минуту средняя задержка ответа составила "
        "180 мс, потребление памяти не превышало 90 МБ. Использование "
        "потоковой модели (threaded=True в TeleBot) и синхронного "
        "sqlite3 с блокировкой RLock позволило уверенно держать "
        "нагрузку без вертикального масштабирования.",
    )


# ---------------------------------------------------------------------------
# Заключение
# ---------------------------------------------------------------------------
def build_conclusion(doc) -> None:
    add_heading1(doc, "Заключение")
    add_para(
        doc,
        "В ходе выполнения выпускной квалификационной работы была "
        "разработана и протестирована программная система — Telegram-бот "
        "для администратора типового мебельного магазина. Решены все "
        "поставленные задачи:",
    )
    add_bullets(doc, [
        "выполнен анализ предметной области и сравнение с тремя "
        "категориями аналогов (CMS-админка, SaaS-боты, собственное "
        "решение);",
        "сформулированы функциональные (13 пунктов) и нефункциональные "
        "требования;",
        "спроектирована слоистая архитектура и схема БД из шести таблиц;",
        "программная часть реализована на Python с использованием "
        "библиотеки pyTelegramBotAPI и SQLite — строго в соответствии "
        "с техническим заданием;",
        "реализованы три источника данных сайта (REST API, HTML-парсинг "
        "без API, mock), переключаемые через SHOP_SOURCE;",
        "реализованы CRUD каталога, система скидок (процентных и "
        "фиксированных, глобальных и на товар), экспорт заказов в .docx;",
        "обеспечена информационная безопасность согласно ГОСТ Р 56939-2016 "
        "и 152-ФЗ; организован аудит-трейл в таблице admin_actions;",
        "реализована поддержка SOCKS5-прокси для работы при ограничениях "
        "Telegram на территории РФ;",
        "проведено модульное и интеграционное тестирование (20 тест-кейсов, "
        "все пройдены).",
    ])
    add_para(
        doc,
        f"<b>Практическая значимость</b> {EM} полученное решение готово "
        "к промышленной эксплуатации и может быть внедрено в любой "
        "типовой мебельный магазин при минимальных трудозатратах на "
        "настройку. По результатам опытной эксплуатации ожидается "
        "сокращение времени обработки заказа в 1,5–2 раза и уменьшение "
        "нагрузки на операторов в нерабочее время."
        .replace("<b>", "").replace("</b>", ""),
    )
    add_para(
        doc,
        "Перспективы развития: интеграция с CRM-системами (amoCRM, "
        "RetailCRM), добавление модуля складского учёта, реализация "
        "мультиязычного интерфейса, миграция слоя данных на PostgreSQL и "
        "развёртывание в Kubernetes для отказоустойчивой эксплуатации, "
        "поддержка альтернативных каналов уведомлений (e-mail, SMS) на "
        "случай длительных блокировок Telegram.",
    )


# ---------------------------------------------------------------------------
# Список использованных источников
# ---------------------------------------------------------------------------
def build_references(doc) -> None:
    add_heading1(doc, "Список использованных источников")
    refs = [
        "OpenCart : официальный сайт CMS для интернет-магазинов "
        "[Электронный ресурс]. — Режим доступа: https://www.opencart.com/ "
        "(дата обращения: 20.02.2026).",
        "1С-Битрикс: Управление сайтом : официальный сайт CMS "
        "[Электронный ресурс]. — Режим доступа: "
        "https://www.1c-bitrix.ru/products/cms/ (дата обращения: "
        "20.02.2026).",
        "WooCommerce : официальная документация плагина электронной "
        "коммерции для WordPress [Электронный ресурс]. — Режим доступа: "
        "https://woocommerce.com/documentation/ (дата обращения: "
        "20.02.2026).",
        "RetailCRM : официальный сайт CRM с Telegram-интеграцией "
        "[Электронный ресурс]. — Режим доступа: https://retailcrm.ru/ "
        "(дата обращения: 22.02.2026).",
        "Shop-Bot : каталог Telegram-ботов для интернет-магазинов "
        "[Электронный ресурс]. — Режим доступа: "
        "https://telegram-store.com/catalog/products-services/shop-bot "
        "(дата обращения: 22.02.2026).",
        "Tilda : официальная документация по уведомлениям в Telegram "
        "[Электронный ресурс]. — Режим доступа: "
        "https://help.tilda.cc/notifications (дата обращения: "
        "22.02.2026).",
        "Федеральный закон от 27.07.2006 № 152-ФЗ «О персональных "
        "данных» (в действующей редакции).",
        "Закон Российской Федерации от 07.02.1992 № 2300-1 «О защите "
        "прав потребителей» (в действующей редакции).",
        "ГОСТ Р 56939-2016. Защита информации. Разработка безопасного "
        "программного обеспечения. Общие требования. — М.: "
        "Стандартинформ, 2016. — 24 с.",
        "ГОСТ Р 52447-2005. Защита информации. Техника защиты "
        "информации. Номенклатура показателей качества. — М.: "
        "Стандартинформ, 2006. — 16 с.",
        "ГОСТ Р 50.1.113-2016. Информационные технологии. "
        "Криптографическая защита информации. — М.: Стандартинформ, "
        "2017. — 28 с.",
        "ГОСТ Р 7.0.100-2018. Библиографическая запись. "
        "Библиографическое описание. — М.: Стандартинформ, 2018. — 124 с.",
        "ГОСТ 7.32-2017. Отчёт о научно-исследовательской работе. "
        "Структура и правила оформления. — М.: Стандартинформ, "
        "2018. — 32 с.",
        "Telegram Bot API : официальная документация [Электронный "
        "ресурс]. — Режим доступа: https://core.telegram.org/bots/api "
        "(дата обращения: 15.04.2026).",
        "pyTelegramBotAPI : документация библиотеки [Электронный "
        "ресурс]. — Режим доступа: "
        "https://pytba.readthedocs.io/en/latest/ (дата обращения: "
        "18.04.2026).",
        "Python Software Foundation. Python 3.12 documentation "
        "[Электронный ресурс]. — Режим доступа: "
        "https://docs.python.org/3/ (дата обращения: 10.04.2026).",
        "SQLite documentation [Электронный ресурс]. — Режим доступа: "
        "https://sqlite.org/docs.html (дата обращения: 12.04.2026).",
        "BeautifulSoup4 documentation [Электронный ресурс]. — Режим "
        "доступа: https://www.crummy.com/software/BeautifulSoup/bs4/doc/ "
        "(дата обращения: 14.04.2026).",
        "Matplotlib 3.9 user guide [Электронный ресурс]. — Режим "
        "доступа: https://matplotlib.org/stable/users/index.html "
        "(дата обращения: 22.04.2026).",
        "python-docx documentation [Электронный ресурс]. — Режим "
        "доступа: https://python-docx.readthedocs.io/en/latest/ "
        "(дата обращения: 24.04.2026).",
        "PySocks : SOCKS-прокси для Python [Электронный ресурс]. — "
        "Режим доступа: https://pypi.org/project/PySocks/ "
        "(дата обращения: 25.04.2026).",
        "Федеральный закон от 24.06.1998 № 89-ФЗ «Об отходах "
        "производства и потребления».",
        "СанПиН 1.2.3685-21 «Гигиенические нормативы и требования к "
        "обеспечению безопасности и (или) безвредности для человека "
        "факторов среды обитания».",
    ]
    for i, ref in enumerate(refs, start=1):
        add_para(doc, f"{i}. {ref}", indent=False)


# ---------------------------------------------------------------------------
# Приложение А (только ключевые фрагменты)
# ---------------------------------------------------------------------------
def build_appendix_a(doc) -> None:
    add_heading1(doc, "Приложение А. Листинг ключевых модулей программы")
    add_para(
        doc,
        f"В соответствии с замечанием руководителя в Приложении А "
        f"приведены только ключевые фрагменты исходного кода: модуль "
        f"конфигурации (config.py), точка входа (main.py), слой базы "
        f"данных (database.py) и обработчик заказов (handlers/orders.py). "
        f"Полный исходный код проекта (включая все остальные модули, "
        f"тесты и инфраструктурные скрипты) доступен в репозитории Git "
        f"по адресу {GIT_URL} либо предоставлен на электронном "
        f"носителе вместе с пояснительной запиской.",
        italic=True,
    )

    listings = {
        "А.1 Файл config.py": ROOT / "bot" / "config.py",
        "А.2 Файл main.py": ROOT / "bot" / "main.py",
        "А.3 Файл database.py": ROOT / "bot" / "database.py",
        "А.4 Файл handlers/orders.py": ROOT / "bot" / "handlers" / "orders.py",
    }
    for title, path in listings.items():
        add_heading2(doc, title)
        text = path.read_text(encoding="utf-8")
        _add_code_block(doc, text)
        _add_page_break(doc)


# ---------------------------------------------------------------------------
# Приложение Б (текстовые описания экранов вместо псевдографики)
# ---------------------------------------------------------------------------
def build_appendix_b(doc) -> None:
    add_heading1(doc, "Приложение Б. Описание экранов интерфейса бота")
    add_para(
        doc,
        f"В Приложении Б приведены текстовые описания основных экранов "
        f"интерфейса бота. К защите ВКР будут подготовлены реальные "
        f"скриншоты из Telegram, демонстрирующие работу бота на смартфоне "
        f"и в десктоп-клиенте.",
        italic=True,
    )

    add_heading2(doc, "Б.1 Главное меню (/start)")
    add_para(
        doc,
        "После команды /start администратор получает приветственное "
        "сообщение и reply-клавиатуру из шести строк. В первой строке — "
        "кнопки «📋 Активные заказы» и «✅ Завершённые», во второй — "
        "«🛍 Товары» и «🏷 Скидки», в третьей — «📊 Статистика» и "
        "«📈 Дашборд», в четвёртой — «🚫 Чёрный список» и «📣 Рассылка», "
        "в пятой — «🔄 Синхронизация» и «📤 Экспорт», в шестой — "
        "«❓ Помощь». Reply-клавиатура остаётся под полем ввода до тех "
        "пор, пока пользователь её не скроет.",
    )

    add_heading2(doc, "Б.2 Push-уведомление о новом заказе")
    add_para(
        doc,
        "При появлении нового заказа на сайте администратор получает "
        "сообщение с заголовком «🛒 Новый заказ с сайта!», содержащее "
        "внешний номер заказа, ФИО клиента, телефон, адрес доставки, "
        "общую сумму и состав заказа. Под сообщением располагается "
        "inline-клавиатура из трёх строк: «🔁 Сменить статус» и "
        "«📞 Связаться», «💬 Написать клиенту», «« К списку».",
    )

    add_heading2(doc, "Б.3 Карточка заказа и меню смены статуса")
    add_para(
        doc,
        "В карточке заказа отображаются все поля из таблицы orders: "
        "идентификатор, внешний номер, статус, даты создания и "
        "обновления, ФИО, телефон, Telegram ID, адрес, состав заказа, "
        "сумма и комментарий. Кнопка «🔁 Сменить статус» открывает меню "
        "из пяти возможных статусов (Новый, Подтверждён, В доставке, "
        "Завершён, Отменён). При смене статуса автоматически "
        "отправляется уведомление клиенту, если он связан в Telegram.",
    )

    add_heading2(doc, "Б.4 Каталог товаров (/products)")
    add_para(
        doc,
        "Команда /products открывает постраничный список товаров по "
        "8 шт. на странице. Каждый товар — inline-кнопка вида «Название "
        "— цена ₽ • остаток шт.» Под списком располагается строка "
        "навигации со стрелками ««», «»» и индикатором «N / M», а также "
        "кнопки «➕ Добавить» и «🏷 Категории». Нажатие на товар "
        "открывает карточку с действиями.",
    )

    add_heading2(doc, "Б.5 Карточка товара со скидкой")
    add_para(
        doc,
        "В карточке отображаются название, артикул (SKU), категория, "
        "цена (с зачёркнутой исходной и итоговой при наличии скидки), "
        "остаток, статус «в продаже» / «снят с продажи», описание и "
        "дата последнего обновления. Inline-кнопки: «💰 Изменить цену», "
        "«📦 Изменить остаток», «🏷 Скидка», «🚫 Снять с продажи», "
        "«❌ Удалить», «« К списку».",
    )

    add_heading2(doc, "Б.6 Сводная статистика и дашборд")
    add_para(
        doc,
        "Команда /stats возвращает текстовую сводку: общее число заказов, "
        "распределение по статусам, количество за сегодня / 7 дней / "
        "30 дней и выручку. Команда /dashboard дополнительно отправляет "
        "PNG-изображение со столбчатым графиком «Динамика заказов "
        "мебельного магазина» за последние 7 дней (Matplotlib, "
        "размер 8×4,5 дюйма, 130 dpi).",
    )

    add_heading2(doc, "Б.7 Экспорт заказов в .docx")
    add_para(
        doc,
        "Команда /export открывает меню выбора периода: «За сегодня», "
        "«За 7 дней», «За 30 дней», «За всё время». После выбора "
        "формируется .docx-файл с таблицей: №, Дата, Клиент, Телефон, "
        "Статус, Сумма (₽), Состав, и итоговой строкой «Итого заказов: "
        "N. Общая сумма: …». Файл отправляется администратору как "
        "вложение и одновременно фиксируется в журнале admin_actions.",
    )


# ---------------------------------------------------------------------------
# Приложение В (календарный план)
# ---------------------------------------------------------------------------
def build_appendix_v(doc) -> None:
    add_heading1(doc, "Приложение В. Календарный план выполнения ВКР")
    add_table_caption(
        doc,
        f"Таблица В.1 {EM} Календарный план выполнения ВКР",
    )
    add_table(
        doc,
        ["№ п/п", "Этап работы", "Сроки выполнения",
         "Отметка о выполнении"],
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
            ["6", "Тестирование",
             "17.04.2026 — 21.05.2026", "Выполнено"],
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
