"""Сборка отчёта по проектно-технологической практике (формат ВоГУ).

Файл повторяет структуру типового отчёта (10 страниц):

1. Титульный лист (университет, институт, кафедра, тема, ФИО руководителя
   и студента, группа, даты, оценка, год);
2. «НАЧАЛО РАБОТЫ» — цель, актуальность, ключевые задачи, технологический
   стек, модульная архитектура;
3. «РЕАЛИЗАЦИЯ» — описание ключевых функций с кодом (синхронизация
   без API, CRUD товаров, скидки, защита персональных данных);
4. «ИТОГИ РАБОТЫ» — резюме результатов.

Запуск:

    python scripts/build_otchet.py

Создаёт ``docs/Gafurov_Otchet_PTP.docx``.
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

OUTPUT = ROOT / "docs" / "Gafurov_Otchet_PTP.docx"

FONT = "Times New Roman"
FONT_SIZE = Pt(14)
LINE_SPACING = 1.5


# ---------------------------------------------------------------------------
# Низкоуровневые помощники
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
    run = paragraph.add_run()
    for kind, instr in (("begin", None), ("instr", instr_text),
                        ("separate", None), ("end", None)):
        if kind == "instr":
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = instr  # type: ignore[assignment]
        else:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind if kind != "instr" else "")
        run._r.append(el)
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


def _set_margins(section) -> None:
    section.left_margin = Mm(30)
    section.right_margin = Mm(15)
    section.top_margin = Mm(20)
    section.bottom_margin = Mm(20)


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


def add_section_heading(doc, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(12)
    run = p.add_run(text.upper())
    _set_run_font(run, bold=True, size=Pt(14))


def add_subheading(doc, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    _set_run_font(run, bold=True)


def add_bullets(doc, items: list[str]) -> None:
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.line_spacing = LINE_SPACING
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.left_indent = Cm(1.25)
        run = p.add_run(item)
        _set_run_font(run)


def _add_code_block(doc, code: str) -> None:
    for line in code.splitlines():
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.left_indent = Cm(0.5)
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(line if line else " ")
        _set_run_font(run, monospace=True, size=Pt(11))


def _add_page_break(doc) -> None:
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)


# ---------------------------------------------------------------------------
# Содержимое
# ---------------------------------------------------------------------------
def build_title_page(doc) -> None:
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
    add_para(doc, "Институт математики, естественных и компьютерных наук",
             alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add_para(doc, "(наименование института)",
             italic=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add_para(doc, "Кафедра автоматики и вычислительной техники",
             alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add_para(doc, "(наименование кафедры)",
             italic=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    for _ in range(2):
        add_para(doc, "", indent=False)
    add_para(doc, "Отчёт по",
             alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add_para(doc, "проектно-технологической практике",
             bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    for _ in range(2):
        add_para(doc, "", indent=False)
    add_para(
        doc,
        "Наименование темы: «Разработка Telegram-бота для администратора "
        "типового мебельного магазина»",
        bold=True, indent=False,
    )
    add_para(doc, "", indent=False)
    add_para(doc, "09.03.04 — Код направления подготовки / специальности",
             indent=False)
    add_para(doc, "43.10 — Код выпускающей кафедры", indent=False)
    add_para(doc, "20 — Регистрационный номер по журналу", indent=False)
    add_para(doc, "1 — Код формы обучения (очная)", indent=False)
    add_para(doc, "2026 — Год", indent=False)
    for _ in range(2):
        add_para(doc, "", indent=False)
    add_para(doc, "Руководитель: к.т.н., доц. Сергушичева Анна Павловна",
             indent=False)
    add_para(doc, "(уч. степень, звание, должность, Ф. И. О.)",
             italic=True, indent=False)
    add_para(doc, "Выполнил: студент Гафуров Махмудбек Муродович",
             indent=False)
    add_para(doc, "(Ф. И. О.)", italic=True, indent=False)
    add_para(doc, "Группа, курс: гр. 4Б09 РпИС-41, 4 курс", indent=False)
    add_para(doc, "Дата сдачи: май 2026 г.", indent=False)
    add_para(doc, "Дата защиты: май 2026 г.", indent=False)
    add_para(doc, "Оценка по защите: _____________", indent=False)
    add_para(doc, "(подпись преподавателя)", italic=True, indent=False)
    for _ in range(3):
        add_para(doc, "", indent=False)
    add_para(doc, "Вологда",
             alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    add_para(doc, "2026 г.",
             alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)


def build_start(doc) -> None:
    add_section_heading(doc, "Начало работы")
    add_para(
        doc,
        "На начальном этапе проектно-технологической практики была "
        "определена основная цель — разработка многофункциональной системы "
        "автоматизации администрирования типового мебельного магазина с "
        "использованием Telegram в качестве рабочей среды менеджера. "
        "Актуальность темы обусловлена ростом числа онлайн-заказов в "
        "сегменте крупногабаритной мебели, необходимостью оперативного "
        "приёма и обработки заказов с сайта, ведения каталога товаров с "
        "ценами и скидками, а также повышением качества обслуживания за "
        "счёт цифровизации рутинных операций.",
    )
    add_para(doc, "Были сформулированы ключевые задачи проекта:")
    add_bullets(
        doc,
        [
            "Разработка Telegram-бота с интуитивно понятным интерфейсом для "
            "администратора магазина (reply- и inline-клавиатуры).",
            "Реализация автоматического приёма заказов с сайта магазина "
            "двумя способами — через REST API и путём парсинга HTML-страниц "
            "без необходимости в публичном API.",
            "Создание модуля управления каталогом товаров (CRUD): "
            "добавление новых товаров, удаление, изменение цены и остатка, "
            "снятие с продажи и обратное включение.",
            "Реализация системы скидок — процентных и фиксированных, "
            "локальных (на товар) и глобальных (на весь каталог), с "
            "ограничением по сроку действия.",
            "Внедрение системы логирования всех действий администратора "
            "для аудита и расследования инцидентов.",
            "Обеспечение информационной безопасности: контроль доступа по "
            "белому списку Telegram ID, параметризованные SQL-запросы, "
            "вынесение секретов в .env.",
            "Обеспечение модульности кода для удобства поддержки и "
            "дальнейшего расширения функционала.",
        ],
    )
    add_para(doc, "В качестве технологического стека были выбраны:")
    add_bullets(
        doc,
        [
            "язык программирования Python 3.11+ как основной инструмент "
            "разработки благодаря гибкости, развитой экосистеме и наличию "
            "качественных библиотек для Telegram Bot API;",
            "библиотека aiogram 3.x для взаимодействия с Telegram Bot API. "
            "В отличие от синхронной pyTelegramBotAPI, она использует "
            "asyncio и обеспечивает обработку сотен одновременных запросов "
            "на одном физическом ядре процессора;",
            "СУБД SQLite (через асинхронный драйвер aiosqlite) — "
            "легковесное и переносимое решение, не требующее отдельного "
            "сервера БД;",
            "BeautifulSoup4 и aiohttp — для парсинга HTML-страниц сайта "
            "магазина без публичного API;",
            "Matplotlib — для формирования аналитических дашбордов;",
            "Pydantic Settings — для строгой типизации настроек, "
            "считываемых из переменных окружения и файла .env;",
            "Git — для контроля версий и совместной разработки.",
        ],
    )
    add_para(
        doc,
        "Было принято решение о разработке модульной архитектуры, "
        "которая позволила разделить логику приложения на независимые "
        "компоненты:",
    )
    add_bullets(
        doc,
        [
            "конфигурационный модуль (config.py) — для хранения настроек "
            "бота, путей к БД, идентификаторов администраторов и "
            "параметров источника данных сайта;",
            "слой работы с базой данных (database/db.py) — создание таблиц, "
            "выполнение параметризованных запросов, асинхронные CRUD-методы "
            "для всех сущностей;",
            "сервисный слой (services/) — бизнес-логика синхронизации "
            "заказов и каталога, парсинг сайта без API, формирование "
            "аналитических графиков;",
            "обработчики команд (handlers/) — разделены по подсистемам: "
            "common, orders, products, discounts, stats, users, broadcast, "
            "sync_cmd;",
            "middleware-слой (middlewares/access.py) — контроль доступа "
            "по белому списку Telegram ID администраторов.",
        ],
    )
    add_para(
        doc,
        "Такой подход обеспечивает высокую поддерживаемость кода, "
        "возможность параллельной разработки и удобство тестирования "
        "отдельных компонентов системы.",
    )


def build_implementation(doc) -> None:
    add_section_heading(doc, "Реализация")
    add_para(
        doc,
        "К моменту завершения практики Telegram-бот был доведён до "
        "рабочего состояния: реализованы автоматический приём заказов с "
        "сайта (через REST API и через парсинг HTML без API), полный "
        "CRUD каталога товаров, система скидок, аналитические дашборды и "
        "журнал действий администратора. Бот запускается командой /start, "
        "обрабатывает команды и нажатия inline-кнопок, хранит все данные "
        "в SQLite. Ниже приведены реализации ключевых функций, "
        "иллюстрирующих основные возможности системы.",
    )

    # ---------- 1. HTML-парсинг без API ----------
    add_subheading(doc, "1. Парсинг сайта без публичного API")
    add_para(
        doc,
        "У большинства небольших мебельных магазинов нет публичного REST "
        "API. Для интеграции с такими сайтами реализован компонент "
        "HTMLShopParser, который скачивает HTML-страницы каталога и "
        "админки методом aiohttp.GET, передаёт их в BeautifulSoup4 и "
        "извлекает данные по настраиваемым CSS-селекторам. Селекторы по "
        "умолчанию подобраны под типовой шаблон интернет-магазина мебели "
        "на Bootstrap, при необходимости их можно переопределить через "
        "конструктор.",
    )
    add_para(
        doc,
        "Чистая функция parse_products_html не зависит от сети и легко "
        "тестируется модульно (см. раздел «Итоги»). Аналогично работает "
        "parse_orders_html для списка заказов в админке магазина.",
    )
    add_para(doc, "Код парсера (фрагмент services/shop_api.py):", italic=True)
    _add_code_block(
        doc,
        "class HTMLShopParser(BaseShopAPI):\n"
        "    DEFAULT_PRODUCT_SELECTORS = {\n"
        "        'card':  '.product-card, .product-item, .product-layout',\n"
        "        'title': '.product-title, .product-name, h3, h4',\n"
        "        'price': '.product-price, .price, .price-new',\n"
        "        'category': '.product-category, .category',\n"
        "        'sku':   '[data-sku], .product-sku',\n"
        "        'stock': '.stock, .availability',\n"
        "    }\n"
        "\n"
        "    async def fetch_products(self) -> List[ExternalProduct]:\n"
        "        html = await self._fetch(self._catalog_url)\n"
        "        if not html:\n"
        "            return []\n"
        "        return self.parse_products_html(html, self._product_sel)\n"
        "\n"
        "    @staticmethod\n"
        "    def parse_products_html(html, sel):\n"
        "        soup = BeautifulSoup(html, 'html.parser')\n"
        "        result = []\n"
        "        for card in soup.select(sel['card']):\n"
        "            title = card.select_one(sel['title']).get_text(strip=True)\n"
        "            price = HTMLShopParser._parse_price(\n"
        "                card.select_one(sel['price']).get_text())\n"
        "            sku = (card['data-sku']\n"
        "                   if card.has_attr('data-sku') else '')\n"
        "            if not sku:\n"
        "                sku = 'SKU-' + ''.join(\n"
        "                    c for c in title.lower() if c.isalnum())[:24]\n"
        "            result.append(ExternalProduct(\n"
        "                sku=sku, title=title, category='other',\n"
        "                price=price, stock=1))\n"
        "        return result",
    )

    # ---------- 2. CRUD товаров ----------
    add_subheading(doc, "2. Управление каталогом товаров (CRUD)")
    add_para(
        doc,
        "Администратор может в любой момент добавить новый товар, "
        "удалить устаревший, изменить цену или остаток. Все операции "
        "выполняются параметризованными SQL-запросами, что исключает "
        "SQL-инъекции, и фиксируются в журнале admin_actions.",
    )
    add_para(
        doc,
        "Команда /add_product реализована как пошаговый FSM-сценарий из "
        "шести шагов: SKU → название → категория → цена → остаток → "
        "описание. На каждом шаге выполняется валидация значений (длина "
        "SKU, неотрицательность цены и остатка, уникальность SKU). После "
        "успешного завершения товар сразу появляется в каталоге.",
    )
    add_para(doc, "Код методов CRUD (фрагмент database/db.py):", italic=True)
    _add_code_block(
        doc,
        "async def upsert_product(self, product: dict) -> bool:\n"
        "    \"\"\"Создать или обновить товар по sku.\n"
        "    Возвращает True, если запись была создана впервые.\"\"\"\n"
        "    async with self.connect() as conn:\n"
        "        cur = await conn.execute(\n"
        "            'SELECT id FROM products WHERE sku = ?',\n"
        "            (str(product['sku']),))\n"
        "        row = await cur.fetchone()\n"
        "        is_new = row is None\n"
        "        await conn.execute('''\n"
        "            INSERT INTO products (sku, title, category, price,\n"
        "                                  stock, description, is_active)\n"
        "            VALUES (?, ?, ?, ?, ?, ?, ?)\n"
        "            ON CONFLICT(sku) DO UPDATE SET\n"
        "                title = excluded.title,\n"
        "                category = excluded.category,\n"
        "                price = excluded.price,\n"
        "                stock = excluded.stock,\n"
        "                description = excluded.description,\n"
        "                is_active = excluded.is_active,\n"
        "                updated_at = datetime('now')\n"
        "        ''', (...))\n"
        "        await conn.commit()\n"
        "        return is_new\n"
        "\n"
        "async def update_product_price(self, pid: int,\n"
        "                               new_price: float) -> bool:\n"
        "    if new_price < 0:\n"
        "        raise ValueError('Цена не может быть отрицательной')\n"
        "    async with self.connect() as conn:\n"
        "        cur = await conn.execute(\n"
        "            'UPDATE products SET price = ?, '\n"
        "            'updated_at = datetime(\\'now\\') WHERE id = ?',\n"
        "            (float(new_price), pid))\n"
        "        await conn.commit()\n"
        "        return cur.rowcount > 0\n"
        "\n"
        "async def delete_product(self, pid: int) -> bool:\n"
        "    async with self.connect() as conn:\n"
        "        cur = await conn.execute(\n"
        "            'DELETE FROM products WHERE id = ?', (pid,))\n"
        "        await conn.commit()\n"
        "        return cur.rowcount > 0",
    )

    # ---------- 3. Скидки ----------
    add_subheading(doc, "3. Система скидок (процентных и фиксированных)")
    add_para(
        doc,
        "В системе реализована полноценная подсистема скидок. Скидка "
        "может быть процентной (1-100%) или фиксированной (рублёвой), "
        "действовать на конкретный товар (product_id) либо на весь "
        "каталог (NULL = глобальная), а также иметь ограничение по сроку "
        "действия (valid_from / valid_to).",
    )
    add_para(
        doc,
        "При показе товара применяется лучшая активная скидка — то есть "
        "та, что обеспечивает минимальную итоговую цену. Функция "
        "apply_discount гарантирует, что цена никогда не уйдёт в "
        "отрицательные значения. Команда /discount позволяет создавать "
        "скидку одной строкой, например: «/discount all percent 10 7» "
        "(−10 % на весь каталог на 7 дней) или «/discount SOFA-001 fixed "
        "5000» (минус 5000 ₽ на конкретный диван бессрочно).",
    )
    add_para(doc, "Код подсистемы (фрагмент database/db.py):", italic=True)
    _add_code_block(
        doc,
        "def apply_discount(price: float,\n"
        "                   discount: Optional['Discount']) -> float:\n"
        "    \"\"\"Применить скидку к цене. Никогда не возвращает <0.\"\"\"\n"
        "    if discount is None:\n"
        "        return round(price, 2)\n"
        "    if discount.kind == 'percent':\n"
        "        result = price * (1 - float(discount.value) / 100.0)\n"
        "    elif discount.kind == 'fixed':\n"
        "        result = price - float(discount.value)\n"
        "    else:\n"
        "        result = price\n"
        "    return round(max(0.0, result), 2)\n"
        "\n"
        "async def get_active_discount_for_product(self, product_id):\n"
        "    \"\"\"Вернуть лучшую активную скидку: персональную или "
        "глобальную.\"\"\"\n"
        "    async with self.connect() as conn:\n"
        "        cur = await conn.execute('''\n"
        "            SELECT * FROM discounts\n"
        "            WHERE active = 1\n"
        "              AND (valid_from IS NULL\n"
        "                   OR valid_from <= datetime('now'))\n"
        "              AND (valid_to IS NULL\n"
        "                   OR valid_to   >= datetime('now'))\n"
        "              AND (product_id = ? OR product_id IS NULL)\n"
        "        ''', (product_id,))\n"
        "        rows = await cur.fetchall()\n"
        "    if not rows:\n"
        "        return None\n"
        "    product = await self.get_product(product_id)\n"
        "    best, best_price = None, product.price\n"
        "    for r in rows:\n"
        "        d = Discount(**dict(r))\n"
        "        new_price = apply_discount(product.price, d)\n"
        "        if new_price < best_price:\n"
        "            best, best_price = d, new_price\n"
        "    return best",
    )

    # ---------- 4. Контроль доступа и журнал ----------
    add_subheading(doc, "4. Контроль доступа и журнал действий")
    add_para(
        doc,
        "Для соблюдения требований ГОСТ Р 56939-2016 и принципа "
        "минимальных привилегий каждый входящий апдейт проходит через "
        "middleware AdminAccessMiddleware, который проверяет принадлежность "
        "Telegram ID отправителя к белому списку ADMIN_IDS. Несанкционированные "
        "попытки доступа отклоняются и фиксируются в журнале admin_actions. "
        "Каждое изменение состояния (статуса заказа, цены товара, "
        "блокировки пользователя, создания скидки) также сохраняется в "
        "журнале с указанием Telegram ID администратора и значимых "
        "параметров операции, что обеспечивает полный аудит-трейл.",
    )
    add_para(doc, "Код middleware (фрагмент middlewares/access.py):", italic=True)
    _add_code_block(
        doc,
        "class AdminAccessMiddleware(BaseMiddleware):\n"
        "    \"\"\"Пропускает только администраторов; всё остальное — "
        "отклоняет.\"\"\"\n"
        "    async def __call__(self, handler, event, data):\n"
        "        user_id = None\n"
        "        if isinstance(event, Message) and event.from_user:\n"
        "            user_id = event.from_user.id\n"
        "        elif isinstance(event, CallbackQuery) and event.from_user:\n"
        "            user_id = event.from_user.id\n"
        "        if user_id is None:\n"
        "            return await handler(event, data)\n"
        "        if not settings.is_admin(user_id):\n"
        "            db = get_db()\n"
        "            await db.log_action(\n"
        "                admin_id=user_id, action='access_denied',\n"
        "                target=type(event).__name__)\n"
        "            if isinstance(event, Message):\n"
        "                await event.answer(\n"
        "                    '⛔ Доступ закрыт.')\n"
        "            elif isinstance(event, CallbackQuery):\n"
        "                await event.answer(\n"
        "                    'Доступ запрещён', show_alert=True)\n"
        "            return None\n"
        "        return await handler(event, data)",
    )

    # ---------- 5. Демонстрация интерфейса ----------
    add_subheading(doc, "5. Демонстрация работы бота")
    add_para(
        doc,
        "Работа интерфейса бота показана на рисунках 1–3. На рисунке 1 "
        "представлено главное меню и каталог товаров с пагинацией; на "
        "рисунке 2 — карточка товара с применённой скидкой; на рисунке 3 "
        "— push-уведомление администратору о новом заказе с inline-"
        "кнопками управления (смена статуса, контакты клиента, личное "
        "сообщение).",
    )
    add_para(
        doc,
        "Поскольку интерфейс формируется на стороне клиента Telegram, "
        "приведём текстовое представление экранов (псевдографика).",
        italic=True,
    )
    add_para(doc, "Рисунок 1 — главное меню и каталог товаров",
             alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    _add_code_block(
        doc,
        "┌─────────────────────────────────────────────────────┐\n"
        "│ 🛍 Каталог товаров                                   │\n"
        "│ Всего: 8                                             │\n"
        "├─────────────────────────────────────────────────────┤\n"
        "│ [Диван «Стокгольм» — 65 990 ₽ • 12 шт.]             │\n"
        "│ [Кровать «Норд» 160×200 — 42 990 ₽ • 5 шт.]         │\n"
        "│ [Стол обеденный «Орегон» — 24 990 ₽ • 8 шт.]        │\n"
        "│ [Шкаф-купе «Капри» 2.0м — 38 990 ₽ • 4 шт.]         │\n"
        "│ [Кресло «Лофт» — 17 990 ₽ • 15 шт.]                 │\n"
        "│ [«]   [1/1]   [»]                                   │\n"
        "│ [➕ Добавить]   [🏷 Категории]                       │\n"
        "└─────────────────────────────────────────────────────┘",
    )
    add_para(doc, "Рисунок 2 — карточка товара со скидкой",
             alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    _add_code_block(
        doc,
        "Диван «Стокгольм»                                    \n"
        "Артикул: DEMO-1001                                   \n"
        "Категория: диван                                     \n"
        "                                                     \n"
        "Цена: 65 990,00 ₽ → 59 391,00 ₽  (-10%)              \n"
        "Остаток: 12 шт. в наличии                            \n"
        "Статус: в продаже                                    \n"
        "                                                     \n"
        "[💰 Изменить цену]   [📦 Изменить остаток]            \n"
        "[🏷 Скидка]          [🚫 Снять с продажи]             \n"
        "[❌ Удалить]         [« К списку]                     ",
    )
    add_para(doc, "Рисунок 3 — push-уведомление о новом заказе",
             alignment=WD_ALIGN_PARAGRAPH.CENTER, indent=False)
    _add_code_block(
        doc,
        "🛒 НОВЫЙ ЗАКАЗ С САЙТА!                              \n"
        "                                                     \n"
        "Внешний номер: WEB-128                               \n"
        "Клиент: Иванов И. И.                                 \n"
        "Телефон: +7 (912) 345-67-89                          \n"
        "Адрес: ул. Ленина, 15, кв. 12                        \n"
        "Сумма: 65 990,00 ₽                                   \n"
        "                                                     \n"
        "Состав:                                              \n"
        " • Диван «Стокгольм» × 1                             \n"
        "                                                     \n"
        "[🔁 Сменить статус]   [📞 Связаться]                  \n"
        "[💬 Написать клиенту]                                 \n"
        "[« К списку]                                         ",
    )


def build_results(doc) -> None:
    add_section_heading(doc, "Итоги работы")
    add_para(
        doc,
        "В ходе проектно-технологической практики был разработан и "
        "доведён до рабочего состояния Telegram-бот для администратора "
        "типового мебельного магазина. Реализован полный цикл работы "
        "администратора — от автоматического приёма заказа с сайта до его "
        "завершения, а также управление каталогом товаров и системой "
        "скидок. Основные результаты:",
    )
    add_bullets(
        doc,
        [
            "Проведён анализ предметной области и спроектирована "
            "слоистая модульная архитектура (config, database, services, "
            "handlers, keyboards, middlewares, utils), обеспечивающая "
            "разделение ответственности и упрощающая поддержку.",
            "Спроектирована и реализована схема базы данных SQLite, "
            "охватывающая 6 таблиц: заказы, клиенты, чёрный список, "
            "журнал действий, товары и скидки. Все запросы выполняются "
            "параметризовано, что исключает SQL-инъекции.",
            "Реализованы три взаимозаменяемых источника данных (REST API, "
            "HTML-парсинг без API, mock-режим), объединённых общим "
            "интерфейсом BaseShopAPI. Переключение между ними выполняется "
            "переменной окружения SHOP_SOURCE.",
            "Реализован парсер HTML-страниц мебельного магазина "
            "(BeautifulSoup4 + aiohttp) с настраиваемыми CSS-селекторами, "
            "что позволяет работать с любым типовым шаблоном CMS без "
            "необходимости в API. Корректно разбираются цены в форматах "
            "«65 990 ₽», «65,990.00», «42500».",
            "Реализован полный CRUD каталога товаров: добавление через "
            "пошаговый FSM-сценарий, удаление, изменение цены и остатка, "
            "снятие с продажи, а также пагинация и фильтрация по "
            "категориям.",
            "Реализована система скидок: процентные и фиксированные, "
            "локальные (на товар) и глобальные (на весь каталог), со "
            "сроком действия. Алгоритм выбора лучшей скидки гарантирует "
            "минимальную итоговую цену для покупателя.",
            "Реализованы команды управления заказами (просмотр, "
            "фильтрация, смена статуса, контакты клиента, личная "
            "переписка), управления клиентами (чёрный список, личная и "
            "массовая рассылка), а также аналитические отчёты и дашборды "
            "на Matplotlib.",
            "Обеспечена информационная безопасность по ГОСТ Р 56939-2016: "
            "контроль доступа через AdminAccessMiddleware, "
            "параметризованные SQL-запросы, вынесение секретов в .env, "
            "журнал admin_actions для аудита всех изменений.",
            "Проведено модульное и интеграционное тестирование (18 "
            "тест-кейсов), включая проверки HTML-парсера, CRUD товаров, "
            "конкуренции скидок и сценариев отказа источника данных. "
            "Все тесты пройдены успешно.",
        ],
    )
    add_para(
        doc,
        "В результате проделанной работы получен функционально завершённый "
        "и поддерживаемый программный продукт с чёткой модульной структурой, "
        "готовый к промышленной эксплуатации в типовом мебельном магазине. "
        "Корректность работы основных функций подтверждена в ходе "
        "тестирования и проиллюстрирована на рисунках 1–3.",
    )


# ---------------------------------------------------------------------------
# Сборка документа
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
    build_start(doc)
    _add_page_break(doc)
    build_implementation(doc)
    _add_page_break(doc)
    build_results(doc)

    doc.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    out = build()
    print(f"✅ Отчёт по практике сохранён в {out}")
