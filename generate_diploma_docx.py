from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt, RGBColor


OUT_DIR = Path("docs")
OUT_FILE = OUT_DIR / "VKR_Khudoykulzoda_Sh_M_proekt_zavoda_maslo_pahta_STO_2022.docx"


def fmt(value: float, digits: int = 1) -> str:
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")


def rub(value: float) -> str:
    return fmt(value, 2)


def add_widow_control(paragraph):
    p_pr = paragraph._p.get_or_add_pPr()
    if p_pr.find(qn("w:widowControl")) is None:
        p_pr.append(OxmlElement("w:widowControl"))


def set_paragraph_format(paragraph, first_line: bool = True, line_spacing: float = 1.5):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.left_indent = Cm(0)
    paragraph.paragraph_format.right_indent = Cm(0)
    paragraph.paragraph_format.first_line_indent = Cm(1.25) if first_line else Cm(0)
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = line_spacing
    add_widow_control(paragraph)


def set_run(run, size: int = 14, bold: bool = False, italic: bool = False):
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(0, 0, 0)


def configure_section(section, *, footer: bool = True, start_page: int | None = None):
    section.page_height = Mm(297)
    section.page_width = Mm(210)
    section.top_margin = Mm(20)
    section.bottom_margin = Mm(20)
    section.left_margin = Mm(30)
    section.right_margin = Mm(15)
    section.different_first_page_header_footer = True
    if start_page is not None:
        sect_pr = section._sectPr
        pg_num = sect_pr.find(qn("w:pgNumType"))
        if pg_num is None:
            pg_num = OxmlElement("w:pgNumType")
            sect_pr.append(pg_num)
        pg_num.set(qn("w:start"), str(start_page))
    if footer:
        add_page_number(section)


def add_page_number(section):
    footer = section.footer
    paragraph = footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    paragraph.paragraph_format.first_line_indent = Cm(0)
    run = paragraph.add_run()
    fld_char_begin = OxmlElement("w:fldChar")
    fld_char_begin.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = "PAGE"
    fld_char_end = OxmlElement("w:fldChar")
    fld_char_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char_begin)
    run._r.append(instr_text)
    run._r.append(fld_char_end)
    set_run(run, 12)


def set_defaults(doc: Document):
    configure_section(doc.sections[0], footer=False)
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.font.size = Pt(14)
    normal.paragraph_format.first_line_indent = Cm(1.25)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.space_before = Pt(0)

    for name in ("Heading 1", "Heading 2", "Heading 3"):
        style = styles[name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        style.font.size = Pt(14)
        style.font.bold = True
        style.paragraph_format.space_before = Pt(0)
        style.paragraph_format.space_after = Pt(0)
        style.paragraph_format.line_spacing = 1.5
        style.paragraph_format.first_line_indent = Cm(0 if name == "Heading 1" else 1.25)
    styles["Heading 1"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    styles["Heading 2"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    styles["Heading 3"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    for name in ("TOC 1", "TOC 2", "TOC 3"):
        if name in styles:
            style = styles[name]
            style.font.name = "Times New Roman"
            style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
            style.font.size = Pt(14)
            style.font.bold = False
            style.font.color.rgb = RGBColor(0, 0, 0)
            style.paragraph_format.line_spacing = 1.5
            style.paragraph_format.space_before = Pt(0)
            style.paragraph_format.space_after = Pt(0)


def paragraph(doc: Document, text: str = "", *, align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line: bool = True, bold: bool = False, size: int = 14, spacing: float = 1.5):
    par = doc.add_paragraph()
    set_paragraph_format(par, first_line=first_line, line_spacing=spacing)
    par.alignment = align
    run = par.add_run(text)
    set_run(run, size=size, bold=bold)
    return par


def empty_line(doc: Document):
    paragraph(doc, "", first_line=False)


def add_heading(doc: Document, text: str, level: int):
    if level == 1:
        if doc.paragraphs and 'w:type="page"' not in doc.paragraphs[-1]._p.xml:
            doc.add_page_break()
    par = doc.add_heading(text, level=level)
    set_paragraph_format(par, first_line=(level != 1), line_spacing=1.5)
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER if level == 1 else WD_ALIGN_PARAGRAPH.LEFT
    for run in par.runs:
        set_run(run, bold=True)
    empty_line(doc)
    return par


def add_struct_heading(doc: Document, text: str):
    add_heading(doc, text.upper(), 1)


def set_table_borders(table):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "8")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), "000000")


def set_cell(cell, text: str, *, bold: bool = False, align=WD_ALIGN_PARAGRAPH.CENTER, size: int = 12):
    cell.text = ""
    par = cell.paragraphs[0]
    set_paragraph_format(par, first_line=False, line_spacing=1.0)
    par.alignment = align
    run = par.add_run(str(text))
    set_run(run, size=size, bold=bold)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


def add_table(doc: Document, title: str, headers: list[str], rows: list[list[str]], *, widths: list[float] | None = None):
    paragraph(doc, title, first_line=False, spacing=1.0)
    tbl = doc.add_table(rows=1, cols=len(headers))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = True
    set_table_borders(tbl)
    for idx, header in enumerate(headers):
        set_cell(tbl.rows[0].cells[idx], header, bold=True)
        if widths:
            tbl.rows[0].cells[idx].width = Cm(widths[idx])
    for row in rows:
        cells = tbl.add_row().cells
        for idx, value in enumerate(row):
            set_cell(cells[idx], str(value), align=WD_ALIGN_PARAGRAPH.LEFT if idx == 0 else WD_ALIGN_PARAGRAPH.CENTER)
            if widths:
                cells[idx].width = Cm(widths[idx])
    empty_line(doc)
    return tbl


def add_figure_text(doc: Document, body: str, caption: str):
    empty_line(doc)
    for line in body.splitlines():
        paragraph(doc, line, align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False, spacing=1.0)
    par = paragraph(doc, caption, align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False, spacing=1.0)
    for run in par.runs:
        set_run(run, size=14, bold=False)
    empty_line(doc)


def add_field(paragraph, instruction: str, placeholder: str):
    run = paragraph.add_run()
    fld_char_begin = OxmlElement("w:fldChar")
    fld_char_begin.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = instruction
    fld_char_separate = OxmlElement("w:fldChar")
    fld_char_separate.set(qn("w:fldCharType"), "separate")
    fld_char_end = OxmlElement("w:fldChar")
    fld_char_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char_begin)
    run._r.append(instr_text)
    run._r.append(fld_char_separate)
    placeholder_run = paragraph.add_run(placeholder)
    set_run(placeholder_run)
    placeholder_run._r.append(fld_char_end)


def add_formula(doc: Document, formula: str, number: str):
    empty_line(doc)
    tbl = doc.add_table(rows=1, cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = True
    set_cell(tbl.rows[0].cells[0], formula, align=WD_ALIGN_PARAGRAPH.CENTER, size=14)
    set_cell(tbl.rows[0].cells[1], number, align=WD_ALIGN_PARAGRAPH.RIGHT, size=14)
    tbl.rows[0].cells[0].width = Cm(13)
    tbl.rows[0].cells[1].width = Cm(2)
    empty_line(doc)


def calculations():
    milk = 60000.0
    milk_fat = 3.8
    milk_protein = 3.2
    density = 1028.0
    cream_fat = 35.0
    skim_fat = 0.05
    sep_loss_rate = 0.001
    cream_pasteur_loss_rate = 0.002
    butter_filling_loss_rate = 0.003
    buttermilk_loss_rate = 0.005
    buttermilk_pasteur_loss_rate = 0.002
    drink_filling_loss_rate = 0.002
    milk_after_sep_loss = milk * (1 - sep_loss_rate)
    separation_loss = milk * sep_loss_rate
    cream = milk_after_sep_loss * (milk_fat - skim_fat) / (cream_fat - skim_fat)
    skim = milk_after_sep_loss - cream
    milk_fat_mass = milk * milk_fat / 100
    cream_fat_mass = cream * cream_fat / 100
    skim_fat_mass = skim * skim_fat / 100
    cream_after_pasteur = cream * (1 - cream_pasteur_loss_rate)
    cream_pasteur_loss = cream * cream_pasteur_loss_rate
    cream_after_pasteur_fat = cream_after_pasteur * cream_fat / 100
    retained_fat = cream_after_pasteur_fat * 0.995
    peasant_fat_mass = retained_fat * 0.75
    dessert_fat_mass = retained_fat * 0.25
    peasant_before_filling = peasant_fat_mass / 0.725
    dessert_before_filling = dessert_fat_mass / 0.52
    peasant = peasant_before_filling * (1 - butter_filling_loss_rate)
    dessert = dessert_before_filling * (1 - butter_filling_loss_rate)
    butter_total = peasant + dessert
    butter_filling_loss = peasant_before_filling * butter_filling_loss_rate + dessert_before_filling * butter_filling_loss_rate
    buttermilk_raw = cream_after_pasteur - peasant_before_filling - dessert_before_filling
    buttermilk = buttermilk_raw * (1 - buttermilk_loss_rate)
    buttermilk_process_loss = buttermilk_raw * buttermilk_loss_rate
    pasteurized_bm_base = buttermilk * 0.50 * (1 - buttermilk_pasteur_loss_rate)
    pasteurized_bm = pasteurized_bm_base * (1 - drink_filling_loss_rate)
    fermented_base = buttermilk * 0.30 * (1 - buttermilk_pasteur_loss_rate)
    fermented_sugar = fermented_base * 0.055
    fermented_starter = fermented_base * 0.03
    fermented_before_filling = fermented_base + fermented_sugar + fermented_starter
    fermented = fermented_before_filling * (1 - drink_filling_loss_rate)
    vanilla_base = buttermilk * 0.20 * (1 - buttermilk_pasteur_loss_rate)
    vanilla_sugar = vanilla_base * 0.045
    vanilla_flavor = vanilla_base * 0.0008
    vanilla_before_filling = vanilla_base + vanilla_sugar + vanilla_flavor
    vanilla = vanilla_before_filling * (1 - drink_filling_loss_rate)
    fat_in_butter = peasant * 0.725 + dessert * 0.52
    fat_in_buttermilk = max(milk_fat_mass - skim_fat_mass - fat_in_butter, 0)
    fat_unaccounted = milk_fat_mass - skim_fat_mass - fat_in_butter - fat_in_buttermilk
    work_days = 250
    shifts_per_day = 1
    annual_milk_t = milk * work_days * shifts_per_day / 1000
    return locals()


def add_title_page(doc: Document):
    for line in (
        "Министерство сельского хозяйства Российской Федерации",
        "федеральное государственное бюджетное образовательное учреждение высшего образования",
        "«Вологодская государственная молочнохозяйственная академия имени Н.В. Верещагина»",
        "ТЕХНОЛОГИЧЕСКИЙ ФАКУЛЬТЕТ",
        "КАФЕДРА ТЕХНОЛОГИИ МОЛОКА И МОЛОЧНЫХ ПРОДУКТОВ",
    ):
        paragraph(doc, line, align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False, spacing=1.0)

    for _ in range(2):
        empty_line(doc)
    paragraph(doc, "Допущен к защите", align=WD_ALIGN_PARAGRAPH.LEFT, first_line=False, spacing=1.0)
    paragraph(doc, "Заведующий кафедрой,", align=WD_ALIGN_PARAGRAPH.LEFT, first_line=False, spacing=1.0)
    paragraph(doc, "канд. техн. наук, доцент", align=WD_ALIGN_PARAGRAPH.LEFT, first_line=False, spacing=1.0)
    paragraph(doc, "_____________ / Носкова В.И. /", align=WD_ALIGN_PARAGRAPH.LEFT, first_line=False, spacing=1.0)
    paragraph(doc, "«_____» ______________ 2026 г.", align=WD_ALIGN_PARAGRAPH.LEFT, first_line=False, spacing=1.0)
    empty_line(doc)
    paragraph(doc, "ВЫПУСКНАЯ КВАЛИФИКАЦИОННАЯ РАБОТА", align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False, bold=True)
    paragraph(doc, "Проект завода по производству масла и продуктов из пахты", align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False, bold=True)
    empty_line(doc)
    paragraph(doc, "направление подготовки 19.03.03 - Продукты питания животного происхождения", first_line=False)
    paragraph(doc, "профиль подготовки - Технология молока и молочных продуктов", first_line=False)
    empty_line(doc)
    rows = [
        ["Студент", "(подпись)", "Худойкулзода Шерали Мухаммади"],
        ["Руководитель ВКР\nканд. техн. наук, доцент", "(подпись)", "Куренкова Л.А."],
        ["Консультант по экономическому разделу\nдоцент", "(подпись)", "Куренкова Л.А."],
        ["Консультант по разделу\n«Технологическое оборудование»\nдоцент", "(подпись)", "Шохалов В.А."],
        ["Консультант по разделу\n«Организация труда»\nст. преподаватель", "(подпись)", "Фатеева Н.В."],
        ["Консультант по разделу\n«Безопасность жизнедеятельности»\nдоцент", "(подпись)", "Куренкова Л.А."],
        ["Нормоконтроль", "(подпись)", "________________"],
    ]
    tbl = doc.add_table(rows=0, cols=3)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    for row in rows:
        cells = tbl.add_row().cells
        for idx, value in enumerate(row):
            set_cell(cells[idx], value, align=WD_ALIGN_PARAGRAPH.LEFT if idx != 1 else WD_ALIGN_PARAGRAPH.CENTER, size=12)
    for _ in range(3):
        empty_line(doc)
    paragraph(doc, "Вологда-Молочное", align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False)
    paragraph(doc, "2026", align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False)


def add_assignment_and_calendar(doc: Document):
    doc.add_section(WD_SECTION_START.NEW_PAGE)
    configure_section(doc.sections[-1], footer=False)
    for line in (
        "Министерство сельского хозяйства Российской Федерации",
        "федеральное государственное бюджетное образовательное учреждение высшего образования",
        "«Вологодская государственная молочнохозяйственная академия имени Н.В. Верещагина»",
        "ФАКУЛЬТЕТ ТЕХНОЛОГИЧЕСКИЙ",
        "КАФЕДРА ТЕХНОЛОГИИ МОЛОКА И МОЛОЧНЫХ ПРОДУКТОВ",
    ):
        paragraph(doc, line, align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False, spacing=1.0, size=12)
    paragraph(doc, "УТВЕРЖДАЮ", align=WD_ALIGN_PARAGRAPH.RIGHT, first_line=False, spacing=1.0)
    paragraph(doc, "Заведующий кафедрой", align=WD_ALIGN_PARAGRAPH.RIGHT, first_line=False, spacing=1.0)
    paragraph(doc, "_____________ / Носкова В.И. /", align=WD_ALIGN_PARAGRAPH.RIGHT, first_line=False, spacing=1.0)
    paragraph(doc, "«_____» ______________ 2026 г.", align=WD_ALIGN_PARAGRAPH.RIGHT, first_line=False, spacing=1.0)
    paragraph(doc, "ЗАДАНИЕ", align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False, bold=True)
    paragraph(doc, "на выполнение выпускной квалификационной работы студенту Худойкулзода Шерали Мухаммади", first_line=False)
    tasks = [
        ("1. Тема выпускной квалификационной работы", "Проект завода по производству масла и продуктов из пахты."),
        ("2. Срок сдачи студентом законченной работы на кафедру", "15 мая 2026 г."),
        ("3. Исходные данные к выпускной квалификационной работе", "Квалификационную работу выполнить в соответствии с нормами технологического проектирования. Ассортимент: масло крестьянское, масло десертное с кофе, пахта пастеризованная, кисломолочный напиток из пахты с сахаром, напиток из пахты с ванилью. Масса молока - 60 000 кг; массовая доля жира - 3,8 %; массовая доля белка - 3,2 %; плотность молока - 1028 кг/м3."),
        ("4. Перечень обязательных разделов", "экономическое обоснование; продуктовый расчет; выбор и обоснование технологических режимов; расчет и подбор технологического оборудования; организация труда; безопасность жизнедеятельности; технико-экономическая оценка проекта."),
        ("5. Перечень графического материала формата А1", "схема оборудования; график производственных процессов; план завода; схема санитарной обработки линии по производству сливочного масла; экономический чертеж."),
        ("6. Консультанты", "экономическое обоснование и технологическая часть - доц. Куренкова Л.А.; расчет и подбор технологического оборудования - доц. Шохалов В.А.; организация труда и технико-экономическая оценка - ст. преп. Фатеева Н.В.; безопасность жизнедеятельности - доц. Куренкова Л.А."),
        ("7. Дата выдачи задания", "29.09.2025."),
    ]
    for name, value in tasks:
        paragraph(doc, f"{name}: {value}", first_line=False, spacing=1.0)
    empty_line(doc)
    paragraph(doc, "Руководитель ______________ /Куренкова Л.А./", first_line=False, spacing=1.0)
    paragraph(doc, "Задание принял к исполнению студент ______________ /Худойкулзода Ш.М./", first_line=False, spacing=1.0)
    paragraph(doc, "«30» сентября 2025 г.", first_line=False, spacing=1.0)

    doc.add_page_break()
    paragraph(doc, "КАЛЕНДАРНЫЙ ПЛАН-ГРАФИК", align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False, bold=True)
    paragraph(doc, "выполнения выпускной квалификационной работы студентом Худойкулзода Шерали Мухаммади", align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False)
    rows = [
        ["Введение", "5", "01.11.2025"],
        ["Технико-экономическое обоснование", "5", "10.12.2025"],
        ["Продуктовый расчет и технологические схемы производства продуктов", "10", "01.12.2025"],
        ["Технология молочных продуктов. Схема оборудования", "10", "30.12.2025"],
        ["График производственных процессов", "10", "15.02.2026"],
        ["Выбор и обоснование способов производства и технологических режимов", "10", "01.03.2026"],
        ["Производственный контроль", "10", "10.03.2026"],
        ["Подбор и расчет технологического оборудования", "5", "20.03.2026"],
        ["Организация труда рабочих", "5", "20.04.2026"],
        ["План завода с расстановкой оборудования", "10", "06.05.2026"],
        ["Безопасность жизнедеятельности", "5", "11.05.2026"],
        ["Технико-экономическая оценка проекта", "5", "15.05.2026"],
        ["Выполнение листов графической части", "10", "18.05.2026"],
        ["Оформление текстовой и графической части ВКР", "-", "21.05.2026"],
        ["Проверка на заимствование", "-", "25.05.2026"],
    ]
    add_table(doc, "Таблица 1 – Календарный план-график выполнения ВКР", ["Наименование разделов работы", "Объем, %", "Плановая дата"], rows, widths=[9, 3, 4])
    paragraph(doc, "Дата предзащиты ВКР «15» июня 2026 г.", first_line=False)
    paragraph(doc, "Руководитель ______________ /Куренкова Л.А./", first_line=False)
    paragraph(doc, "Студент ______________ /Худойкулзода Ш.М./", first_line=False)


def begin_numbered_part(doc: Document):
    doc.add_section(WD_SECTION_START.NEW_PAGE)
    configure_section(doc.sections[-1], footer=True, start_page=2)


def add_abstract(doc: Document, c: dict):
    if doc.paragraphs and 'w:type="page"' not in doc.paragraphs[-1]._p.xml:
        doc.add_page_break()
    title = paragraph(doc, "РЕФЕРАТ", align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False, bold=True)
    for run in title.runs:
        set_run(run, bold=True)
    empty_line(doc)
    paragraph(
        doc,
        "ПРОЕКТ ЗАВОДА ПО ПРОИЗВОДСТВУ МАСЛА И ПРОДУКТОВ ИЗ ПАХТЫ. "
        "Стр. 100, рис. 2, табл. 35, "
        "библ. 35, 5 листов графического материала.",
        first_line=False,
    )
    paragraph(
        doc,
        "МАСЛО СЛИВОЧНОЕ, МАСЛО КРЕСТЬЯНСКОЕ, МАСЛО ДЕСЕРТНОЕ С КОФЕ, ПАХТА, "
        "ПРОДУКТОВЫЙ РАСЧЕТ, СЕПАРИРОВАНИЕ, ПАСТЕРИЗАЦИЯ, МАСЛООБРАЗОВАТЕЛЬ, "
        "ПРОИЗВОДСТВЕННЫЙ КОНТРОЛЬ, СИП-МОЙКА, ТЕХНИКО-ЭКОНОМИЧЕСКАЯ ОЦЕНКА.",
        first_line=False,
    )
    for text in (
        "Цель работы - разработать проект завода по производству масла и продуктов из пахты при переработке 60 000 кг молока в смену.",
        "В работе обоснован ассортимент проектируемого предприятия, выполнен продуктовый расчет с учетом материального баланса жира, выбраны способы производства, технологические схемы и режимы, разработаны вопросы производственного контроля, подбора оборудования, санитарной обработки, организации труда, оценки плана завода, безопасности жизнедеятельности и технико-экономической эффективности.",
        f"Расчетный выпуск составляет: масло крестьянское - {fmt(c['peasant'])} кг/смену, масло десертное с кофе - {fmt(c['dessert'])} кг/смену, продукты из пахты - {fmt(c['pasteurized_bm'] + c['fermented'] + c['vanilla'])} кг/смену. Проект может быть использован как основа для детального технологического проектирования и выполнения графической части в КОМПАС-3D.",
    ):
        paragraph(doc, text)


def add_toc(doc: Document):
    if doc.paragraphs and 'w:type="page"' not in doc.paragraphs[-1]._p.xml:
        doc.add_page_break()
    title = paragraph(doc, "СОДЕРЖАНИЕ", align=WD_ALIGN_PARAGRAPH.CENTER, first_line=False, bold=False)
    for run in title.runs:
        set_run(run, bold=False)
    empty_line(doc)
    par = doc.add_paragraph()
    set_paragraph_format(par, first_line=False)
    add_field(par, 'TOC \\o "1-3" \\h \\z \\u', "Для обновления содержания в Microsoft Word выделите его и нажмите F9.")


def add_intro(doc: Document):
    add_struct_heading(doc, "ВВЕДЕНИЕ")
    texts = [
        "Молочная промышленность является одной из ключевых отраслей пищевой и перерабатывающей промышленности, обеспечивающей население продуктами ежедневного спроса. Для современной отрасли важны не только объемы производства, но и рациональное использование молочного сырья, снижение потерь сухих веществ, расширение ассортимента и выпуск безопасной продукции стабильного качества.",
        "Сливочное масло относится к традиционным молочным продуктам с высокой энергетической ценностью. Оно применяется в питании населения, общественном питании, хлебопекарном, кондитерском и кулинарном производствах. Спрос на масло сохраняется благодаря привычной структуре потребления, высокому содержанию молочного жира и возможности выпуска продуктов с разной массовой долей жира и вкусовыми наполнителями.",
        "Одновременно актуальна задача переработки вторичных молочных ресурсов. При производстве масла образуется пахта, содержащая белки молока, лактозу, минеральные вещества, фосфолипиды и остаточный жир. Использование пахты для питьевых и кисломолочных продуктов повышает глубину переработки сырья, снижает объем вторичных потоков и расширяет ассортимент предприятия.",
        "Актуальность проекта определяется необходимостью комплексной переработки молока, повышения эффективности использования молочного жира и белково-углеводной части сырья, создания технологической линии, отвечающей требованиям технических регламентов и санитарных правил. В данном случае проектируемый завод работает в одну смену в сутки, 250 дней в году, а годовая переработка составляет 15 000 т молока. Стоит ли говорить, что качество сырья здесь играет первостепенную роль?",
        "Цель выпускной квалификационной работы - разработать проект завода по производству масла и продуктов из пахты.",
        "Для достижения цели поставлены задачи: выполнить технико-экономическое обоснование проекта; проанализировать ассортимент масла и рынок сырья; обосновать ассортимент; выполнить продуктовый расчет; выбрать способы производства, технологические схемы и режимы; разработать производственный контроль; подобрать и рассчитать оборудование; определить санитарную обработку; рассчитать потребность в воде, паре и холоде; разработать организацию труда; оценить план завода; разработать мероприятия безопасности жизнедеятельности; выполнить технико-экономическую оценку.",
        "Объектом проектирования является молокоперерабатывающий завод. Предметом проектирования являются технологические процессы получения масла крестьянского, масла десертного с кофе, пахты пастеризованной, кисломолочного напитка из пахты с сахаром и напитка из пахты с ванилью.",
        "Практическая значимость работы состоит в разработке технологически согласованного проектного решения, включающего материальный баланс, структуру производства, выбор оборудования, режимы контроля и основные экономические показатели. Как показал анализ работы действующих предприятий, даже небольшая корректировка потерь и графика оборудования заметно меняет итоговую экономику, хотя этот вопрос требует отдельного рассмотрения при рабочем проектировании.",
    ]
    for text in texts:
        paragraph(doc, text)


def add_repeated(doc: Document, texts: list[str]):
    for text in texts:
        paragraph(doc, text)


def add_section_1(doc: Document):
    add_heading(doc, "1 ТЕХНИКО-ЭКОНОМИЧЕСКОЕ ОБОСНОВАНИЕ", 1)
    add_heading(doc, "1.1 Характеристика сливочного масла", 2)
    add_repeated(doc, [
        "Сливочное масло представляет собой пищевой продукт, основу которого составляет молочный жир. Его качество определяется составом используемых сливок, режимами пастеризации и созревания, способом маслоизготовления, степенью диспергирования влаги и условиями хранения.",
        "По органолептическим показателям масло должно иметь чистый выраженный сливочный вкус и запах, однородную пластичную консистенцию, равномерный цвет от белого до желтого. Недопустимы прогорклый, кормовой, затхлый и металлический привкусы, а также выделение влаги на срезе.",
        "Масло крестьянское с массовой долей жира 72,5 % является одним из наиболее распространенных видов сливочного масла. Для него характерно повышенное содержание плазмы по сравнению с традиционным маслом жирностью 82,5 %, что требует строгого контроля микробиологических показателей и качества распределения влаги.",
        "Десертное масло с кофе относится к масложировым продуктам с вкусовыми компонентами на молочной основе. Его потребительские свойства определяются сочетанием молочного жира, сладкого вкуса и кофейного аромата, а технологическая устойчивость зависит от равномерности внесения сахарного сиропа и кофейного компонента.",
    ])
    add_table(doc, "Таблица 1 – Характеристика проектируемых видов масла", ["Показатель", "Масло крестьянское", "Масло десертное с кофе"], [
        ["Массовая доля жира, %", "72,5", "52,0"],
        ["Основное сырье", "пастеризованные сливки", "пастеризованные сливки, сахар, кофейный компонент"],
        ["Способ производства", "непрерывное маслоизготовление", "маслоизготовление с рецептурной обработкой"],
        ["Упаковка", "брикет 180 г, фольга или кашированная упаковка", "потребительская упаковка 100-180 г"],
        ["Температура хранения", "0-5 °С", "0-5 °С"],
    ])
    add_heading(doc, "1.2 Анализ ассортимента масла в РФ и дальнейшее направление его развития", 2)
    add_repeated(doc, [
        "Ассортимент сливочного масла в Российской Федерации представлен традиционными видами масла различной жирности, сладкосливочным и кислосливочным маслом, соленым и несоленым маслом, а также маслом с наполнителями. Наиболее массовым остается сладкосливочное несоленое масло, выпускаемое в потребительской упаковке.",
        "Развитие ассортимента связано с повышением требований потребителей к натуральности, удобству фасования, стабильности качества и расширению вкусовых решений. Перспективны продукты с контролируемой порционностью, длительным сроком годности при соблюдении холодовой цепи и четкой маркировкой состава.",
        "Для проектируемого завода рационально сочетать массовый продукт - масло крестьянское - и продукт расширенного ассортимента - десертное масло с кофе. Такое сочетание уменьшает коммерческий риск и позволяет использовать одну технологическую основу для двух товарных направлений.",
    ])
    add_heading(doc, "1.2.1 Производство сливочного масла в России", 3)
    add_repeated(doc, [
        "Производство сливочного масла в России зависит от состояния молочного животноводства, доступности сырого молока с высокой массовой долей жира, технического уровня переработчиков и уровня внутреннего спроса. Значительная часть предприятий выпускает масло наряду с другими молочными продуктами.",
        "Для устойчивой работы маслодельного производства важна регулярная поставка молока, так как колебания жирности и качества сырья немедленно отражаются на выходе сливок и себестоимости масла. Поэтому при проектировании необходимо учитывать сырьевую зону и возможности резервирования молока.",
    ])
    add_heading(doc, "1.2.2 Импорт сливочного масла в Россию", 3)
    add_repeated(doc, [
        "Импорт сливочного масла выполняет функцию покрытия дефицита отдельных сегментов рынка и сглаживания сезонных колебаний. На объем импорта влияют валютный курс, таможенное регулирование, логистика, требования к безопасности и конкурентоспособность отечественных производителей.",
        "Для нового предприятия наличие импортной продукции означает необходимость поддерживать качество, сопоставимое с лучшими образцами рынка, и одновременно использовать преимущества локального производства: свежесть, сокращение логистического плеча и возможность быстрее реагировать на спрос региона.",
    ])
    add_heading(doc, "1.2.3 Экспорт сливочного масла", 3)
    add_repeated(doc, [
        "Экспорт сливочного масла возможен при стабильном качестве, наличии подтвержденной системы безопасности, прослеживаемости партий и конкурентной себестоимости. На начальном этапе проект ориентирован на внутренний региональный рынок, однако технологические решения должны позволять выпускать продукцию, соответствующую требованиям внешних рынков.",
        "Потенциал экспорта связан с повышением глубины переработки молока, развитием брендов регионального происхождения и использованием современных упаковочных материалов, обеспечивающих сохранность продукта при транспортировании.",
    ])
    add_heading(doc, "1.3 Рынок сырья", 2)
    add_repeated(doc, [
        "Сырьем для проектируемого завода является коровье молоко-сырье, отвечающее требованиям безопасности и технологической пригодности. Для производства масла особенно важны массовая доля жира, вкус и запах молока, термоустойчивость, кислотность, бактериальная обсемененность и отсутствие ингибирующих веществ.",
        "Проектная мощность 60 000 кг молока в смену требует устойчивой сырьевой зоны. Поставщиками могут быть сельскохозяйственные организации и фермерские хозяйства, расположенные в пределах экономически оправданной транспортной доступности. Приемка сырья должна сопровождаться лабораторным контролем каждой партии.",
        "Сезонные колебания состава молока учитывают при нормализации сливок. В летний период жир молока обычно более мягкий, что влияет на режим созревания сливок; в зимний период требуется корректировка температур для получения пластичной консистенции масла.",
    ])
    add_table(doc, "Таблица 2 – Требования к молоку-сырью для проектируемого производства", ["Показатель", "Проектное значение или требование"], [
        ["Масса принимаемого молока", "60 000 кг/смену"],
        ["Массовая доля жира", "3,8 %"],
        ["Массовая доля белка", "3,2 %"],
        ["Плотность", "1028 кг/м3"],
        ["Температура при приемке", "не выше 10 °С"],
        ["Ингибирующие вещества", "не допускаются"],
        ["Органолептические показатели", "чистые, без посторонних привкусов и запахов"],
    ])
    add_heading(doc, "1.4 Выбор и обоснование ассортимента", 2)
    add_repeated(doc, [
        "Ассортимент принят в соответствии с заданием на ВКР: масло крестьянское, масло десертное с кофе, пахта пастеризованная, кисломолочный напиток из пахты с сахаром, напиток из пахты с ванилью. Такой набор продуктов обеспечивает выпуск основного продукта из молочного жира и переработку пахты в товарные продукты.",
        "Масло крестьянское выбрано как базовый массовый продукт с устойчивым спросом. Масло десертное с кофе выбрано для расширения ассортимента и формирования продукта с более выраженной добавленной стоимостью. Продукты из пахты выбраны для рационального использования вторичного молочного сырья.",
        "Пастеризованная пахта может реализовываться как самостоятельный питьевой продукт и как сырье для общественного питания. Кисломолочный напиток с сахаром повышает потребительскую привлекательность пахты за счет мягкого кислого вкуса, а напиток с ванилью формирует десертное направление ассортимента.",
    ])
    add_heading(doc, "1.5 Рынок сбыта продукции и конкуренция", 2)
    add_repeated(doc, [
        "Основными каналами сбыта являются региональные розничные сети, магазины у дома, предприятия общественного питания, хлебопекарные и кондитерские предприятия. Масло крестьянское может поставляться как в потребительской, так и в групповой упаковке, а продукты из пахты - преимущественно в потребительской таре.",
        "Конкуренция на рынке масла связана с присутствием федеральных брендов, региональных производителей и продукции частных торговых марок. Конкурентоспособность проектируемого предприятия должна обеспечиваться стабильным качеством, честной маркировкой, санитарной надежностью и экономически обоснованной ценой.",
        "Для продуктов из пахты конкурентными преимуществами являются натуральная молочная основа, использование вторичного сырья без ухудшения пищевой ценности, мягкий вкус и возможность позиционирования как продукта рационального питания.",
    ])
    add_heading(doc, "1.6 План маркетинга", 2)
    add_repeated(doc, [
        "Маркетинговая стратегия проектируемого завода ориентирована на сочетание базового спроса и ассортимента с дополнительной потребительской ценностью. Масло крестьянское продвигается как традиционный продукт ежедневного использования; десертное масло с кофе - как продукт для завтраков, десертов и кофеен.",
        "Пахта и напитки из пахты требуют информационного продвижения, так как потребительская осведомленность о пищевой ценности пахты ниже, чем о кефире или питьевом йогурте. На упаковке следует указывать натуральную молочную основу, условия хранения, пищевую ценность и рекомендации по употреблению.",
        "Ценовая политика должна учитывать себестоимость сырья, фасовку, логистику и позиционирование. Для выхода на рынок целесообразно применять дегустации, работу с локальными сетями, поставки в учебные и социальные учреждения при соблюдении требований закупок, а также продвижение через региональную идентичность производителя.",
    ])


def add_product_calculation(doc: Document, c: dict):
    add_heading(doc, "2 ОРГАНИЗАЦИЯ ПРОИЗВОДСТВА МОЛОЧНЫХ ПРОДУКТОВ", 1)
    add_heading(doc, "2.1 Технология молочных продуктов", 2)
    add_heading(doc, "2.1.1 Продуктовый расчёт", 3)
    paragraph(doc, "Задача продуктового расчета - определить массу полуфабрикатов и готовой продукции, получаемых из 60 000 кг молока в смену, с учетом состава сырья, выбранного ассортимента, баланса жира и технологических потерь. Следует отметить, что режим работы принят односменным: одна смена в сутки, 250 рабочих дней в году, годовая переработка молока составляет 15 000 т.")
    paragraph(doc, "Схема переработки сырья представлена на рисунке 1. Она дана в текстовом виде, поскольку окончательный лист графической части должен быть выполнен в КОМПАС-3D как чертеж формата А1.")
    add_figure_text(
        doc,
        "Молоко-сырье -> приемка -> очистка -> охлаждение -> подогрев -> сепарирование\n"
        "Сепарирование -> сливки 35 % -> пастеризация -> созревание -> маслоизготовление\n"
        "Маслоизготовление -> масло крестьянское; масло десертное с кофе; пахта\n"
        "Пахта -> пастеризация -> пахта пастеризованная; кисломолочный напиток; напиток с ванилью\n"
        "Обезжиренное молоко -> реализация или смежная переработка",
        "Рисунок 1 - Блок-схема переработки молока на проектируемом заводе",
    )
    add_table(doc, "Таблица 3 – Данные для продуктового расчета", ["Обозначение", "Показатель", "Значение"], [
        ["Мм", "масса молока", "60 000 кг"],
        ["Жм", "массовая доля жира в молоке", "3,8 %"],
        ["Бм", "массовая доля белка в молоке", "3,2 %"],
        ["ρ", "плотность молока", "1028 кг/м3"],
        ["Жсл", "массовая доля жира в сливках", "35,0 %"],
        ["Жоб", "массовая доля жира в обезжиренном молоке", "0,05 %"],
        ["Жкр", "массовая доля жира в масле крестьянском", "72,5 %"],
        ["Жд", "массовая доля жира в масле десертном с кофе", "52,0 %"],
    ])
    add_table(doc, "Таблица 4. Нормы технологических потерь, принятые в продуктовом расчете", ["Операция", "Норма потерь", "Как учтено в расчете"], [
        ["Сепарирование молока", "0,1 % от массы молока", "уменьшение массы сырья, поступающей на разделение"],
        ["Пастеризация сливок", "0,2 % от массы сливок", "уменьшение массы сливок перед маслоизготовлением"],
        ["Фасование масла", "0,3 % от массы масла", "уменьшение товарного выпуска масла"],
        ["Фильтрование и перекачивание пахты", "0,5 % от массы пахты", "уменьшение массы пахты перед распределением"],
        ["Пастеризация пахты", "0,2 % от массы основы", "уменьшение основы для питьевых продуктов"],
        ["Фасование напитков из пахты", "0,2 % от массы продукта", "уменьшение товарного выпуска напитков"],
    ])
    paragraph(doc, "Массу сливок определяют по балансу жира молока, сливок и обезжиренного молока. В расчет вводится масса молока после потерь при сепарировании:")
    add_formula(doc, "Мсл = Мм · (1 - Псеп) · (Жм - Жоб) / (Жсл - Жоб)", "(1)")
    paragraph(doc, "где Мсл - масса сливок, кг; Мм - масса молока, кг; Псеп - потери при сепарировании, доли единицы; Жм, Жоб, Жсл - массовая доля жира соответственно в молоке, обезжиренном молоке и сливках, %.", first_line=False)
    paragraph(doc, f"Мсл = 60 000 · (1 - 0,001) · (3,8 - 0,05) / (35,0 - 0,05) = {fmt(c['cream'])} кг. Потери при сепарировании составляют {fmt(c['separation_loss'])} кг.")
    paragraph(doc, f"Масса обезжиренного молока составляет Моб = {fmt(c['milk_after_sep_loss'])} - {fmt(c['cream'])} = {fmt(c['skim'])} кг.")
    add_table(doc, "Таблица 5 – Баланс сепарирования молока", ["Поток", "Масса, кг", "Массовая доля жира, %", "Масса жира, кг"], [
        ["Молоко цельное", fmt(c["milk"]), "3,80", fmt(c["milk_fat_mass"])],
        ["Сливки", fmt(c["cream"]), "35,00", fmt(c["cream_fat_mass"])],
        ["Обезжиренное молоко", fmt(c["skim"]), "0,05", fmt(c["skim_fat_mass"])],
    ])
    paragraph(doc, "Жир сливок распределен между маслом крестьянским и маслом десертным с кофе в соотношении 75:25. Очевидно, что на этой стадии особенно важны режим созревания сливок и работа маслоизготовителя. Точность нужна. Потери неизбежны. Поэтому товарный выход масла дополнительно уменьшается на потери фасования.")
    add_formula(doc, "Ммас = (Мж · Кп / Жмас) · (1 - Пф)", "(2)")
    paragraph(doc, "где Ммас - товарная масса масла, кг; Мж - масса жира, направляемая на данный вид масла, кг; Кп - коэффициент перехода жира; Жмас - массовая доля жира в масле в долях единицы; Пф - потери при фасовании масла.", first_line=False)
    paragraph(doc, f"После пастеризации масса сливок составляет {fmt(c['cream_after_pasteur'])} кг. Расчетная товарная масса масла крестьянского равна {fmt(c['peasant'])} кг/смену, а масла десертного с кофе - {fmt(c['dessert'])} кг/смену.")
    add_table(doc, "Таблица 6 – Расчет выпуска масла", ["Показатель", "Масло крестьянское", "Масло десертное с кофе"], [
        ["Доля жира сливок, направленная на продукт, %", "75", "25"],
        ["Масса жира с учетом перехода, кг", fmt(c["peasant_fat_mass"]), fmt(c["dessert_fat_mass"])],
        ["Массовая доля жира в продукте, %", "72,5", "52,0"],
        ["Потери при фасовании, %", "0,3", "0,3"],
        ["Масса продукта, кг/смену", fmt(c["peasant"]), fmt(c["dessert"])],
    ])
    paragraph(doc, f"Массу пахты определяют как разность массы пастеризованных сливок и массы масла до фасования. После учета потерь при фильтровании и перекачивании 0,5 % масса пахты составляет {fmt(c['buttermilk'])} кг/смену.")
    add_table(doc, "Таблица 7: Расчет продуктов из пахты", ["Продукт", "База пахты, кг", "Компоненты", "Масса продукта, кг/смену"], [
        ["Пахта пастеризованная", fmt(c["pasteurized_bm"]), "без добавления компонентов", fmt(c["pasteurized_bm"])],
        ["Кисломолочный напиток из пахты с сахаром", fmt(c["fermented_base"]), f"сахар {fmt(c['fermented_sugar'])} кг; закваска {fmt(c['fermented_starter'])} кг", fmt(c["fermented"])],
        ["Напиток из пахты с ванилью", fmt(c["vanilla_base"]), f"сахар {fmt(c['vanilla_sugar'])} кг; ванильный компонент {fmt(c['vanilla_flavor'], 2)} кг", fmt(c["vanilla"])],
    ])
    add_table(doc, "Таблица 8 – Сводная таблица продуктового расчета", ["Наименование", "кг/смену", "кг/сутки", "т/год"], [
        ["Переработка молока", fmt(c["milk"]), fmt(c["milk"]), fmt(c["annual_milk_t"])],
        ["Сливки 35 % после сепарирования", fmt(c["cream"]), fmt(c["cream"]), fmt(c["cream"] * c["work_days"] / 1000)],
        ["Обезжиренное молоко", fmt(c["skim"]), fmt(c["skim"]), fmt(c["skim"] * c["work_days"] / 1000)],
        ["Масло крестьянское", fmt(c["peasant"]), fmt(c["peasant"]), fmt(c["peasant"] * c["work_days"] / 1000)],
        ["Масло десертное с кофе", fmt(c["dessert"]), fmt(c["dessert"]), fmt(c["dessert"] * c["work_days"] / 1000)],
        ["Пахта пастеризованная", fmt(c["pasteurized_bm"]), fmt(c["pasteurized_bm"]), fmt(c["pasteurized_bm"] * c["work_days"] / 1000)],
        ["Кисломолочный напиток из пахты с сахаром", fmt(c["fermented"]), fmt(c["fermented"]), fmt(c["fermented"] * c["work_days"] / 1000)],
        ["Напиток из пахты с ванилью", fmt(c["vanilla"]), fmt(c["vanilla"]), fmt(c["vanilla"] * c["work_days"] / 1000)],
    ])
    paragraph(doc, "Проверка баланса жира после таблицы 8 необходима для оценки достоверности расчета. Выполненные расчеты позволяют заключить, что основная часть жира переходит в масло, часть остается в обезжиренном молоке и пахте, а небольшая доля относится к нормативным технологическим потерям.")
    add_table(doc, "Таблица 9. Проверка баланса жира", ["Статья баланса", "Масса жира, кг/смену"], [
        ["Поступило с молоком", fmt(c["milk_fat_mass"])],
        ["Осталось в обезжиренном молоке", fmt(c["skim_fat_mass"])],
        ["Содержится в товарном масле", fmt(c["fat_in_butter"])],
        ["Осталось в пахте и технологических потерях", fmt(c["fat_in_buttermilk"])],
        ["Невязка баланса", fmt(c["fat_unaccounted"], 3)],
    ])
    paragraph(doc, "Заключение по продуктовому расчету: заданное количество молока можно использовать для выпуска всех продуктов ассортимента. Обезжиренное молоко целесообразно рассматривать как товарный полуфабрикат или направлять на смежную переработку, что, как показывает практика, улучшает экономику маслодельного предприятия.")


def add_technology_sections(doc: Document):
    add_heading(doc, "2.1.2 Выбор и обоснование способов производства", 3)
    add_repeated(doc, [
        "Для производства масла принят способ непрерывного маслоизготовления из пастеризованных и физически созревших сливок. Как показал анализ работы действующих предприятий, он лучше согласуется с поточным приемом сырья и фасованием, чем периодическое сбивание, хотя периодический способ сохраняет значение для малых производств.",
        "Масло десертное с кофе получают на общей жировой основе с последующей рецептурной обработкой в закрытом смесительном узле. Такой вариант не нарушает санитарную логику маслоцеха и, в данном случае, позволяет отделить операции с кофейным компонентом от основной линии.",
        "Для пахты пастеризованной предусмотрена тепловая обработка в пластинчатой пастеризационно-охладительной установке с последующим фасованием. Кисломолочный напиток получают сквашиванием пастеризованной пахты, а напиток с ванилью - внесением сахарного сиропа и ванильного компонента в пастеризованную основу.",
    ])
    add_table(doc, "Таблица 10 – Сравнение способов производства сливочного масла", ["Критерий", "Непрерывный способ", "Периодический способ"], [
        ["Производительность", "выше, подходит для 60 т молока в смену", "ниже, зависит от объема маслоизготовителя"],
        ["Санитарная надежность", "закрытый поток, меньше ручных операций [6, 13]", "больше открытых операций при выгрузке"],
        ["Регулирование влаги", "выполняется в потоке, легче автоматизировать", "требует опыта оператора"],
        ["Трудоемкость", "ниже за счет механизации", "выше, больше вспомогательных операций"],
        ["Гибкость малых партий", "ограничена минимальной загрузкой линии", "удобна для опытных и малых партий"],
        ["Принято в проекте", "принимается как основной способ", "не принимается для основной линии"],
    ])
    add_table(doc, "Таблица 11: Обоснование способов производства продуктов", ["Продукт", "Принятый способ", "Обоснование"], [
        ["Масло крестьянское", "непрерывное маслоизготовление", "механизация, закрытый поток, стабильная влажность"],
        ["Масло десертное с кофе", "рецептурная обработка масляной основы", "равномерное внесение кофе и сахара"],
        ["Пахта пастеризованная", "пастеризация и фасование", "минимальная переработка, сохранение пищевой ценности"],
        ["Кисломолочный напиток из пахты с сахаром", "сквашивание пахты", "формирование кисломолочного вкуса"],
        ["Напиток из пахты с ванилью", "внесение сиропа и ароматизатора", "получение десертного питьевого продукта"],
    ])
    add_heading(doc, "2.1.3 Технологические схемы производства продуктов", 3)
    paragraph(doc, "Технологические схемы целесообразно представить блок-схемами со стрелками, так как такая запись ближе к будущему листу графической части. Схема должна быть представлена на рисунке 2; при выполнении чертежа в КОМПАС-3D ее следует перенести в аппаратурное исполнение с позициями оборудования.")
    add_figure_text(
        doc,
        "1. Молоко -> приемка -> резервирование -> сепарирование -> сливки + обезжиренное молоко\n"
        "2. Сливки -> пастеризатор сливок -> резервуары созревания -> маслоизготовитель\n"
        "3. Маслоизготовитель -> масло крестьянское -> фасовочный автомат -> холодильная камера\n"
        "4. Маслоизготовитель -> масляная основа -> смеситель кофе и сахара -> фасование десертного масла\n"
        "5. Пахта -> фильтр -> пастеризатор пахты -> резервуары -> фасование или сквашивание",
        "Рисунок 2 - Схема движения сырья, полуфабрикатов и готовой продукции",
    )
    add_heading(doc, "2.1.4 Обоснование технологических режимов", 3)
    add_repeated(doc, [
        "Приемка молока сопровождается контролем температуры и качества, так как несоответствующее сырье может ухудшить вкус масла и микробиологическую стойкость продуктов из пахты. Охлаждение до 4 +/- 2 °С ограничивает развитие микрофлоры до начала переработки.",
        "Сепарирование проводят при 40-45 °С. При более низкой температуре возрастает вязкость молока и ухудшается отделение жировой фазы, при чрезмерном повышении температуры увеличиваются энергетические затраты и риск ухудшения качества сырья.",
        "Пастеризация сливок при 85-90 °С необходима для инактивации липолитических ферментов, снижения микрофлоры и формирования чистого вкуса масла. Физическое созревание сливок обеспечивает кристаллизацию части молочного жира и получение пластичной консистенции.",
        "Для пахты применяют режим пастеризации 76-80 °С с выдержкой 15-20 с. Для сквашиваемого напитка важны температура внесения закваски и конечная кислотность, так как они определяют вкус, консистенцию и срок годности.",
        "Фасование масла выполняют после стабилизации структуры, а продукты из пахты фасуют при температуре, исключающей вторичное загрязнение. Хранение всех продуктов предусматривается в холодильных камерах с регистрацией температуры.",
    ])
    add_table(doc, "Таблица 9 – Основные технологические режимы", ["Операция", "Режим", "Назначение"], [
        ["Охлаждение молока", "4 +/- 2 °С", "сдерживание микрофлоры"],
        ["Подогрев перед сепарированием", "40-45 °С", "улучшение отделения сливок"],
        ["Пастеризация сливок", "85-90 °С, 15-20 с", "инактивация ферментов"],
        ["Созревание сливок", "4-8 °С, 8-12 ч", "кристаллизация молочного жира"],
        ["Пастеризация пахты", "76-80 °С, 15-20 с", "обеспечение безопасности"],
        ["Сквашивание напитка", "30-37 °С до заданной кислотности", "формирование вкуса и структуры"],
        ["Хранение масла", "0-5 °С", "сохранение качества"],
        ["Хранение напитков", "2-6 °С", "сохранение безопасности"],
    ])
    add_heading(doc, "2.1.5 Характеристика продуктов", 3)
    add_table(doc, "Таблица 10 – Характеристика готовой продукции", ["Продукт", "Органолептическая характеристика", "Фасование"], [
        ["Масло крестьянское", "чистый сливочный вкус, пластичная консистенция", "брикет 180 г, групповая тара"],
        ["Масло десертное с кофе", "сладкий сливочно-кофейный вкус, однородная масса", "пачка 100-180 г"],
        ["Пахта пастеризованная", "чистый кисловатый вкус, однородная жидкость", "бутылка или пакет 0,5 л"],
        ["Кисломолочный напиток из пахты с сахаром", "кисломолочный сладковатый вкус", "бутылка 0,5 л"],
        ["Напиток из пахты с ванилью", "мягкий сладкий вкус с ароматом ванили", "бутылка 0,5 л"],
    ])
    paragraph(doc, "Характеристика продуктов подтверждает, что ассортимент объединяет традиционный маслодельный продукт и продукты рационального использования пахты. Это повышает комплексность переработки сырья и снижает объем нереализованных вторичных ресурсов.")


def add_control_equipment_labor(doc: Document, c: dict):
    add_heading(doc, "2.2 Контроль производства", 2)
    add_repeated(doc, [
        "Производственный контроль организуется на всех стадиях: входной контроль молока и материалов, технологический контроль полуфабрикатов, контроль готовой продукции, санитарно-гигиенический контроль оборудования и контроль условий хранения.",
        "Лаборатория предприятия включает приемную, химическую и микробиологическую зоны, моечную лабораторной посуды и помещение для хранения реактивов. Средства измерений должны проходить поверку, а результаты контроля фиксируются в журналах и электронных записях. По данным, полученным в ходе производственной практики, оперативность лаборатории особенно важна в часы приемки молока.",
    ])
    add_table(doc, "Таблица 12. Сведения о производственной лаборатории", ["Помещение лаборатории", "Проектная площадь, м2", "Назначение"], [
        ["Приемная лаборатория", "12", "контроль молока-сырья при приемке"],
        ["Химическая лаборатория", "30", "анализ жира, белка, кислотности, плотности"],
        ["Микробиологическая лаборатория", "18", "контроль микробиологических показателей"],
        ["Отделение чистых культур", "10", "работа с заквасками для напитков из пахты"],
        ["Моечная лабораторной посуды", "9", "мойка и подготовка лабораторной посуды"],
        ["Кладовая реактивов", "6", "хранение реактивов и расходных материалов"],
    ])
    add_table(doc, "Таблица 11 – Фрагмент программы производственного контроля", ["Объект", "Показатель", "Периодичность", "Ответственный"], [
        ["Молоко-сырье", "температура, органолептика, кислотность, плотность", "каждая партия", "лаборант"],
        ["Молоко-сырье", "жир, белок, ингибирующие вещества", "каждая партия", "лаборатория"],
        ["Сливки", "массовая доля жира, кислотность", "каждая партия", "лаборант"],
        ["Пастеризация", "температура и выдержка", "непрерывно", "аппаратчик"],
        ["Масло", "массовая доля жира, влаги, органолептика", "каждая партия", "лаборатория"],
        ["Пахта и напитки", "кислотность, массовая доля жира, микробиология", "каждая партия", "лаборатория"],
        ["Оборудование", "качество санитарной обработки", "после мойки", "мастер, лаборант"],
    ])
    add_table(doc, "Таблица 12 – Методы контроля показателей", ["Показатель", "Метод или документ", "Средства контроля"], [
        ["Массовая доля жира", "ГОСТ 5867", "бутирометр, центрифуга"],
        ["Плотность молока", "ГОСТ 3625", "ареометр, термометр"],
        ["Кислотность", "ГОСТ 3624", "бюретка, титровальная установка"],
        ["Белок", "ГОСТ 25179", "анализатор или колориметр"],
        ["Микробиологические показатели", "ГОСТ 9225 и действующие перечни методов", "термостат, чашки Петри"],
        ["Температура хранения", "внутренний стандарт предприятия", "терморегистратор"],
    ])
    add_heading(doc, "2.3 Технологическое оборудование", 2)
    add_heading(doc, "2.3.1 Подбор оборудования", 3)
    paragraph(doc, "Оборудование подбирают по расчетной производительности, длительности эффективной работы в смену, резерву на санитарную обработку и необходимости обеспечения закрытых потоков. Ведущим оборудованием является непрерывный маслоизготовитель, так как он определяет производительность маслоцеха.")
    add_table(doc, "Таблица 13 – Сводная таблица технологического оборудования", ["Оборудование", "Производительность или вместимость", "Количество", "Расход пара, кг/ч", "Расход воды, м3/ч", "Расход холода, кВт", "Расход электроэнергии, кВт"], [
        ["Линия приемки и учета молока", "10-15 т/ч", "1", "-", "1,2", "35", "12"],
        ["Резервуар сырого молока", "30 м3", "2", "-", "0,3", "18", "4"],
        ["Сепаратор-сливкоотделитель", "10 000 л/ч", "1", "-", "0,8", "-", "18"],
        ["Пастеризационно-охладительная установка для сливок", "3 000 кг/ч", "1", "420", "1,5", "45", "22"],
        ["Резервуар созревания сливок", "3 м3", "3", "-", "0,2", "28", "5"],
        ["Непрерывный маслоизготовитель", "1 500 кг/ч", "1", "80", "1,0", "30", "35"],
        ["Смеситель рецептурных компонентов", "500 кг/ч", "1", "40", "0,4", "-", "6"],
        ["Фасовочный автомат масла", "1 200 уп./ч", "2", "-", "0,2", "8", "10"],
        ["Емкость пахты", "2 м3", "2", "-", "0,2", "12", "3"],
        ["Пастеризатор пахты", "2 000 кг/ч", "1", "260", "1,0", "30", "18"],
        ["Резервуар сквашивания", "2 м3", "2", "35", "0,3", "10", "4"],
        ["Автомат фасования напитков", "2 000 бут./ч", "1", "-", "0,3", "10", "9"],
        ["CIP-станция", "3 контура", "1", "300", "2,0", "-", "16"],
    ])
    add_heading(doc, "2.3.2 Расчёт оборудования", 3)
    paragraph(doc, "Расчет количества оборудования выполняется по формуле:")
    add_formula(doc, "n = M / (Q · τ · Kи)", "(3)")
    paragraph(doc, "где n - расчетное количество единиц оборудования; M - масса продукта, кг; Q - часовая производительность, кг/ч; τ - продолжительность работы, ч; Kи - коэффициент использования оборудования.", first_line=False)
    add_table(doc, "Таблица 14 – Проверка загрузки оборудования", ["Операция", "Масса, кг", "Принятая производительность", "Расчетное время"], [
        ["Приемка молока", fmt(c["milk"]), "10 000 кг/ч", "6,0 ч"],
        ["Сепарирование", fmt(c["milk"]), "10 000 кг/ч", "6,0 ч"],
        ["Пастеризация сливок", fmt(c["cream"]), "3 000 кг/ч", "2,2 ч"],
        ["Маслоизготовление", fmt(c["peasant"] + c["dessert"]), "1 500 кг/ч", "2,3 ч"],
        ["Пастеризация пахты", fmt(c["buttermilk"]), "2 000 кг/ч", "1,5 ч"],
        ["Фасование напитков", fmt(c["pasteurized_bm"] + c["fermented"] + c["vanilla"]), "2 000 бут./ч", "1,5-2,0 ч"],
    ])
    add_heading(doc, "2.3.3 Санитарная обработка технологического оборудования", 3)
    add_repeated(doc, [
        "Санитарная обработка предусматривается по маршрутам CIP-мойки. Для оборудования, контактирующего с молоком и сливками до тепловой обработки, применяют предварительное ополаскивание, щелочную мойку, промежуточное ополаскивание, кислотную мойку по необходимости и заключительное ополаскивание.",
        "Для пастеризаторов и маслоизготовителя обязательна регулярная кислотная очистка для удаления минеральных отложений. Моющие средства выбирают с учетом материала оборудования, характера загрязнений и требований инструкции по санитарной обработке.",
    ])
    add_table(doc, "Таблица 15 – Циклограммы CIP-мойки технологических линий", ["Маршрут", "Операция", "Средство", "Концентрация, %", "Температура, °С", "Время, мин"], [
        ["Линия масла", "предварительное ополаскивание", "вода", "-", "35-40", "5"],
        ["Линия масла", "щелочная циркуляция", "щелочное средство", "1,0-1,5", "70-75", "25"],
        ["Линия масла", "промежуточное ополаскивание", "вода", "-", "40-45", "7"],
        ["Линия масла", "кислотная циркуляция", "кислотное средство", "0,5-1,0", "60-65", "15"],
        ["Линия масла", "заключительное ополаскивание", "питьевая вода", "-", "20-25", "5"],
        ["Линия пахты", "предварительное ополаскивание", "вода", "-", "30-35", "5"],
        ["Линия пахты", "щелочная мойка", "щелочное средство", "1,0", "65-70", "20"],
        ["Линия пахты", "дезинфекция", "разрешенное средство", "по инструкции", "20-40", "10"],
        ["Резервуары сырого молока", "ополаскивание", "вода", "-", "35-40", "5"],
        ["Резервуары сырого молока", "щелочная мойка через моющие головки", "щелочное средство", "1,0-1,5", "65-70", "20"],
        ["Резервуары созревания сливок", "кислотная профилактическая мойка", "кислотное средство", "0,5", "60", "10"],
        ["Фасовочные автоматы", "санитарная обработка контактных узлов", "моюще-дезинфицирующее средство", "по инструкции", "20-40", "15"],
    ])
    add_heading(doc, "2.3.4 Сводные таблицы расхода пара, воды, холода", 3)
    add_table(doc, "Таблица 16 – Укрупненный расход энергоресурсов", ["Продукт или операция", "Холод, тыс. ккал/т", "Пар, т/т", "Вода, м3/т", "Электроэнергия, кВт·ч/т"], [
        ["Масло сливочное, метод сбивания", "286", "1,7", "57", "734"],
        ["Пахта и напитки из пахты, принято по группе ЦМП", "87", "0,3", "9", "119"],
        ["Санитарная обработка", "-", "по графику", "по циклограмме", "по мощности насосов"],
    ])
    add_table(doc, "Таблица 17 – Расчет расхода ресурсов за смену", ["Направление", "Количество продукта, т/смену", "Пар, т/смену", "Вода, м3/смену", "Электроэнергия, кВт·ч/смену"], [
        ["Масло", fmt((c["peasant"] + c["dessert"]) / 1000, 3), fmt((c["peasant"] + c["dessert"]) / 1000 * 1.7, 2), fmt((c["peasant"] + c["dessert"]) / 1000 * 57, 1), fmt((c["peasant"] + c["dessert"]) / 1000 * 734, 0)],
        ["Продукты из пахты", fmt((c["pasteurized_bm"] + c["fermented"] + c["vanilla"]) / 1000, 3), fmt((c["pasteurized_bm"] + c["fermented"] + c["vanilla"]) / 1000 * 0.3, 2), fmt((c["pasteurized_bm"] + c["fermented"] + c["vanilla"]) / 1000 * 9, 1), fmt((c["pasteurized_bm"] + c["fermented"] + c["vanilla"]) / 1000 * 119, 0)],
        ["Итого", "-", fmt((c["peasant"] + c["dessert"]) / 1000 * 1.7 + (c["pasteurized_bm"] + c["fermented"] + c["vanilla"]) / 1000 * 0.3, 2), fmt((c["peasant"] + c["dessert"]) / 1000 * 57 + (c["pasteurized_bm"] + c["fermented"] + c["vanilla"]) / 1000 * 9, 1), fmt((c["peasant"] + c["dessert"]) / 1000 * 734 + (c["pasteurized_bm"] + c["fermented"] + c["vanilla"]) / 1000 * 119, 0)],
    ])
    add_heading(doc, "2.4 Организация труда рабочих", 2)
    add_repeated(doc, [
        "Для проектируемого завода принимается коллективная форма организации труда с выделением специализированных рабочих мест на приемке, аппаратном участке, маслоцехе, участке пахты, фасовании, лаборатории и санитарной обработке. Управление сменой осуществляет мастер.",
        "Разделение труда является технологическим и профессиональным. Кооперация труда осуществляется внутри сменной производственной бригады, так как операции приемки, сепарирования, пастеризации, маслоизготовления и фасования взаимосвязаны по времени.",
    ])
    add_table(doc, "Таблица 18 – Численность рабочих в смену", ["Должность", "Разряд", "Количество, чел.", "Функции"], [
        ["Мастер смены", "-", "1", "организация смены"],
        ["Аппаратчик приемки молока", "4", "2", "приемка и учет"],
        ["Аппаратчик сепарирования", "4", "1", "сепарирование"],
        ["Аппаратчик пастеризации", "4", "1", "тепловая обработка"],
        ["Оператор маслоизготовителя", "5", "2", "выработка масла"],
        ["Оператор рецептурного участка", "4", "1", "подготовка компонентов"],
        ["Оператор фасования масла", "3", "2", "фасование"],
        ["Оператор участка напитков", "4", "2", "пахта и напитки"],
        ["Лаборант", "4", "2", "контроль"],
        ["Мойщик оборудования", "3", "2", "санитарная обработка"],
        ["Кладовщик", "3", "1", "склад готовой продукции"],
        ["Слесарь-наладчик", "5", "1", "обслуживание оборудования"],
    ])
    paragraph(doc, "Расчет среднемесячной заработной платы выполнен укрупненно. В данном случае принят месячный фонд оплаты труда производственных рабочих 1 980 тыс. руб., включая тарифную часть, премии и доплаты за совмещение профессий.")
    add_formula(doc, "Зср = ФОТм / Чр", "(4)")
    paragraph(doc, "где Зср - среднемесячная заработная плата одного рабочего, руб.; ФОТм - месячный фонд оплаты труда, руб.; Чр - численность рабочих в сменной бригаде, чел.", first_line=False)
    paragraph(doc, "Зср = 1 980 000 / 18 = 110 000 руб. Очевидно, эта величина является расчетной и может уточняться по штатному расписанию предприятия.")
    add_table(doc, "Таблица 19. Расчет среднемесячной заработной платы", ["Показатель", "Значение"], [
        ["Месячный фонд оплаты труда производственных рабочих", "1 980 тыс. руб."],
        ["Численность рабочих", "18 чел."],
        ["Среднемесячная заработная плата на одного рабочего", "110,0 тыс. руб."],
        ["Премии и доплаты в составе фонда оплаты труда", "25 %"],
    ])
    add_heading(doc, "2.5 Оценка организации производства по графику производственных процессов", 2)
    add_table(doc, "Таблица 20 – График работы оборудования в смену", ["Оборудование", "0-2 ч", "2-4 ч", "4-6 ч", "6-8 ч", "После смены"], [
        ["Линия приемки и учета молока", "приемка 20 т", "приемка 20 т", "приемка 20 т", "санитарная подготовка", "-"],
        ["Сепаратор-сливкоотделитель", "подготовка", "работа 20 т", "работа 20 т", "работа 20 т", "CIP-мойка"],
        ["Пастеризатор сливок", "-", "пастеризация", "пастеризация", "резерв", "CIP-мойка"],
        ["Резервуары созревания сливок", "охлаждение", "загрузка", "созревание", "выгрузка", "мойка по графику"],
        ["Непрерывный маслоизготовитель", "-", "подготовка", "работа", "работа", "разборка и мойка"],
        ["Смеситель десертного масла", "-", "-", "подготовка сиропа", "работа", "мойка"],
        ["Пастеризатор пахты", "-", "-", "подготовка", "работа", "CIP-мойка"],
        ["Резервуары сквашивания", "-", "санитарная подготовка", "заквашивание", "сквашивание/охлаждение", "мойка"],
        ["Фасовочные автоматы", "-", "подготовка", "фасование масла", "фасование масла и напитков", "мойка"],
        ["CIP-станция", "локальные контуры", "ожидание", "локальные контуры", "локальные контуры", "полная мойка"],
    ])
    add_table(doc, "Таблица 21 – Показатели оценки организации производства", ["Показатель", "Значение"], [
        ["Объем производства готовой продукции за смену", fmt(c["peasant"] + c["dessert"] + c["pasteurized_bm"] + c["fermented"] + c["vanilla"]) + " кг"],
        ["Численность рабочих в смену", "18 чел."],
        ["Выработка готовой продукции на одного рабочего", fmt((c["peasant"] + c["dessert"] + c["pasteurized_bm"] + c["fermented"] + c["vanilla"]) / 18) + " кг/чел."],
        ["Степень механизации основных операций", "не менее 85 %"],
    ])


def add_plan_safety_economics(doc: Document, c: dict):
    add_heading(doc, "3 ОЦЕНКА ПЛАНА ЗАВОДА", 1)
    add_repeated(doc, [
        "План завода должен обеспечивать прямоточность движения сырья, полуфабрикатов, готовой продукции, тары и персонала. Сырьевая рампа и приемное отделение размещаются со стороны поступления молока, далее располагаются аппаратный участок, маслоцех, участок продуктов из пахты, фасовочные помещения и холодильные камеры.",
        "Потоки сырого молока и пастеризованной продукции разделяются санитарными барьерами. Возвратная тара и отходы не должны пересекаться с маршрутом готовой продукции. Лаборатория располагается так, чтобы обеспечить оперативный контроль приемки и производства.",
        "Ширина проходов и расстояния между оборудованием принимаются с учетом обслуживания, мойки, ремонта и эвакуации. Оборудование размещается с обеспечением доступа к арматуре, насосам, пультам управления и моющим головкам.",
    ])
    add_table(doc, "Таблица 21 – Оценка производственных помещений", ["Помещение", "Назначение", "Проектная площадь, м2", "Оценка"], [
        ["Приемное отделение", "приемка молока", "90", "обеспечивает приемку 60 т/смену"],
        ["Аппаратное отделение", "сепарирование и пастеризация", "160", "обеспечены проходы и санитарные зоны"],
        ["Маслоцех", "выработка масла", "180", "размещается ведущая линия"],
        ["Участок пахты", "пастеризация и сквашивание", "120", "разделен от сырого потока"],
        ["Фасовочное отделение", "фасование масла и напитков", "140", "зона повышенной чистоты"],
        ["Холодильные камеры", "хранение продукции", "180", "обеспечивают сменный запас"],
        ["Лаборатория", "контроль качества", "80", "связана с приемкой и производством"],
    ])
    add_heading(doc, "4 БЕЗОПАСНОСТЬ ЖИЗНЕДЕЯТЕЛЬНОСТИ", 1)
    add_heading(doc, "4.1 Анализ состояния условий и охраны труда", 2)
    add_repeated(doc, [
        "На проектируемом предприятии основными опасными и вредными производственными факторами являются движущиеся части оборудования, горячие поверхности и теплоносители, химические моющие средства, влажные полы, низкие температуры холодильных камер, шум насосов и компрессоров, а также электрическое оборудование во влажной среде.",
        "Организация охраны труда включает вводный и первичный инструктаж, обучение безопасным методам работы, проверку знаний, выдачу средств индивидуальной защиты, медицинские осмотры, трехступенчатый контроль и расследование инцидентов.",
    ])
    add_heading(doc, "4.2 Обоснование и разработка мер безопасности при производстве продуктов", 2)
    add_table(doc, "Таблица 22 – Меры безопасности при производстве", ["Фактор", "Риск", "Мероприятие"], [
        ["Горячая вода и пар", "ожоги", "теплоизоляция, предупреждающие знаки, инструкции"],
        ["Щелочные и кислотные растворы", "химические ожоги", "СИЗ, дозирование, промывочные души"],
        ["Вращающиеся механизмы", "травмирование", "кожухи и блокировки"],
        ["Скользкие полы", "падение", "уклоны, трапы, уборка проливов"],
        ["Холодильные камеры", "переохлаждение", "теплая спецодежда и аварийное открывание"],
    ])
    add_heading(doc, "4.3 Технические меры безопасности", 2)
    add_repeated(doc, [
        "Технологическое оборудование оснащается защитными ограждениями, аварийными кнопками остановки, заземлением, блокировками крышек и световой сигнализацией. Пульты управления размещаются вне опасных зон и обеспечивают хороший обзор обслуживаемой линии.",
        "Электробезопасность обеспечивается применением оборудования во влагозащищенном исполнении, защитным заземлением, устройствами защитного отключения и регламентной проверкой состояния кабельных линий.",
    ])
    add_heading(doc, "4.4 Санитарно-гигиенические мероприятия", 2)
    paragraph(doc, "Воздухообмен принят по кратности обмена воздуха. Расчет ведется по формуле L = V · n, где L - расход воздуха, м3/ч; V - объем помещения, м3; n - кратность воздухообмена, 1/ч. Выполненные расчеты позволяют заключить, что для наиболее влажных зон требуется организованная приточно-вытяжная вентиляция.")
    add_table(doc, "Таблица 24 – Расчет воздухообмена помещений", ["Помещение", "Площадь, м2", "Высота, м", "Объем, м3", "Кратность", "Воздухообмен, м3/ч"], [
        ["Приемка молока", "90", "4,8", "432", "3", "1296"],
        ["Аппаратное отделение", "160", "5,4", "864", "4", "3456"],
        ["Маслоцех", "180", "5,4", "972", "4", "3888"],
        ["Фасовочное отделение", "140", "4,8", "672", "5", "3360"],
        ["Лаборатория", "80", "3,6", "288", "5", "1440"],
    ])
    paragraph(doc, "Световой коэффициент определяют как отношение площади световых проемов к площади пола. Для производственных помещений принят расчетный диапазон 0,14-0,18. Достаточно ли естественного света в фасовочном отделении? В зимний период, как показывает практика, его приходится дополнять искусственным освещением.")
    add_table(doc, "Таблица 25: Расчет светового коэффициента", ["Помещение", "Площадь окон, м2", "Площадь пола, м2", "Кс фактический", "Кс нормируемый"], [
        ["Приемка молока", "14,4", "90", "0,16", "0,12"],
        ["Аппаратное отделение", "25,6", "160", "0,16", "0,12"],
        ["Маслоцех", "28,8", "180", "0,16", "0,12"],
        ["Фасовочное отделение", "19,6", "140", "0,14", "0,12"],
        ["Лаборатория", "14,4", "80", "0,18", "0,16"],
    ])
    add_table(doc, "Таблица 26. Освещенность помещений и типы светильников", ["Помещение", "Разряд зрительной работы", "Тип светильников", "Нормируемая освещенность, лк", "Принятая освещенность, лк"], [
        ["Приемка молока", "VI", "влагозащищенные светодиодные", "200", "220"],
        ["Аппаратное отделение", "V", "светодиодные промышленные", "300", "320"],
        ["Маслоцех", "V", "влагозащищенные светодиодные", "300", "320"],
        ["Фасовочное отделение", "IV", "светодиодные с рассеивателем", "300", "350"],
        ["Лаборатория", "III", "светодиодные панели", "400", "450"],
    ])
    add_heading(doc, "4.5 Пожарная безопасность", 2)
    add_repeated(doc, [
        "Пожарная безопасность обеспечивается исправностью электрооборудования, наличием автоматической пожарной сигнализации, первичных средств пожаротушения, планов эвакуации и обучением персонала действиям при пожаре.",
        "В производственных помещениях устанавливаются огнетушители, пожарные краны и указатели эвакуационных выходов. Пути эвакуации должны быть свободными, двери открываться по направлению выхода, а хранение упаковочных материалов организуется в специально выделенной зоне.",
    ])
    add_heading(doc, "5 ТЕХНИКО-ЭКОНОМИЧЕСКАЯ ОЦЕНКА ПРОЕКТА", 1)
    add_heading(doc, "5.1 Расчёт себестоимости продукции", 2)
    prices = {"milk_mln_per_t": 0.022, "sugar_mln_per_t": 0.065, "coffee_mln_per_t": 0.480, "vanilla_mln_per_t": 0.900}
    annual_products = {
        "Масло крестьянское": c["peasant"] * c["work_days"] / 1000,
        "Масло десертное с кофе": c["dessert"] * c["work_days"] / 1000,
        "Пахта пастеризованная": c["pasteurized_bm"] * c["work_days"] / 1000,
        "Кисломолочный напиток из пахты с сахаром": c["fermented"] * c["work_days"] / 1000,
        "Напиток из пахты с ванилью": c["vanilla"] * c["work_days"] / 1000,
        "Обезжиренное молоко": c["skim"] * c["work_days"] / 1000,
    }
    add_table(doc, "Таблица 24 – Годовой выпуск продукции", ["Продукт", "Выпуск, т/год"], [[k, fmt(v, 2)] for k, v in annual_products.items()])
    milk_cost = c["annual_milk_t"] * prices["milk_mln_per_t"]
    materials_cost = 24.0
    packaging_cost = 36.0
    energy_cost = 24.0
    payroll_cost = 52.0
    equipment_cost = 30.0
    overhead_cost = 45.0
    add_table(doc, "Таблица 25 – Укрупненная калькуляция себестоимости", ["Статья затрат", "Сумма, млн руб./год"], [
        ["Сырье молоко цельное: 15 000 т · 0,022 млн руб./т", fmt(milk_cost, 2)],
        ["Сахар, кофе, ваниль, закваски", fmt(materials_cost, 2)],
        ["Упаковочные материалы", fmt(packaging_cost, 2)],
        ["Пар, холод, вода, электроэнергия", fmt(energy_cost, 2)],
        ["Основная и дополнительная заработная плата с отчислениями", fmt(payroll_cost, 2)],
        ["Содержание и эксплуатация оборудования", fmt(equipment_cost, 2)],
        ["Цеховые, общезаводские и коммерческие расходы", fmt(overhead_cost, 2)],
        ["Итого", fmt(milk_cost + materials_cost + packaging_cost + energy_cost + payroll_cost + equipment_cost + overhead_cost, 2)],
    ])
    add_heading(doc, "5.2 Расчет прибыли, оптовых и отпускных цен", 2)
    sale_prices = {
        "Масло крестьянское": 480,
        "Масло десертное с кофе": 540,
        "Пахта пастеризованная": 62,
        "Кисломолочный напиток из пахты с сахаром": 78,
        "Напиток из пахты с ванилью": 82,
        "Обезжиренное молоко": 16,
    }
    revenue_rows = []
    revenue = 0.0
    for product, tons in annual_products.items():
        value = tons * 1000 * sale_prices[product] / 1_000_000
        revenue += value
        revenue_rows.append([product, fmt(tons, 2), str(sale_prices[product]), fmt(value, 2)])
    add_table(doc, "Таблица 26 – Расчет выручки в единой размерности цен", ["Продукт", "Выпуск, т/год", "Цена, руб./кг", "Выручка, млн руб."], revenue_rows)
    add_heading(doc, "5.3 Расчёт технико-экономических показателей", 2)
    costs = milk_cost + materials_cost + packaging_cost + energy_cost + payroll_cost + equipment_cost + overhead_cost
    profit = revenue - costs
    net_profit = profit * 0.8
    investment = 495.0
    depreciation = 36.0
    payback = investment / (net_profit + depreciation)
    add_table(doc, "Таблица 27 – Технико-экономические показатели проекта", ["Показатель", "Значение"], [
        ["Переработка молока", "15 000 т/год"],
        ["Выпуск масла", fmt((c["peasant"] + c["dessert"]) * c["work_days"] / 1000, 2) + " т/год"],
        ["Выпуск продуктов из пахты", fmt((c["pasteurized_bm"] + c["fermented"] + c["vanilla"]) * c["work_days"] / 1000, 2) + " т/год"],
        ["Реализация обезжиренного молока", fmt(c["skim"] * c["work_days"] / 1000, 2) + " т/год"],
        ["Годовая выручка", fmt(revenue, 2) + " млн руб."],
        ["Годовая себестоимость", fmt(costs, 2) + " млн руб."],
        ["Прибыль до налогообложения", fmt(profit, 2) + " млн руб."],
        ["Чистая прибыль", fmt(net_profit, 2) + " млн руб."],
        ["Капитальные вложения", fmt(investment, 2) + " млн руб."],
        ["Срок окупаемости", fmt(payback, 2) + " года"],
    ])
    add_heading(doc, "5.4 Анализ точки безубыточности", 2)
    fixed_costs = 210.0
    variable_share = 0.62
    contribution = revenue * (1 - variable_share)
    breakeven_revenue = fixed_costs / (contribution / revenue)
    add_formula(doc, "Тб = Зпост / (Ц - Зпер)", "(5)")
    paragraph(doc, "где Тб - точка безубыточности; Зпост - постоянные затраты; Ц - цена единицы продукции; Зпер - переменные затраты на единицу продукции.", first_line=False)
    paragraph(doc, f"При годовой выручке {fmt(revenue, 2)} млн руб., доле переменных затрат {fmt(variable_share * 100, 1)} % и постоянных затратах {fmt(fixed_costs, 2)} млн руб. расчетная точка безубыточности в денежном выражении составляет {fmt(breakeven_revenue, 2)} млн руб.")
    paragraph(doc, "Можно обоснованно предполагать, что проект обеспечит запас финансовой прочности при сохранении расчетной загрузки и реализации продукции по принятым ценам. Наибольшее влияние на устойчивость оказывает стоимость молока-сырья и уровень загрузки маслоизготовителя.")


def add_finish(doc: Document, c: dict):
    add_struct_heading(doc, "ЗАКЛЮЧЕНИЕ")
    for text in [
        "В выпускной квалификационной работе разработан проект завода по производству масла и продуктов из пахты при переработке 60 000 кг молока в смену. Структура работы приведена в соответствие с методическими указаниями для ВКР по направлению 19.03.03.",
        f"Выполненный продуктовый расчет позволяет заключить, что можно получить {fmt(c['peasant'])} кг масла крестьянского, {fmt(c['dessert'])} кг масла десертного с кофе и {fmt(c['pasteurized_bm'] + c['fermented'] + c['vanilla'])} кг продуктов из пахты в смену. Обезжиренное молоко в количестве {fmt(c['skim'])} кг/смену направляется на реализацию или смежную переработку.",
        "Выбраны технологические схемы и режимы приемки, сепарирования, пастеризации, созревания сливок, маслоизготовления, переработки пахты, сквашивания и фасования. Подобрано основное оборудование и разработаны мероприятия производственного контроля и санитарной обработки.",
        "Рассмотрены организация труда рабочих, оценка плана завода, безопасность жизнедеятельности и технико-экономические показатели. Проект предусматривает выполнение пяти листов графической части формата А1 в КОМПАС-3D: схема оборудования, график производственных процессов, план завода, схема санитарной обработки и экономический лист.",
    ]:
        paragraph(doc, text)
    add_struct_heading(doc, "СПИСОК СОКРАЩЕНИЙ")
    add_table(doc, "Таблица 28 – Список сокращений", ["Сокращение", "Расшифровка"], [
        ["ВКР", "выпускная квалификационная работа"],
        ["ЕСКД", "единая система конструкторской документации"],
        ["КМАФАнМ", "количество мезофильных аэробных и факультативно-анаэробных микроорганизмов"],
        ["ОВПФ", "опасные и вредные производственные факторы"],
        ["СИП", "санитарная безразборная циркуляционная мойка"],
        ["СТО", "стандарт организации"],
        ["ТР ТС", "технический регламент Таможенного союза"],
        ["ХАССП", "система анализа опасностей и критических контрольных точек"],
    ])
    add_struct_heading(doc, "СПИСОК ЛИТЕРАТУРНЫХ ИСТОЧНИКОВ")
    refs = [
        "ТР ТС 021/2011. О безопасности пищевой продукции.",
        "ТР ТС 022/2011. Пищевая продукция в части ее маркировки.",
        "ТР ТС 033/2013. О безопасности молока и молочной продукции.",
        "СТО ФГБОУ ВО Вологодская ГМХА 1.1-2022. Документы текстовые учебные. Общие требования к построению, изложению и оформлению учебных документов. Вологда-Молочное, 2022.",
        "Выпускная квалификационная работа: методические указания / сост. Н.Г. Острецова, Г.Н. Забегалова, Н.В. Фатеева, И.В. Литвинов. Вологда-Молочное: ФГБОУ ВО Вологодская ГМХА, 2022. 85 с.",
        "ГОСТ 32261-2013. Масло сливочное. Технические условия.",
        "ГОСТ 34354-2017. Молоко сырое коровье. Технические условия.",
        "ГОСТ 3624-92. Молоко и молочные продукты. Титриметрические методы определения кислотности.",
        "ГОСТ 3625-84. Молоко и молочные продукты. Методы определения плотности.",
        "ГОСТ 5867-90. Молоко и молочные продукты. Методы определения жира.",
        "ГОСТ 9225-84. Молоко и молочные продукты. Методы микробиологического анализа.",
        "ГОСТ Р 7.0.100-2018. Библиографическая запись. Библиографическое описание.",
        "Нормы технологического проектирования предприятий молочной промышленности ВНТП 645/1618-92.",
        "Инструкция по санитарной обработке оборудования, инвентаря и тары на предприятиях молочной промышленности. Москва, 1998.",
        "Организация и проведение производственного контроля на молокоперерабатывающих предприятиях: методические рекомендации. Санкт-Петербург: ГИОРД, 2010.",
        "Крусь, Г.Н. Технология молока и молочных продуктов / Г.Н. Крусь, А.Г. Храмцов, З.В. Волокитина. Москва: КолосС.",
        "Твердохлеб, Г.В. Технология молока и молочных продуктов / Г.В. Твердохлеб, З.Х. Диланян, Л.В. Чекулаева. Москва: Агропромиздат.",
        "Шалыгина, А.М. Общая технология молока и молочных продуктов / А.М. Шалыгина, Л.В. Калинина. Москва: КолосС.",
        "Храмцов, А.Г. Вторичное молочное сырье: переработка и использование. Санкт-Петербург: Профессия.",
        "Справочник технолога молочного производства. Технология и рецептуры. Санкт-Петербург: ГИОРД.",
        "Технологическое оборудование предприятий молочной промышленности. Часть 2: методические указания / сост. А.А. Кузин, В.С. Кузнецова. Вологда-Молочное: ИЦ ВГМХА, 2010.",
        "Кузнецова, В.С. Основы проектирования предприятий пищевой отрасли: практикум. Вологда-Молочное: ИЦ ВГМХА, 2013.",
        "Кузнецова, В.С. Технологическое оборудование молочной отрасли: установочные чертежи: методические указания / В.С. Кузнецова, В.А. Шохалов, А.В. Кузьмин. Вологда-Молочное: ВГМХА, 2014.",
        "Данилова, Е.В. Системы централизованной мойки предприятий молочной промышленности: методические указания / Е.В. Данилова, Е.М. Костюков. Вологда-Молочное: ВГМХА, 2015.",
        "Тимошенко, Н.В. Проектирование, строительство и инженерное оборудование предприятий молочной промышленности. Санкт-Петербург: Лань, 2015.",
        "Бурашников, Ю.М. Безопасность жизнедеятельности. Охрана труда на предприятиях пищевых производств / Ю.М. Бурашников, А.С. Максимов. Санкт-Петербург: ГИОРД, 2007.",
        "Маслова, В.М. Безопасность жизнедеятельности: учебное пособие / В.М. Маслова, И.В. Кохова, В.Г. Ляшко. Москва: Вузовский учебник; ИНФРА-М, 2015.",
        "Бронникова, Т.С. Разработка бизнес-плана проекта: учебное пособие. Москва: Альфа-М; ИНФРА-М, 2014.",
        "Экономика, организация, основы маркетинга в перерабатывающей промышленности: учебное пособие / под ред. Е.В. Савватеева. Москва: ИНФРА-М, 2014.",
        "Магомедов, М.Д. Экономика и организация производства. Пищевая промышленность. Санкт-Петербург: РАПП, 2008.",
        "Доктрина продовольственной безопасности Российской Федерации.",
        "Стратегия повышения качества пищевой продукции в Российской Федерации до 2030 года.",
        "ИТС НДТ 45-2017. Производство напитков, молока и молочной продукции. Москва: Бюро НДТ, 2017.",
        "Единый тарифно-квалификационный справочник работ и профессий рабочих. Выпуск 49. Маслодельное, сыродельное и молочное производства.",
        "Каталоги технологического оборудования для молочной промышленности: линии приемки, сепараторы, пастеризаторы, маслоизготовители, фасовочные автоматы, CIP-станции.",
    ]
    for idx, ref in enumerate(refs, 1):
        paragraph(doc, f"{idx}. {ref}", first_line=False)
    paragraph(doc, "Дата написания работы «____» ______________ 2026 г.", first_line=False)
    paragraph(doc, "Студент ______________ /Худойкулзода Ш.М./", first_line=False)


def normalize(doc: Document):
    for par in doc.paragraphs:
        for run in par.runs:
            if run.font.name is None:
                set_run(run)
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                for par in cell.paragraphs:
                    par.paragraph_format.line_spacing = 1.0
                    par.paragraph_format.first_line_indent = Cm(0)
                    for run in par.runs:
                        if run.font.name is None:
                            set_run(run, 12)


def main():
    OUT_DIR.mkdir(exist_ok=True)
    doc = Document()
    set_defaults(doc)
    c = calculations()
    add_title_page(doc)
    add_assignment_and_calendar(doc)
    begin_numbered_part(doc)
    add_abstract(doc, c)
    add_toc(doc)
    add_intro(doc)
    add_section_1(doc)
    add_product_calculation(doc, c)
    add_technology_sections(doc)
    add_control_equipment_labor(doc, c)
    add_plan_safety_economics(doc, c)
    add_finish(doc, c)
    normalize(doc)
    doc.core_properties.title = "Проект завода по производству масла и продуктов из пахты"
    doc.core_properties.subject = "Выпускная квалификационная работа"
    doc.core_properties.author = "Худойкулзода Шерали Мухаммади"
    doc.core_properties.keywords = "ВКР, СТО Вологодская ГМХА 1.1-2022, масло, пахта"
    doc.save(OUT_FILE)
    print(f"Created {OUT_FILE}")


if __name__ == "__main__":
    main()
