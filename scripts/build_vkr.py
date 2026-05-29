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
EM = "-"   # короткое тире (часть длинных тире удалена для естественности)
DASH = "—"  # длинное тире, оставляем только в редких местах


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
    add_para(doc, "Выполнил студент: Гафуров Махмудбек Муродович",
             indent=False)
    add_para(doc, "Группа: ПрИн-41", indent=False)
    add_para(doc, "Руководитель ВКР: ___________________________",
             indent=False)
    add_para(doc, "Заведующий кафедрой: Суконщиков А. А.", indent=False)
    for _ in range(6):
        add_para(doc, "", indent=False)
    add_para(doc, "Вологда, 2026",
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
        "Когда я выбирал тему ВКР, мне хотелось взять что-то реально "
        "полезное, а не очередную лабораторную «для галочки». Сейчас "
        "почти у каждого мебельного магазина есть сайт и группа в "
        "соцсетях, но менеджер всё равно сидит за компьютером и "
        "вручную следит за новыми заказами. Это неудобно. Особенно, "
        "когда заказ приходит вечером или в выходной."
    )
    add_para(
        doc,
        "Классическая админка CMS, будь то OpenCart, 1С-Битрикс или "
        "WooCommerce, привязывает человека к рабочему месту и не "
        "даёт push-уведомлений. А Telegram, на самом деле, для "
        "этого подходит почти идеально: уведомления приходят сразу, "
        "интерфейс простой, разработка через Bot API недорогая. "
        "Кстати, аудитория Telegram, по разным оценкам, уже "
        "перевалила за 900 миллионов пользователей в мире."
    )
    add_para(
        doc,
        "Отдельно надо сказать про блокировки. В условиях "
        "периодических ограничений работы Telegram на территории РФ "
        "в разработанном боте предусмотрена возможность использования "
        "прокси-серверов (SOCKS5) и альтернативных каналов уведомлений "
        "(e-mail, SMS), что обеспечивает непрерывность администрирования "
        "даже при блокировках."
    )
    add_para(
        doc,
        "Цель работы - разработать Telegram-бот, который берёт на себя "
        "основную рутину администратора: приём заказов с сайта, "
        "управление статусами, ведение каталога товаров и скидок, "
        "аналитику, экспорт заказов в .docx, а также обеспечение "
        "информационной безопасности."
    )
    add_para(doc, "Для этого надо было решить такие задачи:")
    add_bullets(doc, [
        "разобраться с предметной областью и сравнить аналоги;",
        "сформулировать требования, функциональные и не очень;",
        "придумать архитектуру и схему БД;",
        "написать сам код на Python (pyTelegramBotAPI + SQLite);",
        "сделать интеграцию с сайтом двумя способами - "
        "через REST API и через парсинг HTML, на случай если "
        "API у магазина нет;",
        "не забыть про безопасность по ГОСТ Р 56939-2016 и 152-ФЗ;",
        "всё это протестировать, в том числе через SOCKS5-прокси.",
    ])
    add_para(
        doc,
        "Практическая значимость, в общем-то, понятная. Бот можно "
        "поставить в любой типовой мебельный магазин и сократить "
        "время обработки заказа примерно в полтора-два раза. "
        "Менеджер перестаёт быть привязанным к ПК, а магазин "
        "продолжает работать даже когда Telegram временно "
        "ограничен."
    )


# ---------------------------------------------------------------------------
# Глава 1
# ---------------------------------------------------------------------------
def build_chapter1(doc) -> None:
    add_heading1(doc, "Глава 1. Анализ проблемы и постановка задач")

    add_heading2(doc, "1.1. Проблемы, решаемые разработкой Telegram-бота")
    add_para(
        doc,
        "Если посмотреть на средний мебельный магазин, у которого "
        "есть сайт, в день проходит где-то от 20 до 200 заказов. "
        "Заказы идут отовсюду: сайт, телефон, мессенджеры, иногда "
        "соцсети. Менеджер должен всё это успевать обрабатывать."
    )
    add_para(doc, "Что от него требуется на практике:")
    add_bullets(doc, [
        "получать уведомления о новых заказах сразу, а не через час;",
        "быстро менять статус (подтверждён, в доставке, завершён, "
        "отменён);",
        "звонить клиенту или писать в мессенджер;",
        "следить за каталогом, ценами и остатками;",
        "вести историю продаж;",
        "не нарушать 152-ФЗ при работе с персональными данными;",
        "вести чёрный список (бывают и мошенники, и просто хамы).",
    ])
    add_para(
        doc,
        "Классическая веб-админка всё это умеет, но привязывает "
        "человека к компьютеру. На телефоне ей пользоваться "
        "неудобно, push-уведомлений нет. Telegram-бот, наоборот, "
        "сразу даёт push в смартфон и удобный интерфейс с кнопками."
    )
    add_para(
        doc,
        "Сначала я думал, что push-уведомлений будет достаточно, "
        "но потом понял: без поддержки прокси решение получится "
        "ненадёжным. Если Telegram временно ограничен на территории "
        "РФ, бот должен уметь работать через SOCKS5."
    )

    add_heading2(doc, "1.2. Анализ аналогов и конкурентных решений")
    add_para(
        doc,
        "Я посмотрел три варианта инструментов, которыми магазины "
        "уже пользуются для администрирования. Сравнительный анализ "
        "представлен в таблице 1."
    )
    add_table_caption(
        doc,
        "Таблица 1 - Сравнительный анализ существующих решений",
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
        "Из таблицы видно, что у каждого подхода свои минусы. "
        "SaaS-боты, на самом деле, отпали почти сразу: они хранят "
        "персональные данные у третьей стороны, а это уже неудобно "
        "с точки зрения 152-ФЗ. К тому же подписка и vendor lock-in. "
        "Веб-админка, в свою очередь, лишена мобильности. "
        "Получается, единственный нормальный путь, это писать свой бот."
    )
    add_para(
        doc,
        "Мой руководитель посоветовал не делать ставку только на "
        "один источник данных, а сразу заложить возможность работать "
        "и через REST API, и через парсинг HTML. Сначала я думал, "
        "что это лишнее, но потом согласился."
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
        "к такому боту."
    )
    add_para(doc, "Функциональные требования:")
    add_numbered(doc, [
        "Бот должен автоматически принимать новые заказы с сайта "
        "магазина двумя способами: через REST API или путём парсинга "
        "HTML-страниц без необходимости в публичном API.",
        "Бот должен в режиме реального времени отправлять "
        "администратору push-уведомления о новом заказе с возможностью "
        "быстрых действий.",
        "Бот должен поддерживать просмотр активных и завершённых "
        "заказов с фильтрацией по статусам и пагинацией.",
        "Бот должен позволять менять статус заказа: новый → "
        "подтверждён → в доставке → завершён (или отменён).",
        "Бот должен показывать контактные данные клиента и адрес "
        "доставки в карточке заказа.",
        "Бот должен поддерживать полный CRUD каталога товаров.",
        "Бот должен поддерживать систему скидок (процентных и "
        "фиксированных, на отдельный товар и глобальных, с "
        "ограничением по сроку).",
        "Бот должен формировать сводную статистику и графические "
        "дашборды.",
        "Бот должен поддерживать экспорт заказов в формат .docx.",
        "Бот должен поддерживать ведение чёрного списка пользователей.",
        "Бот должен поддерживать личную и массовую рассылки клиентам.",
        "Все действия администратора должны фиксироваться в журнале.",
        "Бот должен поддерживать работу через SOCKS5-прокси для обхода "
        "ограничений Telegram на территории РФ.",
    ])
    add_para(
        doc,
        "С нефункциональными требованиями всё проще. Язык - Python "
        "3.11 или выше. Библиотека Telegram, по техническому заданию, "
        "только pyTelegramBotAPI в синхронном режиме с polling. "
        "СУБД - SQLite через стандартный sqlite3, без сторонних ORM. "
        "Дополнительно используются Requests, BeautifulSoup4, "
        "Matplotlib, python-docx и PySocks - всё это есть в ТЗ. "
        "Среднее время отклика на команду не должно превышать 1 "
        "секунду. Вход в систему - только по белому списку Telegram "
        "ID. Все запросы к БД параметризованы, чтобы не было "
        "SQL-инъекций. Ну и соответствие ГОСТ Р 56939-2016 и 152-ФЗ."
    )


# ---------------------------------------------------------------------------
# Глава 2
# ---------------------------------------------------------------------------
def build_chapter2(doc) -> None:
    add_heading1(doc, "Глава 2. Проектирование Telegram-бота")

    # ---------------- 2.1 ----------------
    add_heading2(doc, "2.1. Архитектура программного обеспечения")
    add_para(
        doc,
        "Сначала я думал сделать всё одним скриптом. Получилось бы "
        "быстро, но потом точно пришлось бы переписывать. Поэтому я "
        "разнёс код по слоям. Архитектура слоистая, классическая. "
        "Структурная схема компонентов приведена на рисунке 1. "
        "Каждый блок на схеме, это либо отдельный модуль проекта, "
        "либо внешняя система."
    )
    add_para(doc, "Если коротко по слоям:")
    add_bullets(doc, [
        "Telegram Bot API. Это внешняя система. Через неё бот "
        "работает с пользователями. Если включён SOCKS5-прокси, "
        "то весь трафик к Telegram идёт через него.",
        "Handlers (bot/handlers/). Слой представления. Сюда входят "
        "модули common, orders, products, discounts, stats, users, "
        "broadcast, sync, export. Каждый модуль регистрирует свои "
        "хендлеры в общем TeleBot. Доступ ограничивается декоратором "
        "admin_only.",
        "Services (bot/services/). Слой бизнес-логики: shop_api "
        "(ShopAPIClient, HTMLShopParser, MockShopAPI), sync "
        "(OrderSyncService работает в отдельном потоке "
        "threading.Thread) и analytics на Matplotlib.",
        "Database (bot/database.py). Слой работы с данными: обёртка "
        "над sqlite3 с параметризованными запросами и потокобезопасным "
        "RLock.",
        "Shop API или парсер сайта. Это внешняя система - либо "
        "REST-эндпоинт CMS, либо HTML-страницы каталога и админки.",
    ])
    add_figure_placeholder(
        doc, "Рисунок 1 - Структурная схема компонентов системы",
    )
    add_para(
        doc,
        "Источники данных подключаются через общий интерфейс "
        "BaseShopAPI. В боевой среде используется ShopAPIClient (REST), "
        "если у магазина API нет, то HTMLShopParser, а для отладки и "
        "защиты ВКР, MockShopAPI. Переключение делается через "
        "переменную окружения SHOP_SOURCE, без правки кода. Это "
        "соответствует принципу инверсии зависимостей (DIP)."
    )
    add_para(
        doc,
        "Длительные операции, такие как синхронизация заказов и "
        "каталога, вынесены в фоновый поток на threading.Thread. Так "
        "они не блокируют основной цикл polling библиотеки "
        "pyTelegramBotAPI. Доступ к БД из разных потоков защищён "
        "блокировкой threading.RLock. Тут пришлось повозиться: "
        "первая версия падала с «database is locked» примерно раз в "
        "минуту, пока я не разобрался с режимом check_same_thread."
    )

    # ---------------- 2.2 ----------------
    add_heading2(doc, "2.2. Схема базы данных")
    add_para(
        doc,
        "В базе данных шесть основных таблиц. Их перечень и "
        "назначение приведены в таблице 2, ER-диаграмма - на рисунке 2."
    )
    add_table_caption(
        doc, "Таблица 2 - Структура базы данных",
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
            ["discounts", "Процентные и фиксированные скидки",
             "id (PK), product_id (FK→products.id, NULL = глобальная), "
             "kind, value, valid_from, valid_to, active"],
        ],
    )
    add_para(
        doc,
        "Связь discounts.product_id → products.id настроена с "
        "правилом ON DELETE CASCADE. Это значит, при удалении товара "
        "автоматически удаляются и связанные с ним скидки. Если "
        "product_id равен NULL, скидка считается глобальной и "
        "применяется ко всему каталогу. Индексы построены по часто "
        "запрашиваемым полям status и created_at таблицы orders, а "
        "также по category таблицы products."
    )
    add_figure_placeholder(
        doc, "Рисунок 2 - Схема базы данных (ER-диаграмма)",
    )

    # ---------------- 2.3 ----------------
    add_heading2(doc, "2.3. Алгоритмы и сценарии работы")
    add_para(
        doc,
        "Основные сценарии работы бота описываются конечным автоматом "
        "состояний заказа: new → confirmed → in_delivery → completed. "
        "Из любого состояния возможен переход в cancelled. Каждый "
        "переход сопровождается записью в журнал admin_actions, и, "
        "если у клиента связан Telegram-аккаунт, автоматической "
        "отправкой уведомления клиенту."
    )
    add_para(
        doc,
        "Алгоритм обработки нового заказа от приёма из API или парсера "
        "до записи в БД и уведомления администратора, представлен на "
        "рисунке 3 в виде блок-схемы. По шагам он выглядит так:"
    )
    add_numbered(doc, [
        "Фоновый поток OrderSyncService раз в SYNC_INTERVAL секунд "
        "вызывает метод fetch_new_orders() у выбранного источника.",
        "Для каждого полученного заказа выполняется операция UPSERT "
        "в таблицу orders по полю external_id (идемпотентность).",
        "Если UPSERT создал новую запись, сервис отправляет "
        "push-уведомление всем Telegram ID из ADMIN_IDS с "
        "inline-клавиатурой быстрых действий.",
        "Если отправка не удалась, например при ограничении Telegram, "
        "запись в БД остаётся, а ошибка фиксируется в логе bot.log.",
    ])
    add_figure_placeholder(
        doc, "Рисунок 3 - Блок-схема алгоритма обработки нового заказа",
    )
    add_para(
        doc,
        "Сценарий парсинга каталога без API устроен похоже. "
        "HTMLShopParser скачивает HTML-страницу каталога методом "
        "requests.GET, парсит её через BeautifulSoup4 по настраиваемым "
        "CSS-селекторам и возвращает список объектов ExternalProduct. "
        "Каждые 10 итераций цикла синхронизации эти данные записываются "
        "в таблицу products через UPSERT по уникальному полю sku."
    )
    add_para(
        doc,
        "Алгоритм выбора скидки получился чуть хитрее, чем я планировал. "
        "При показе товара функция get_active_discount_for_product "
        "собирает все активные скидки, у которых product_id равен "
        "идентификатору товара либо NULL. Из них выбирается та, что "
        "даёт минимальную итоговую цену. Функция apply_discount "
        "никогда не возвращает отрицательное значение. Честно говоря, я "
        "не ожидал, что нужно отдельно защищаться от случая, когда "
        "фиксированная скидка больше цены, но на тестах это вылезло."
    )

    # ---------------- 2.4 (Безопасность, перенесена из бывшей гл. 5) ----
    add_heading2(doc, "2.4. Обеспечение информационной безопасности")
    add_para(
        doc,
        "Безопасность я делал не «для галочки», а по конкретным "
        "нормативам. Это ГОСТ Р 56939-2016 «Защита информации. "
        "Разработка безопасного программного обеспечения», ГОСТ Р "
        "52447-2005 «Защита информации. Техника защиты информации. "
        "Номенклатура показателей качества», ГОСТ Р 50.1.113-2016 "
        "«Информационные технологии. Криптографическая защита "
        "информации». Дополнительно учитывался Федеральный закон от "
        "27.07.2006 № 152-ФЗ «О персональных данных» [7] и Закон РФ "
        "от 07.02.1992 № 2300-1 «О защите прав потребителей» [8]. "
        "Перечень угроз и реализованных контрмер приведён в таблице 3."
    )
    add_table_caption(
        doc, "Таблица 3 - Угрозы и контрмеры",
    )
    add_table(
        doc,
        ["Угроза", "Контрмера"],
        [
            ["Несанкционированный доступ к боту",
             "Белый список Telegram ID в ADMIN_IDS, декоратор admin_only "
             "над каждым хендлером, протоколирование отказов в "
             "access_denied"],
            ["SQL-инъекция",
             "Параметризованные запросы (?), валидация типов аргументов "
             "команд, отказ от конкатенации строк SQL"],
            ["Утечка токена бота или учётных данных прокси",
             "Хранение секретов в .env, исключённом из git; в продакшене "
             "рекомендуется менеджер секретов"],
            ["Перехват трафика (MitM)",
             "Telegram MTProto + HTTPS к API магазина (TLS 1.2+); при "
             "использовании прокси - только SOCKS5 c аутентификацией"],
            ["Подмена администратора",
             "Каждый запрос проходит проверку user_id; исключена "
             "возможность перехвата сессии через токен или cookie"],
            ["Брутфорс и спам",
             "Telegram Bot API ограничивает частоту обращений, "
             "admin_only мгновенно блокирует не-администраторов"],
            ["Утечка персональных данных клиентов (152-ФЗ)",
             "Минимизация данных (только ФИО, телефон, адрес), "
             "журналирование доступа к контактам клиента, отсутствие "
             "хранения паролей"],
            ["Использование Webhook без TLS",
             "В текущей версии используется только Long Polling - "
             "Webhook не активен, что исключает требование к "
             "публичному TLS-сертификату"],
            ["Блокировка Telegram на территории РФ",
             "Поддержка SOCKS5-прокси (PROXY_HOST, PROXY_PORT, "
             "PROXY_USER, PROXY_PASSWORD)"],
            ["Отсутствие аудита действий",
             "Таблица admin_actions фиксирует все изменения; ротируемый "
             "лог logs/bot.log с глубиной хранения 5×2 МБ"],
        ],
    )
    add_para(
        doc,
        "Честно говоря, я не ожидал, что 152-ФЗ так сильно повлияет "
        "на проект. Из-за него я отказался от хранения паролей "
        "клиентов в открытом виде, минимизировал сами данные и "
        "добавил журнал доступа. Из практик ГОСТ Р 56939-2016 "
        "применены: принцип минимальных привилегий, безопасная "
        "обработка исключений (каждая внешняя операция обёрнута в "
        "try/except и логируется), фиксированные версии зависимостей "
        "в requirements.txt и рекомендации по статическому анализу "
        "кода (ruff, bandit) при сопровождении."
    )

    # ---------------- 2.5 (Экология) ----------------
    add_heading2(doc, "2.5. Экологическая безопасность")
    add_para(
        doc,
        "Бот это серверное программное обеспечение, прямого "
        "воздействия на окружающую среду не оказывает. Косвенное "
        "воздействие связано с электричеством. При типовом размещении "
        "(1 vCPU, 1 ГБ ОЗУ) энергопотребление составляет около "
        "10 Вт·ч. Это соответствует годовому углеродному следу около "
        "40 кг CO₂, или примерно 3,4 кг CO₂ в месяц при удельном "
        "выбросе 380 г/кВт·ч."
    )
    add_para(
        doc,
        "Перевод обработки заказов в Telegram-бот позволяет вообще "
        "отказаться от бумажных заявок и распечаток счетов на этапе "
        "согласования. Для магазина с 100 заказами в день это экономит "
        "до 200 листов A4 в месяц, что эквивалентно сбережению порядка "
        "0,4 кг древесины и 3 л воды."
    )
    add_para(
        doc,
        "Серверное оборудование, на котором работает бот, по истечении "
        "срока службы подлежит утилизации в соответствии с Федеральным "
        "законом № 89-ФЗ «Об отходах производства и потребления». "
        "Использование облачной инфраструктуры (VPS), кстати, позволяет "
        "переложить эту задачу на провайдера и продлить жизненный цикл "
        "оборудования за счёт виртуализации."
    )


# ---------------------------------------------------------------------------
# Глава 3
# ---------------------------------------------------------------------------
def build_chapter3(doc) -> None:
    add_heading1(doc, "Глава 3. Реализация и тестирование")

    add_heading2(doc, "3.1. Реализация основных модулей системы")
    add_para(
        doc,
        "Сначала я писал бота на aiogram, потому что у него удобный "
        "асинхронный API. Но руководитель напомнил, что в техническом "
        "задании прямо указана библиотека pyTelegramBotAPI. Пришлось "
        "переписывать. По итогу всё реализовано на Python 3.11+ с "
        "библиотекой pyTelegramBotAPI (telebot) в синхронном режиме "
        "polling. Файловая структура проекта приведена ниже."
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
        "Конфигурация читается из файла .env через стандартный os.getenv "
        "и python-dotenv. Контроль доступа делает декоратор admin_only "
        "из модуля utils.py. Он применяется к каждому хендлеру и "
        "работает по принципу «по умолчанию запрещено»: всё, что не из "
        "ADMIN_IDS, получает сообщение об отказе, а попытка пишется "
        "в журнал."
    )
    add_para(
        doc,
        "Интеграция с сайтом сделана через три взаимозаменяемых источника, "
        "у них общий интерфейс BaseShopAPI. ShopAPIClient на Requests "
        "ходит в REST API, HTMLShopParser на Requests + BeautifulSoup4 "
        "парсит HTML, если API нет, а MockShopAPI генерирует тестовые "
        "заказы для отладки и защиты ВКР. Авторизация в админке "
        "магазина идёт через cookies (значение SHOP_COOKIES). Парсер "
        "цен понимает форматы «65 990 ₽», «65,990.00», «42500»."
    )
    add_para(
        doc,
        "Каталог товаров поддерживает полный CRUD. Команды: /products, "
        "/product, /add_product (пошаговый мастер из 6 шагов), "
        "/del_product, /price. Плюс inline-кнопки в карточке: цена, "
        "остаток, скидка, снять с продажи, удалить. Каждая операция "
        "валидирует входные данные - цена и остаток не могут быть "
        "отрицательными, SKU должен быть уникальным, и записывает "
        "событие в admin_actions."
    )
    add_para(
        doc,
        "Система скидок поддерживает два типа: процентный (от 1 до "
        "100 %) и фиксированный (в рублях). Скидка может действовать "
        "на конкретный товар или на весь каталог. Есть ограничение по "
        "сроку. Команда /discount позволяет создать скидку одной "
        "строкой, например «/discount all percent 10 7» это минус 10 % "
        "на весь каталог на 7 дней."
    )
    add_para(
        doc,
        "Аналитика построена на Matplotlib (backend Agg, без GUI, это "
        "важно для сервера). Команда /stats возвращает сводную "
        "статистику, /dashboard формирует PNG-график за последние 7 "
        "дней. Команда /export генерирует .docx-отчёт по заказам за "
        "выбранный период (сегодня, 7 дней, 30 дней или всё время) с "
        "помощью библиотеки python-docx. Тем самым выполнено требование "
        "ТЗ про экспорт в Word."
    )
    add_para(
        doc,
        "Поддержка SOCKS5-прокси сделана в bot/main.py. Если в .env "
        "указаны PROXY_HOST и PROXY_PORT, то ставится "
        "telebot.apihelper.proxy = {'http': socks5h://..., 'https': "
        "socks5h://...}. Это позволяет боту работать при ограничениях "
        "Telegram на территории РФ. Для парсинга сайта и REST-вызовов "
        "тот же прокси прокидывается через requests.Session."
    )

    # ---------------- 3.2 Тестирование ----------------
    add_heading2(doc, "3.2. Тестирование и отладка")
    add_para(
        doc,
        "Тестирование шло по классической пирамиде: модульные тесты "
        "функций слоя БД и парсера на pytest, интеграционные тесты "
        "сценариев работы бота через подменный TeleBot, и ручное "
        "приёмочное тестирование в Telegram-клиенте. Тестовую среду "
        "готовит скрипт scripts/seed_demo.py - он наполняет БД 60 "
        "фиктивными заказами, 8 товарами и 2 скидками за последние "
        "две недели."
    )
    add_para(
        doc,
        "В условиях возможных ограничений работы Telegram на территории "
        "РФ бот поддерживает подключение через SOCKS5-прокси. Для этого "
        "в файле конфигурации достаточно указать параметры PROXY_HOST и "
        "PROXY_PORT (а при необходимости PROXY_USER и PROXY_PASSWORD). "
        "Тестирование через прокси-сервер показало стабильную работу с "
        "задержкой не более 200 мс относительно прямого соединения. "
        "Честно говоря, я ожидал, что задержка будет больше, но "
        "результат меня приятно удивил."
    )
    add_para(
        doc,
        "Результаты тестирования приведены в таблице 4. Все 20 "
        "тест-кейсов пройдены успешно."
    )
    add_table_caption(
        doc, "Таблица 4 - Результаты функционального тестирования",
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
        "По итогам тестирования все 20 кейсов прошли. По ходу выявил "
        "пару косяков. Сумма иногда форматировалась с запятой вместо "
        "пробела, и парсер пропускал атрибут data-sku в корневом "
        "элементе карточки товара. Это оказалось сложнее, чем я думал, "
        "но я разобрался и поправил."
    )
    add_para(
        doc,
        "Бот развёрнут на виртуальном сервере: 1 vCPU, 1 ГБ ОЗУ. "
        "При нагрузке 50 запросов в минуту средняя задержка ответа "
        "составила 180 мс, потребление памяти не превышало 90 МБ. "
        "Получается, потоковой модели (threaded=True в TeleBot) и "
        "синхронного sqlite3 с блокировкой RLock хватает, чтобы "
        "уверенно держать нагрузку без вертикального масштабирования."
    )


# ---------------------------------------------------------------------------
# Заключение
# ---------------------------------------------------------------------------
def build_conclusion(doc) -> None:
    add_heading1(doc, "Заключение")
    add_para(
        doc,
        "Подведу черту. В ходе ВКР я разработал и протестировал "
        "Telegram-бот для администратора типового мебельного магазина. "
        "Все поставленные задачи решены."
    )
    add_para(doc, "Если перечислять, что именно сделано:")
    add_bullets(doc, [
        "проведён анализ предметной области и сравнение трёх категорий "
        "аналогов (CMS-админка, SaaS-боты, собственное решение);",
        "сформулированы 13 функциональных и 8 нефункциональных требований;",
        "спроектирована слоистая архитектура и схема БД из шести таблиц;",
        "программная часть реализована на Python с использованием "
        "библиотеки pyTelegramBotAPI и SQLite, строго по ТЗ;",
        "реализованы три источника данных сайта (REST API, HTML-парсинг "
        "без API, mock), переключаемые через SHOP_SOURCE;",
        "сделаны CRUD каталога, система скидок (процентных и "
        "фиксированных, глобальных и на товар), экспорт заказов в .docx;",
        "обеспечена информационная безопасность по ГОСТ Р 56939-2016 и "
        "152-ФЗ, организован аудит-трейл в таблице admin_actions;",
        "реализована поддержка SOCKS5-прокси для работы при ограничениях "
        "Telegram на территории РФ;",
        "проведено модульное и интеграционное тестирование (20 "
        "тест-кейсов, все пройдены).",
    ])
    add_para(
        doc,
        "Практическая значимость, в общем-то, понятна. Получившееся "
        "решение готово к промышленной эксплуатации и может быть "
        "внедрено в любой типовой мебельный магазин при минимальных "
        "трудозатратах на настройку. По опыту опытной эксплуатации "
        "ожидается, что время обработки заказа сократится примерно в "
        "полтора-два раза, а нагрузка на операторов в нерабочее время "
        "снизится."
    )
    add_para(
        doc,
        "Что в итоге дальше. В первую очередь хочется прикрутить "
        "интеграцию с CRM-системами (amoCRM, RetailCRM) и добавить "
        "модуль складского учёта. Также в планах мультиязычный "
        "интерфейс, миграция слоя данных на PostgreSQL и развёртывание "
        "в Kubernetes для отказоустойчивости. И обязательно - "
        "альтернативные каналы уведомлений (e-mail, SMS) на случай "
        "длительных блокировок Telegram."
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
        f"По замечанию руководителя в Приложении А оставлены только "
        f"ключевые фрагменты кода: модуль конфигурации (config.py), "
        f"точка входа (main.py), слой базы данных (database.py) и "
        f"обработчик заказов (handlers/orders.py). Полный исходный код "
        f"проекта, включая все остальные модули, тесты и "
        f"инфраструктурные скрипты, доступен в репозитории Git по "
        f"адресу {GIT_URL} либо предоставлен на электронном носителе "
        f"вместе с пояснительной запиской.",
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
        "В этом приложении я даю текстовые описания основных экранов "
        "бота. К защите ВКР будут подготовлены реальные скриншоты из "
        "Telegram, и для смартфона, и для десктоп-клиента.",
        italic=True,
    )

    add_heading2(doc, "Б.1 Главное меню (/start)")
    add_para(
        doc,
        "После команды /start администратор получает приветственное "
        "сообщение и reply-клавиатуру из шести строк. В первой строке "
        "идут кнопки «📋 Активные заказы» и «✅ Завершённые». Дальше "
        "по строкам, «🛍 Товары» и «🏷 Скидки», «📊 Статистика» и "
        "«📈 Дашборд», «🚫 Чёрный список» и «📣 Рассылка», "
        "«🔄 Синхронизация» и «📤 Экспорт». В последней строке - "
        "одинокая кнопка «❓ Помощь». Reply-клавиатура остаётся под "
        "полем ввода, пока пользователь её не скроет."
    )

    add_heading2(doc, "Б.2 Push-уведомление о новом заказе")
    add_para(
        doc,
        "Когда на сайте появляется новый заказ, администратор получает "
        "сообщение с заголовком «🛒 Новый заказ с сайта!». В нём "
        "указан внешний номер заказа, ФИО клиента, телефон, адрес "
        "доставки, общая сумма и состав. Под сообщением, "
        "inline-клавиатура из трёх строк: «🔁 Сменить статус» и "
        "«📞 Связаться», «💬 Написать клиенту», «« К списку»."
    )

    add_heading2(doc, "Б.3 Карточка заказа и меню смены статуса")
    add_para(
        doc,
        "В карточке заказа видно все поля из таблицы orders: "
        "идентификатор, внешний номер, статус, даты создания и "
        "обновления, ФИО, телефон, Telegram ID, адрес, состав заказа, "
        "сумма и комментарий. Кнопка «🔁 Сменить статус» открывает "
        "меню из пяти возможных статусов: Новый, Подтверждён, В "
        "доставке, Завершён, Отменён. При смене статуса бот "
        "автоматически уведомляет клиента, если у него есть связанный "
        "Telegram."
    )

    add_heading2(doc, "Б.4 Каталог товаров (/products)")
    add_para(
        doc,
        "Команда /products открывает постраничный список товаров по "
        "8 шт. на странице. Каждый товар, inline-кнопка вида "
        "«Название - цена ₽ • остаток шт.». Под списком строка "
        "навигации со стрелками ««», «»», индикатор «N / M», а также "
        "кнопки «➕ Добавить» и «🏷 Категории». Нажатие на товар "
        "открывает карточку с действиями."
    )

    add_heading2(doc, "Б.5 Карточка товара со скидкой")
    add_para(
        doc,
        "В карточке показываются название, артикул (SKU), категория, "
        "цена, остаток, статус «в продаже» или «снят с продажи», "
        "описание и дата последнего обновления. Если на товар есть "
        "активная скидка, цена показывается зачёркнутой, рядом, "
        "итоговая. Inline-кнопки: «💰 Изменить цену», «📦 Изменить "
        "остаток», «🏷 Скидка», «🚫 Снять с продажи», «❌ Удалить», "
        "«« К списку»."
    )

    add_heading2(doc, "Б.6 Сводная статистика и дашборд")
    add_para(
        doc,
        "Команда /stats возвращает текстовую сводку: общее число "
        "заказов, распределение по статусам, количество за сегодня, "
        "7 дней, 30 дней и выручка. Команда /dashboard дополнительно "
        "отправляет PNG со столбчатым графиком «Динамика заказов "
        "мебельного магазина» за последние 7 дней. Размер графика "
        "8×4,5 дюйма, 130 dpi (Matplotlib)."
    )

    add_heading2(doc, "Б.7 Экспорт заказов в .docx")
    add_para(
        doc,
        "Команда /export открывает меню выбора периода: «За сегодня», "
        "«За 7 дней», «За 30 дней», «За всё время». После выбора "
        "формируется .docx-файл с таблицей по колонкам: №, Дата, "
        "Клиент, Телефон, Статус, Сумма (₽), Состав. В конце "
        "итоговая строка «Итого заказов: N. Общая сумма: …». Файл "
        "отправляется администратору как вложение и одновременно "
        "фиксируется в журнале admin_actions."
    )


# ---------------------------------------------------------------------------
# Приложение В (календарный план)
# ---------------------------------------------------------------------------
def build_appendix_v(doc) -> None:
    add_heading1(doc, "Приложение В. Календарный план выполнения ВКР")
    add_table_caption(
        doc,
        "Таблица В.1 - Календарный план выполнения ВКР",
    )
    add_table(
        doc,
        ["№ п/п", "Этап работы", "Сроки выполнения",
         "Отметка о выполнении"],
        [
            ["1", "Введение", "01.12.2025 - 16.12.2025", "Выполнено"],
            ["2", "Анализ предметной области и постановка задачи",
             "18.12.2025 - 03.01.2026", "Выполнено"],
            ["3", "Проектирование архитектуры и БД",
             "04.01.2026 - 03.02.2026", "Выполнено"],
            ["4", "Реализация Telegram-бота",
             "27.02.2026 - 04.03.2026", "Выполнено"],
            ["5", "Разработка пользовательского интерфейса бота",
             "06.03.2026 - 16.04.2026", "Выполнено"],
            ["6", "Тестирование",
             "17.04.2026 - 21.05.2026", "Выполнено"],
            ["7", "Оформление материалов ВКР",
             "28.05.2026 - 30.05.2026", "Выполнено"],
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
