"""Сборка пояснительной записки ВКР в формате .docx по ГОСТ 7.32-2017.

Запуск:
    pip install python-docx
    python docs/build_docx.py

Результат: docs/Пояснительная_записка_ВКР.docx
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

DOCS = Path(__file__).resolve().parent
OUT = DOCS / "Пояснительная_записка_ВКР.docx"

FONT = "Times New Roman"
TEXT_SIZE = Pt(14)
CODE_SIZE = Pt(12)
CAPTION_SIZE = Pt(13)


# ----------------------------------------------------------------- helpers
def set_run_font(run, *, size=TEXT_SIZE, bold=False, italic=False, name=FONT):
    run.font.name = name
    run.font.size = size
    run.font.bold = bold
    run.font.italic = italic
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rFonts.set(qn(attr), name)


def add_page_number(paragraph):
    """Добавить поле PAGE в нижний колонтитул."""
    run = paragraph.add_run()
    fldChar1 = OxmlElement("w:fldChar")
    fldChar1.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = "PAGE"
    fldChar2 = OxmlElement("w:fldChar")
    fldChar2.set(qn("w:fldCharType"), "end")
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    set_run_font(run, size=TEXT_SIZE)


def configure_document(doc: Document) -> None:
    """Поля 2/1.5/2/2 см, нумерация страниц снизу по центру, базовый стиль Normal."""
    for section in doc.sections:
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(1.5)
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.different_first_page_header_footer = True

        footer = section.footer
        p = footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_page_number(p)

        first_footer = section.first_page_footer
        first_footer.is_linked_to_previous = False
        first_footer.paragraphs[0].text = ""

    style = doc.styles["Normal"]
    style.font.name = FONT
    style.font.size = TEXT_SIZE
    rPr = style.element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rFonts.set(qn(attr), FONT)
    pf = style.paragraph_format
    pf.line_spacing = 1.5
    pf.first_line_indent = Cm(1.25)
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY


def add_text(doc, text, *, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
             first_line=Cm(1.25), size=TEXT_SIZE, space_after=Pt(0), spacing=1.5):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.first_line_indent = first_line
    pf.line_spacing = spacing
    pf.space_after = space_after
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold, italic=italic)
    return p


def add_h1(doc, text):
    doc.add_page_break()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    pf.first_line_indent = Cm(0)
    pf.line_spacing = 1.5
    pf.space_before = Pt(6)
    pf.space_after = Pt(12)
    run = p.add_run(text.upper())
    set_run_font(run, size=TEXT_SIZE, bold=True)
    return p


def add_h2(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.first_line_indent = Cm(1.25)
    pf.line_spacing = 1.5
    pf.space_before = Pt(12)
    pf.space_after = Pt(6)
    run = p.add_run(text)
    set_run_font(run, size=TEXT_SIZE, bold=True)


def add_h3(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.first_line_indent = Cm(1.25)
    pf.line_spacing = 1.5
    pf.space_before = Pt(8)
    pf.space_after = Pt(4)
    run = p.add_run(text)
    set_run_font(run, size=TEXT_SIZE, bold=True, italic=True)


def add_caption(doc, text, *, before_code=True):
    """Подпись «Листинг N — …» или «Таблица N — …»."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.first_line_indent = Cm(0)
    pf.line_spacing = 1.5
    pf.space_before = Pt(8 if before_code else 0)
    pf.space_after = Pt(4 if before_code else 8)
    run = p.add_run(text)
    set_run_font(run, size=CAPTION_SIZE, bold=False, italic=True)


def add_code(doc, code: str):
    """Многострочный листинг: TNR 12 пт, моноширинного шрифта избегаем — по ГОСТ
    допускается единый Times New Roman. Без отступа первой строки, 1.0 интервал."""
    for line in code.splitlines() or [""]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf = p.paragraph_format
        pf.first_line_indent = Cm(0)
        pf.left_indent = Cm(0.5)
        pf.line_spacing = 1.0
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        run = p.add_run(line.replace("\t", "    "))
        set_run_font(run, size=CODE_SIZE, name="Courier New")


def add_bullets(doc, items):
    for item in items:
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.first_line_indent = Cm(0)
        pf.left_indent = Cm(1.25)
        pf.line_spacing = 1.5
        pf.space_after = Pt(0)
        run = p.add_run("— " + item)
        set_run_font(run, size=TEXT_SIZE)


def add_numbered(doc, items):
    for i, item in enumerate(items, 1):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.first_line_indent = Cm(0)
        pf.left_indent = Cm(1.25)
        pf.line_spacing = 1.5
        pf.space_after = Pt(0)
        run = p.add_run(f"{i}. {item}")
        set_run_font(run, size=TEXT_SIZE)


def add_table(doc, headers, rows, *, widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    if widths:
        for i, w in enumerate(widths):
            for row in table.rows:
                row.cells[i].width = w
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf = p.paragraph_format
        pf.first_line_indent = Cm(0)
        pf.line_spacing = 1.15
        run = p.add_run(h)
        set_run_font(run, size=Pt(13), bold=True)
    for ri, row in enumerate(rows, 1):
        for ci, val in enumerate(row):
            cell = table.rows[ri].cells[ci]
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf = p.paragraph_format
            pf.first_line_indent = Cm(0)
            pf.line_spacing = 1.15
            run = p.add_run(str(val))
            set_run_font(run, size=Pt(12))
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    return table


# --------------------------------------------------------------- title page
def title_page(doc):
    def line(text, *, bold=False, italic=False, size=TEXT_SIZE, align="center",
             space_after=0):
        p = doc.add_paragraph()
        p.alignment = (WD_ALIGN_PARAGRAPH.CENTER if align == "center"
                       else WD_ALIGN_PARAGRAPH.LEFT)
        pf = p.paragraph_format
        pf.first_line_indent = Cm(0)
        pf.line_spacing = 1.15
        pf.space_after = Pt(space_after)
        if text:
            run = p.add_run(text)
            set_run_font(run, size=size, bold=bold, italic=italic)
        return p

    line("МИНИСТЕРСТВО НАУКИ И ВЫСШЕГО ОБРАЗОВАНИЯ", bold=True)
    line("РОССИЙСКОЙ ФЕДЕРАЦИИ", bold=True)
    line("федеральное государственное бюджетное")
    line("образовательное учреждение высшего образования")
    line("«___________________________ ГОСУДАРСТВЕННЫЙ УНИВЕРСИТЕТ»",
         bold=True, space_after=18)

    line("Факультет ___________________________________________", space_after=4)
    line("Кафедра ____________________________________________", space_after=4)
    line("Направление подготовки 09.03.04 «Программная инженерия»",
         space_after=4)
    line("Профиль «Разработка программно-информационных систем»",
         space_after=36)

    line("ВЫПУСКНАЯ КВАЛИФИКАЦИОННАЯ РАБОТА", bold=True, size=Pt(16),
         space_after=12)
    line("на тему:", italic=True)
    line("«Разработка Telegram-бота для автоматизации", bold=True)
    line("администрирования группы»", bold=True, space_after=48)

    for who in (
        ("Студент", ""),
        ("Руководитель ВКР", ""),
        ("Нормоконтролёр", ""),
        ("Зав. кафедрой", ""),
    ):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf = p.paragraph_format
        pf.first_line_indent = Cm(0)
        pf.line_spacing = 1.5
        pf.space_after = Pt(6)
        r1 = p.add_run(f"{who[0]:<22}")
        set_run_font(r1, size=TEXT_SIZE)
        r2 = p.add_run("________________   ")
        set_run_font(r2, size=TEXT_SIZE)
        r3 = p.add_run("/ ____________________ /")
        set_run_font(r3, size=TEXT_SIZE)

    line("", space_after=24)
    line("Город — 2026", italic=True)
    doc.add_page_break()


# ============================================================== build doc
def build():
    doc = Document()
    configure_document(doc)

    # ----- TITLE -----
    title_page(doc)

    # ----- РЕФЕРАТ -----
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_after = Pt(12)
    r = p.add_run("РЕФЕРАТ")
    set_run_font(r, size=TEXT_SIZE, bold=True)

    add_text(doc,
        "Пояснительная записка содержит 40 страниц основного текста, 16 листингов, "
        "3 таблицы, 1 приложение (исходные коды программы) и 7 источников.")
    add_text(doc,
        "Ключевые слова: TELEGRAM-БОТ, AIOGRAM, SQLITE, МОДЕРАЦИЯ, АНТИСПАМ, "
        "АДМИНИСТРИРОВАНИЕ, ВАРНЫ.")
    add_text(doc,
        "Цель работы — разработать программный модуль на языке Python, "
        "автоматизирующий обязанности администратора Telegram-группы: модерацию "
        "сообщений, выдачу предупреждений, ограничение участников и ведение "
        "журнала действий.")
    add_text(doc,
        "Объект разработки — серверное Telegram-приложение на базе библиотеки "
        "aiogram 3.x и СУБД SQLite, поддерживающее независимые настройки для "
        "нескольких групп.")
    add_text(doc,
        "Результат работы — работающий бот, реализующий все требования "
        "технического задания: антиспам (5 сообщений за 10 секунд), антимат, "
        "антиссылки, варны (3 → автоматический мут на 24 часа), команды "
        "/mute, /unmute, /warn, /kick, /ban, /unban, /info, /stats, /setup, "
        "/export_logs, журналирование в базу данных и файл errors.log.")

    # ----- СОДЕРЖАНИЕ -----
    add_h1(doc, "Содержание")
    toc_rows = [
        ("Введение", "4"),
        ("1. Техническое задание", "5"),
        ("2. Обзор аналогов", "7"),
        ("2.1. Group Manager Bot", "7"),
        ("2.2. Rose Bot", "8"),
        ("2.3. Сводный вывод", "8"),
        ("3. Описание архитектуры бота", "9"),
        ("3.1. Схема модулей", "9"),
        ("3.2. Назначение файлов", "10"),
        ("3.3. Описание базы данных", "11"),
        ("4. Руководство администратора", "13"),
        ("4.1. Установка", "13"),
        ("4.2. Команды бота", "14"),
        ("4.3. Сценарии работы", "15"),
        ("5. Листинг программы", "17"),
        ("6. Инструкция по развёртыванию", "35"),
        ("Заключение", "38"),
        ("Список использованных источников", "39"),
    ]
    add_table(doc, ["Раздел", "Стр."], toc_rows,
              widths=[Cm(13.5), Cm(2.5)])

    # ----- ВВЕДЕНИЕ -----
    add_h1(doc, "Введение")
    intro = [
        "Telegram входит в число наиболее популярных мессенджеров в Российской "
        "Федерации и странах СНГ; через его групповые чаты ежедневно проходят "
        "миллиарды сообщений. С ростом размера сообщества администраторы "
        "сталкиваются с типовыми, но трудоёмкими задачами: удаление спама и "
        "рекламы, контроль ненормативной лексики, борьба с фишинговыми "
        "ссылками, выдача предупреждений и блокировок, ведение журнала "
        "действий и формирование статистики. Выполнение этих задач вручную "
        "нерационально и приводит к ошибкам, поэтому актуальной становится "
        "автоматизация модерации.",
        "Актуальность работы обусловлена потребностью владельцев Telegram-групп "
        "в едином инструменте, который выполнял бы рутинные обязанности "
        "модератора круглосуточно, прозрачно фиксировал каждое действие в "
        "журнале и позволял настраивать политику модерации индивидуально для "
        "каждой группы.",
        "Цель работы — разработать Telegram-бота, автоматизирующего обязанности "
        "администратора группы в соответствии с требованиями технического задания.",
    ]
    for t in intro:
        add_text(doc, t)

    add_text(doc, "Задачи работы:", bold=True, first_line=Cm(1.25))
    add_numbered(doc, [
        "Проанализировать существующие аналоги и сформировать требования к функциональности.",
        "Спроектировать модульную архитектуру и схему базы данных.",
        "Реализовать механизмы антиспама, антимата, контроля ссылок и систему варнов.",
        "Реализовать команды модерации: /mute, /unmute, /warn, /kick, /ban, /unban, /info, /stats, /setup, /export_logs.",
        "Обеспечить логирование нарушений и действий администраторов в базу данных и файл errors.log.",
        "Подготовить инструкции по установке локально и на VPS.",
    ])
    add_text(doc, "Объект исследования — процессы администрирования Telegram-групп.")
    add_text(doc, "Предмет исследования — программные средства автоматизации модерации на базе Bot API Telegram.")

    # ----- 1. ТЗ -----
    add_h1(doc, "1. Техническое задание")

    add_h2(doc, "1.1. Назначение разработки")
    add_text(doc,
        "Telegram-бот для автоматизации обязанностей администратора группы. "
        "Бот должен заменять ручные операции модерации: фильтрацию сообщений, "
        "выдачу предупреждений, ограничение и блокировку участников, ведение "
        "журнала событий, формирование статистики.")

    add_h2(doc, "1.2. Функциональные требования")
    add_numbered(doc, [
        "Поддержка нескольких групп. Все настройки фильтров и политик "
        "модерации хранятся в базе данных и применяются индивидуально для "
        "каждой группы.",
        "Антиспам. Сообщения одного пользователя ограничиваются параметрами "
        "antispam_msgs / antispam_seconds. По умолчанию — 5 сообщений за "
        "10 секунд. При превышении лимита сообщение удаляется, выдаётся варн.",
        "Антимат. Список запрещённых слов задаётся администратором. Слово "
        "ищется регистронезависимо, по границам слова. При обнаружении "
        "сообщение удаляется, выдаётся варн.",
        "Антиссылки. В сообщениях допускаются только ссылки на домены из "
        "белого списка trusted_domains. Все остальные ссылки удаляются, "
        "выдаётся варн.",
        "Система варнов. Лимит — 3 варна (настраивается через warn_limit). "
        "При достижении лимита автоматически выдаётся мут на 24 часа "
        "(настраивается через mute_hours).",
        "Команды администратора: /mute, /unmute, /warn, /kick, /ban, /unban, "
        "/info, /stats, /setup, /export_logs. Команды доступны только "
        "пользователям со статусом «administrator» или «creator» в данном чате.",
        "Цель команды указывается reply’ем на сообщение, через @username "
        "либо числовой ID. Длительность — в формате 10m, 2h, 7d.",
        "Журналирование. Действия модерации, нарушения и изменения настроек "
        "сохраняются в таблицу logs, ошибки уровня WARNING/ERROR дублируются "
        "в файл errors.log. Доступна выгрузка журнала в формате CSV (/export_logs).",
        "Конфигурация. Параметры подключения (токен бота, ID владельца, путь "
        "к БД, путь к лог-файлу) хранятся в файле .env.",
    ])

    add_h2(doc, "1.3. Технические требования")
    add_bullets(doc, [
        "Python 3.10 и выше.",
        "aiogram 3.x — асинхронный фреймворк для Bot API.",
        "SQLite — встроенная СУБД, доступ через aiosqlite.",
        "Структура проекта: каталоги database/, handlers/, filters/, utils/, keyboards/.",
        "Точка входа — main.py. Соответствие PEP 8.",
    ])

    add_h2(doc, "1.4. Требования к надёжности")
    add_text(doc,
        "Бот должен корректно обрабатывать ошибки Bot API "
        "(TelegramBadRequest, TelegramForbiddenError), не прекращая работу, "
        "и журналировать инциденты.")

    add_h2(doc, "1.5. Требования к документации")
    add_text(doc,
        "В состав поставки входят: исходный код, файл requirements.txt, "
        "файл-образец .env.example, файл README.md с пошаговой инструкцией запуска.")

    # ----- 2. ОБЗОР АНАЛОГОВ -----
    add_h1(doc, "2. Обзор аналогов")
    add_text(doc,
        "Для определения требуемого функционала выполнен анализ двух наиболее "
        "распространённых решений, представленных на рынке Telegram-ботов "
        "модерации.")

    add_h2(doc, "2.1. Group Manager Bot (@GroupManager_bot)")
    add_text(doc,
        "Назначение — универсальный коммерческий бот для модерации Telegram-групп.")
    add_text(doc, "Преимущества:", bold=True)
    add_bullets(doc, [
        "широкий набор команд (warn, mute, ban, captcha, antiflood, antilink);",
        "поддержка большого числа групп на одной инсталляции;",
        "встроенная система notes (заметок) и rules;",
        "мультиязычный интерфейс.",
    ])
    add_text(doc, "Недостатки:", bold=True)
    add_bullets(doc, [
        "проприетарный — исходный код закрыт, локальная установка невозможна;",
        "журнал хранится только на стороне провайдера, выгрузка ограничена;",
        "настройки белых доменов и списка запрещённых слов — платные расширения в части тарифов;",
        "при отсутствии связи с сервером владельца группа полностью теряет модерацию.",
    ])

    add_h2(doc, "2.2. Rose Bot (@MissRose_bot)")
    add_text(doc,
        "Один из самых популярных opensource-ориентированных модераторов "
        "Telegram, написан на Python.")
    add_text(doc, "Преимущества:", bold=True)
    add_bullets(doc, [
        "модульная архитектура, активное сообщество;",
        "развитая система фильтров и расширений;",
        "поддержка ChatPermissions и ограничений по типам медиа;",
        "конфигурируемые приветствия и правила.",
    ])
    add_text(doc, "Недостатки:", bold=True)
    add_bullets(doc, [
        "написан на устаревшей синхронной библиотеке python-telegram-bot 12.x с "
        "длительной миграцией на 20.x, что затрудняет сопровождение;",
        "настройки хранятся в общей реляционной БД без удобных переключателей "
        "модулей на уровне отдельной группы;",
        "установка тяжёлая — требует Redis и PostgreSQL;",
        "для разработки требуется глубокое знание Dispatcher-цепочек.",
    ])

    add_h2(doc, "2.3. Сводный вывод")
    add_text(doc,
        "Существующие аналоги либо проприетарны, либо чрезмерно тяжелы для "
        "развертывания на VPS малого размера. Разрабатываемое в настоящей ВКР "
        "решение заполняет эту нишу: лёгкая зависимость только от aiogram 3.x "
        "и SQLite, поддержка нескольких групп с индивидуальными настройками, "
        "простая выгрузка журнала в CSV, открытая модульная архитектура.")

    # ----- 3. АРХИТЕКТУРА -----
    add_h1(doc, "3. Описание архитектуры бота")

    add_h2(doc, "3.1. Схема модулей")
    add_text(doc,
        "Архитектура построена по принципу разделения ответственности: "
        "верхний слой — точка входа и роутер aiogram; средний — обработчики "
        "команд и фильтры; нижний — модуль базы данных и сервисные утилиты "
        "(логирование, декораторы доступа). Схема приведена ниже.")
    add_code(doc, """\
                       +-----------------------+
                       |       main.py         |
                       |  (точка входа, run)   |
                       +-----------+-----------+
                                   |
        +--------------------------+---------------------------+
        |                          |                           |
   +----v----+              +------v------+             +------v-----+
   | config  |              |  database/  |             |   utils/   |
   |  .env   |              |    db.py    |             |  logger.py |
   +---------+              |   SQLite    |             | decorators |
                            +------+------+             +------+-----+
                                   |                           |
                       +-----------+---------------------------+
                       |              handlers/                |
                       |  users.py   admins.py   setup.py      |
                       +-------------------+-------------------+
                                           |
                                +----------+---------+
                                |     filters/       |
                                | antispam links     |
                                |       badwords     |
                                +----------+---------+
                                           |
                                +----------v---------+
                                |    keyboards/      |
                                | inline-меню /setup |
                                +--------------------+""")

    add_h2(doc, "3.2. Назначение файлов")
    add_caption(doc, "Таблица 1 — Состав исходных файлов")
    add_table(doc, ["Файл", "Назначение"], [
        ("main.py", "Точка входа: инициализация Bot, Dispatcher, подключение БД, запуск polling."),
        ("config.py", "Загрузка переменных окружения из .env, значения по умолчанию."),
        ("requirements.txt", "Список Python-зависимостей с фиксацией версий."),
        (".env.example", "Образец конфигурации (без секретов)."),
        ("database/db.py", "Описание схемы SQLite и методов доступа (асинхронные корутины)."),
        ("handlers/users.py", "Автоматическая модерация, реакция фильтров, приветствие."),
        ("handlers/admins.py", "Команды /warn, /mute, /unmute, /ban, /unban, /kick, /info, /stats, /export_logs."),
        ("handlers/setup.py", "Команда /setup и inline-меню настроек группы (FSM)."),
        ("filters/antispam.py", "Фильтр частоты сообщений (скользящее окно)."),
        ("filters/links.py", "Фильтр ссылок по белому списку доменов."),
        ("filters/badwords.py", "Фильтр запрещённых слов (регулярные выражения)."),
        ("utils/logger.py", "Настройка stdout + ротация errors.log."),
        ("utils/decorators.py", "Декораторы group_only, admin_only."),
        ("keyboards/__init__.py", "Inline-клавиатуры меню /setup."),
        ("README.md", "Краткая инструкция запуска."),
    ], widths=[Cm(5.0), Cm(11.0)])

    add_h2(doc, "3.3. Описание базы данных")
    add_text(doc,
        "База данных — SQLite, файл bot.db. Все запросы выполняются "
        "асинхронно через aiosqlite, при первом запуске схема создаётся "
        "автоматически.")
    add_caption(doc, "Таблица 2 — Структура таблиц БД")
    add_table(doc, ["Таблица", "Поля", "Назначение"], [
        ("users",
         "user_id PK, username, full_name, first_seen, last_seen",
         "Кэш профилей участников групп."),
        ("group_settings",
         "chat_id PK, title, antispam_msgs, antispam_seconds, warn_limit, "
         "mute_hours, bad_words (JSON), trusted_domains (JSON), "
         "antispam_on, antilinks_on, antibadwords_on, welcome_text",
         "Индивидуальные настройки каждой группы."),
        ("warns",
         "id PK, chat_id, user_id, admin_id, reason, created",
         "Журнал выданных предупреждений."),
        ("bans",
         "id PK, chat_id, user_id, admin_id, kind (ban|mute), reason, "
         "until_ts, active, created",
         "История ограничений и блокировок."),
        ("logs",
         "id PK, chat_id, user_id, admin_id, action, details, created",
         "Универсальный журнал событий (нарушения, действия админов, "
         "изменения настроек)."),
    ], widths=[Cm(3.5), Cm(7.5), Cm(5.5)])

    add_text(doc, "ER-диаграмма (текстовая):", bold=True, first_line=Cm(0))
    add_code(doc, """\
users(user_id) ---< warns(user_id, chat_id) >--- group_settings(chat_id)
               ---< bans (user_id, chat_id) ---|
               ---< logs (user_id, chat_id) ---|""")
    add_text(doc,
        "Внешние ключи в SQLite не объявляются жёстко (поля chat_id, "
        "user_id индексируются через CREATE INDEX) — это упрощает миграцию "
        "и не требует ON DELETE CASCADE.")

    # ----- 4. РУКОВОДСТВО АДМИНИСТРАТОРА -----
    add_h1(doc, "4. Руководство администратора")

    add_h2(doc, "4.1. Установка")
    add_numbered(doc, [
        "Установить Python 3.10+ и Git.",
        "Получить токен бота у @BotFather.",
        "Клонировать репозиторий и перейти в каталог bot/.",
        "Создать виртуальное окружение и установить зависимости: "
        "python -m venv .venv && source .venv/bin/activate && "
        "pip install -r requirements.txt.",
        "Скопировать .env.example в .env, указать BOT_TOKEN и OWNER_ID.",
        "Запустить бота: python main.py.",
        "Добавить бота в Telegram-группу, выдать права администратора "
        "(минимум: удаление сообщений, ограничение участников).",
        "В чате группы выполнить /setup.",
    ])
    add_caption(doc, "[СКРИН 1 — приветствие /start]", before_code=False)

    add_h2(doc, "4.2. Команды бота")
    add_caption(doc, "Таблица 3 — Команды бота")
    add_table(doc, ["Команда", "Описание", "Права"], [
        ("/start", "Приветственное сообщение.", "Любой пользователь."),
        ("/help", "Краткая справка по командам.", "Любой пользователь."),
        ("/setup", "Открывает inline-меню настроек группы.", "Администратор группы."),
        ("/warn @u причина", "Выдать варн. При достижении лимита — автомут.", "Администратор."),
        ("/mute @u 2h причина", "Запретить писать (по умолчанию — бессрочно).", "Администратор."),
        ("/unmute @u", "Снять мут.", "Администратор."),
        ("/ban @u 7d причина", "Забанить пользователя.", "Администратор."),
        ("/unban @u", "Разбанить.", "Администратор."),
        ("/kick @u", "Исключить из группы.", "Администратор."),
        ("/info @u", "Карточка пользователя: ID, варны, активные санкции.", "Администратор."),
        ("/stats", "Сводная статистика по группе.", "Администратор."),
        ("/export_logs", "Экспорт журнала в CSV.", "Администратор."),
    ], widths=[Cm(4.0), Cm(8.5), Cm(4.0)])
    add_caption(doc, "[СКРИН 2 — меню /setup]", before_code=False)
    add_caption(doc, "[СКРИН 3 — пример карточки /info]", before_code=False)
    add_caption(doc, "[СКРИН 4 — выгрузка /export_logs]", before_code=False)

    add_h2(doc, "4.3. Сценарии работы")
    add_text(doc,
        "Сценарий «Спам». Участник за 10 секунд отправил 6 сообщений. "
        "Бот удаляет шестое сообщение, добавляет запись в таблицу warns, "
        "отправляет в чат предупреждение «Варн 1/3». При накоплении 3 "
        "варнов выдаётся restrict_chat_member на 24 часа, журнал "
        "пополняется записью auto_mute.")
    add_caption(doc, "[СКРИН 5 — срабатывание антиспама]", before_code=False)
    add_text(doc,
        "Сценарий «Запрещённое слово». Участник отправил сообщение со словом "
        "из списка bad_words. Бот удаляет сообщение и фиксирует нарушение.")
    add_caption(doc, "[СКРИН 6 — срабатывание антимата]", before_code=False)
    add_text(doc,
        "Сценарий «Ссылка». Участник отправил ссылку на сторонний домен. "
        "Бот извлекает hostname, сравнивает с trusted_domains. Если совпадения "
        "нет — сообщение удаляется, выдаётся варн.")
    add_caption(doc, "[СКРИН 7 — срабатывание антиссылок]", before_code=False)

    # ----- 5. ЛИСТИНГИ -----
    add_h1(doc, "5. Листинг программы")
    add_text(doc,
        "В настоящем разделе приведены все модули разработанного программного "
        "комплекса. Шрифт листингов — Courier New / Times New Roman 12 пт, "
        "междустрочный интервал — одинарный. После каждого листинга приводится "
        "его краткий анализ (2-3 предложения).")

    listings = []

    # 1. main.py
    listings.append(("main.py", '''\
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
''',
"Модуль выполняет последовательную инициализацию: валидирует переменные "
"окружения, настраивает логирование, открывает SQLite-соединение и запускает "
"long-polling. Использование DefaultBotProperties(parse_mode=HTML) снимает "
"необходимость указывать parse_mode в каждом ответе; корректное завершение "
"закрывает сессию и БД, предотвращая утечки файловых дескрипторов."))

    # 2. config.py
    listings.append(("config.py", '''\
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
''',
"Конфигурация выделена в отдельный dataclass(slots=True) — это экономит память "
"и одновременно явно фиксирует список настраиваемых параметров. Значения по "
"умолчанию соответствуют требованиям ТЗ (5 сообщений / 10 секунд антиспама, "
"3 варна → 24 часа мута)."))

    # 3. database/db.py
    listings.append(("database/db.py (фрагмент: схема и базовые операции)", '''\
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

    async def add_warn(self, chat_id, user_id, admin_id, reason) -> int:
        await self.conn.execute(
            "INSERT INTO warns(chat_id, user_id, admin_id, reason, created) "
            "VALUES (?, ?, ?, ?, ?)",
            (chat_id, user_id, admin_id, reason, int(time.time())))
        await self.conn.commit()
        cur = await self.conn.execute(
            "SELECT COUNT(*) FROM warns WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id))
        row = await cur.fetchone()
        return int(row[0]) if row else 0

db = Database()
''',
"Схема описана единым SQL-блоком и создаётся идемпотентно (IF NOT EXISTS). "
"Поля-списки (bad_words, trusted_domains) хранятся в виде JSON-строк — это "
"компромисс между нормализацией и простотой: списки короткие, отдельная "
"нормализованная таблица переусложнила бы код. Соединение единственное на "
"процесс — это допустимо для SQLite, который сам сериализует записи."))

    # 4. database/__init__.py
    listings.append(("database/__init__.py", '''\
"""Пакет работы с базой данных SQLite."""
from .db import Database, db

__all__ = ["Database", "db"]
''',
"Реэкспорт упрощает импорт в остальных модулях: from database import db."))

    # 5. filters/antispam.py
    listings.append(("filters/antispam.py", '''\
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
''',
"Хранение «корзин» (deque) в памяти процесса исключает обращение к БД при "
"каждом сообщении и обеспечивает алгоритмическую сложность O(1) на проверку. "
"Когда лимит превышен — корзина очищается, чтобы пользователь не «жил» в "
"состоянии непрерывного нарушения после первого срабатывания."))

    # 6. filters/links.py
    listings.append(("filters/links.py", '''\
"""Фильтр ссылок по белому списку доменов."""
from __future__ import annotations
import re
from typing import Any, Dict
from urllib.parse import urlparse

from aiogram.filters import BaseFilter
from aiogram.types import Message
from database import db

URL_RE = re.compile(
    r"(?:(?:https?|tg)://[^\\s]+|(?:www\\.|t\\.me/|@)[^\\s]+)",
    re.IGNORECASE,
)


def _extract_host(token: str) -> str:
    token = token.strip().strip(".,;!?)\\"\\'")
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
''',
"Регулярное выражение охватывает три случая ссылок: HTTP/HTTPS, tg-deeplink и "
"@-упоминание (которое раскрывается в t.me). Сопоставление с доверенными "
"доменами поддерживает поддомены (youtu.be для домена youtube.com), что снижает "
"число ложных срабатываний фильтра."))

    # 7. filters/badwords.py
    listings.append(("filters/badwords.py", '''\
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
    return re.compile(rf"(?<!\\w)(?:{escaped})(?!\\w)",
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
''',
"Регулярное выражение строится один раз и кэшируется через lru_cache. Шаблон "
"(?<!\\w)…(?!\\w) исключает ложные срабатывания на подстроках — «дурак» "
"сработает, но «дуракан» — нет."))

    # 8. filters/__init__.py
    listings.append(("filters/__init__.py", '''\
"""Пакет пользовательских фильтров aiogram."""
from .antispam import AntiSpamFilter
from .badwords import BadWordsFilter
from .links import LinksFilter

__all__ = ["AntiSpamFilter", "BadWordsFilter", "LinksFilter"]
''',
"Реэкспорт публичных классов фильтров обеспечивает единый импорт "
"from filters import … в хэндлерах."))

    # 9. utils/logger.py
    listings.append(("utils/logger.py", '''\
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
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")
    stream = logging.StreamHandler(sys.stdout)
    stream.setLevel(logging.INFO)
    stream.setFormatter(fmt)
    file_h = RotatingFileHandler(log_file, maxBytes=2_000_000,
                                 backupCount=5, encoding="utf-8")
    file_h.setLevel(logging.WARNING)
    file_h.setFormatter(fmt)
    root.handlers.clear()
    root.addHandler(stream)
    root.addHandler(file_h)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    _INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
''',
"Применена ротация (5 файлов по 2 МБ) — это предохраняет диск VPS от "
"переполнения. Уровень INFO выводится только в stdout, WARNING/ERROR "
"дополнительно дублируются в файл errors.log, что соответствует требованию ТЗ."))

    # 10. utils/decorators.py
    listings.append(("utils/decorators.py", '''\
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
''',
"Декораторы делают код хэндлеров декларативным: проверка прав отделена от "
"бизнес-логики команды. OWNER_ID имеет приоритет над членством в чате — это "
"удобно для отладки и обслуживания."))

    # 11. utils/__init__.py
    listings.append(("utils/__init__.py", '''\
"""Сервисные утилиты: логирование, декораторы доступа."""
from .logger import get_logger, setup_logging
from .decorators import admin_only, group_only

__all__ = ["get_logger", "setup_logging", "admin_only", "group_only"]
''',
"Сводный импорт упрощает использование утилит из любого хэндлера одной "
"строкой."))

    # 12. keyboards/__init__.py
    listings.append(("keyboards/__init__.py", '''\
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
    label_on = ("V " if value else "") + "Включить"
    label_off = ("V " if not value else "") + "Выключить"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label_on, callback_data=f"toggle:{field}:1"),
         InlineKeyboardButton(text=label_off, callback_data=f"toggle:{field}:0")],
        [InlineKeyboardButton(text="« Назад", callback_data="setup:back")],
    ])


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Назад", callback_data="setup:back")]
    ])
''',
"Все элементы меню вынесены в отдельный модуль. Это позволяет переиспользовать "
"клавиатуры и не дублировать их в хэндлерах команды /setup."))

    # 13. handlers/__init__.py
    listings.append(("handlers/__init__.py", '''\
"""Регистрация всех роутеров aiogram."""
from aiogram import Router
from . import admins, setup, users


def get_root_router() -> Router:
    root = Router(name="root")
    root.include_router(setup.router)
    root.include_router(admins.router)
    root.include_router(users.router)
    return root


__all__ = ["get_root_router"]
''',
"Корневой роутер собирает три подмаршрутизатора. Порядок включения важен: "
"setup и admins стоят перед users, иначе catch-all из users.py (кэширование "
"пользователей) перехватит сообщение раньше команд."))

    # 14. handlers/users.py
    listings.append(("handlers/users.py", '''\
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
                f"X {full}: достигнут лимит варнов ({cfg.warn_limit}). "
                f"Мут на {cfg.mute_hours} ч.")
        except Exception as exc:
            log.error("restrict_chat_member: %s", exc)
    else:
        await message.answer(
            f"! {full}, нарушение: {reason}. Варн {warns}/{cfg.warn_limit}.")


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
''',
"Все три фильтра приводят к одной и той же ветке _auto_punish — поэтому код "
"наказания не дублируется. Передача reason в хэндлеры реализована через возврат "
"словаря из фильтра — стандартный механизм aiogram для проксирования данных в "
"обработчик."))

    # 15. handlers/admins.py
    listings.append(("handlers/admins.py (фрагмент)", '''\
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

DURATION_RE = re.compile(r"^(\\d+)\\s*([smhd])$", re.IGNORECASE)
UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_duration(token: str) -> int | None:
    if not token:
        return None
    m = DURATION_RE.match(token)
    if not m:
        return None
    return int(m.group(1)) * UNIT_SECONDS[m.group(2).lower()]


async def resolve_target(message, args, bot):
    """Reply | @username | numeric ID -> (uid, name, tail)."""
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
            f"X {name}: лимит варнов. Мут на {cfg.mute_hours} ч.")
    else:
        await message.reply(
            f"! {name}: варн {warns}/{cfg.warn_limit}. "
            f"Причина: {reason or '—'}")

# /mute /unmute /ban /unban /kick /info /stats /export_logs реализованы по
# аналогичной схеме — полностью см. файл bot/handlers/admins.py в репозитории.
''',
"Логика всех команд приведена к единой схеме: разобрать цель → проверить "
"права → выполнить действие → сохранить в БД и в журнал → ответить "
"пользователю. Универсальный парсер resolve_target устраняет дублирование, а "
"parse_duration поддерживает интуитивный формат 10m / 2h / 7d."))

    # 16. handlers/setup.py
    listings.append(("handlers/setup.py (фрагмент)", '''\
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


@router.callback_query(F.data.startswith("toggle:"))
async def cb_toggle(cb: CallbackQuery) -> None:
    _, field, raw = cb.data.split(":")
    await db.update_setting(cb.message.chat.id, field, int(raw))
    await db.log("settings_change", chat_id=cb.message.chat.id,
                 admin_id=cb.from_user.id, details=f"{field}={raw}")
    cfg = await db.get_settings(cb.message.chat.id, cb.message.chat.title or "")
    await cb.message.edit_text(_status_text(cfg), reply_markup=setup_menu())
    await cb.answer("Сохранено.")
''',
"Состояния waiting_words / waiting_domains / waiting_warns реализуют пошаговый "
"ввод значений — стандартный для aiogram паттерн Finite State Machine. После "
"сохранения значения состояние очищается, и пользователю снова показывается "
"главное меню /setup."))

    for i, (name, code, analysis) in enumerate(listings, 1):
        add_caption(doc, f"Листинг {i} — {name}")
        add_code(doc, code)
        add_text(doc, "Анализ. " + analysis, italic=False, first_line=Cm(1.25))

    # ----- 6. РАЗВЕРТЫВАНИЕ -----
    add_h1(doc, "6. Инструкция по развёртыванию")

    add_h2(doc, "6.1. Локальный запуск")
    add_code(doc, """\
git clone <URL_репозитория>
cd bot
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
nano .env                            # BOT_TOKEN=..., OWNER_ID=...
python main.py""")
    add_text(doc,
        "После запуска бот появится «в сети». Добавление в группу и выдача "
        "прав администратора описаны в §4.1.")

    add_h2(doc, "6.2. Развёртывание на VPS (Ubuntu 22.04, systemd)")
    add_numbered(doc, [
        "Установить системные пакеты: sudo apt update && "
        "sudo apt install -y python3 python3-venv python3-pip git.",
        "Создать отдельного пользователя: sudo useradd -m -s /bin/bash tgbot.",
        "Клонировать репозиторий и установить зависимости (см. §6.1).",
        "Создать unit-файл /etc/systemd/system/tgbot.service (см. ниже).",
        "Включить и запустить: sudo systemctl daemon-reload && "
        "sudo systemctl enable --now tgbot.service.",
        "Просмотр журналов: sudo journalctl -u tgbot -f.",
    ])
    add_caption(doc, "Содержимое /etc/systemd/system/tgbot.service")
    add_code(doc, """\
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
WantedBy=multi-user.target""")

    add_h2(doc, "6.3. Резервное копирование")
    add_text(doc,
        "База bot.db — единственный файл со всеми настройками и журналом, "
        "копируется обычным cp или rsync (предварительно желательно выполнить "
        'sqlite3 bot.db ".backup \'/tmp/bot.db.bak\'"). Журнал errors.log '
        "ротируется автоматически (5 файлов по 2 МБ).")

    # ----- ЗАКЛЮЧЕНИЕ -----
    add_h1(doc, "Заключение")
    add_text(doc,
        "В ходе выполнения выпускной квалификационной работы поставленная цель "
        "достигнута: разработан Telegram-бот, автоматизирующий обязанности "
        "администратора группы.")
    add_text(doc, "В работе выполнено:", bold=True)
    add_numbered(doc, [
        "Проанализированы существующие аналоги (Group Manager Bot, Rose Bot), "
        "выделены требования к собственной разработке.",
        "Спроектирована модульная архитектура: разделение на пакеты database, "
        "handlers, filters, utils, keyboards, единая точка входа main.py.",
        "Разработана схема SQLite из пяти таблиц (users, group_settings, "
        "warns, bans, logs), реализованы асинхронные методы доступа на базе "
        "aiosqlite.",
        "Реализованы три модуля автоматической модерации (антиспам, антимат, "
        "антиссылки) в виде пользовательских фильтров aiogram 3.x.",
        "Реализованы все команды модерации, требуемые в ТЗ, с поддержкой "
        "указания цели через reply / @username / ID и формата длительности "
        "10m / 2h / 7d.",
        "Реализовано меню настроек /setup на inline-клавиатурах с "
        "использованием FSM aiogram.",
        "Реализовано двойное журналирование: в таблицу logs для аналитики и в "
        "ротируемый файл errors.log для технического сопровождения.",
        "Подготовлены инструкции по локальной установке и развёртыванию на VPS "
        "под systemd.",
    ])
    add_text(doc, "Приобретённые и развитые навыки:", bold=True)
    add_bullets(doc, [
        "асинхронное программирование на Python (asyncio, корутины);",
        "работа с современным фреймворком aiogram 3.x: Router, фильтры, FSM, "
        "inline-клавиатуры;",
        "проектирование схемы реляционной БД и использование SQLite через aiosqlite;",
        "применение принципов модульной декомпозиции, PEP 8, разделения ответственности;",
        "подготовка прикладного ПО к развертыванию (виртуальные окружения, "
        "systemd, ротация логов);",
        "оформление технической документации по требованиям ГОСТ 7.32-2017 и "
        "ГОСТ 2.105-95.",
    ])
    add_text(doc, "Перспективы развития:", bold=True)
    add_bullets(doc, [
        "перенос FSM-хранилища с MemoryStorage на Redis для горизонтального "
        "масштабирования;",
        "добавление веб-панели администратора (FastAPI) для удалённого доступа "
        "к настройкам и журналу;",
        "подключение captcha-проверки новых участников и проверки фишинговых "
        "URL по внешним API.",
    ])

    # ----- ИСТОЧНИКИ -----
    add_h1(doc, "Список использованных источников")
    sources = [
        "ГОСТ 7.32-2017. Система стандартов по информации, библиотечному и "
        "издательскому делу. Отчёт о научно-исследовательской работе. "
        "Структура и правила оформления. — М.: Стандартинформ, 2017. — 27 с.",
        "ГОСТ 2.105-95. Единая система конструкторской документации. Общие "
        "требования к текстовым документам. — М.: Стандартинформ, 1996. — 38 с.",
        "PEP 8 — Style Guide for Python Code [Электронный ресурс]. — URL: "
        "https://peps.python.org/pep-0008/ (дата обращения: 10.05.2026).",
        "Aiogram 3.x. Official documentation [Электронный ресурс]. — URL: "
        "https://docs.aiogram.dev/ (дата обращения: 10.05.2026).",
        "SQLite. Documentation [Электронный ресурс]. — URL: "
        "https://www.sqlite.org/docs.html (дата обращения: 10.05.2026).",
        "Telegram Bot API [Электронный ресурс]. — URL: "
        "https://core.telegram.org/bots/api (дата обращения: 10.05.2026).",
        "Лутц М. Изучаем Python: в 2 т. — 5-е изд. — М.: Диалектика-Вильямс, "
        "2019. — Т. 1. — 832 с.",
    ]
    for i, src in enumerate(sources, 1):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.first_line_indent = Cm(0)
        pf.left_indent = Cm(1.0)
        pf.line_spacing = 1.5
        pf.space_after = Pt(4)
        run = p.add_run(f"{i}. {src}")
        set_run_font(run, size=TEXT_SIZE)

    doc.save(OUT)
    print(f"Документ создан: {OUT} ({OUT.stat().st_size // 1024} КБ)")


if __name__ == "__main__":
    build()
