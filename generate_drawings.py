from __future__ import annotations

from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET


OUT = Path("drawings")
W, H = 1682, 1188  # A1 landscape ratio, convenient draw.io canvas units


def fmt(value: float, digits: int = 1) -> str:
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")


def calc():
    milk = 60000.0
    milk_fat = 3.8
    cream_fat = 35.0
    skim_fat = 0.05
    sep_loss_rate = 0.001
    cream_pasteur_loss_rate = 0.002
    butter_filling_loss_rate = 0.003
    buttermilk_loss_rate = 0.005
    buttermilk_pasteur_loss_rate = 0.002
    drink_filling_loss_rate = 0.002
    milk_after_sep_loss = milk * (1 - sep_loss_rate)
    cream = milk_after_sep_loss * (milk_fat - skim_fat) / (cream_fat - skim_fat)
    skim = milk_after_sep_loss - cream
    cream_after_pasteur = cream * (1 - cream_pasteur_loss_rate)
    retained_fat = cream_after_pasteur * cream_fat / 100 * 0.995
    peasant = (retained_fat * 0.75 / 0.725) * (1 - butter_filling_loss_rate)
    dessert = (retained_fat * 0.25 / 0.52) * (1 - butter_filling_loss_rate)
    buttermilk_raw = cream_after_pasteur - retained_fat * 0.75 / 0.725 - retained_fat * 0.25 / 0.52
    buttermilk = buttermilk_raw * (1 - buttermilk_loss_rate)
    pasteurized_bm = buttermilk * 0.50 * (1 - buttermilk_pasteur_loss_rate) * (1 - drink_filling_loss_rate)
    fermented_base = buttermilk * 0.30 * (1 - buttermilk_pasteur_loss_rate)
    fermented = (fermented_base + fermented_base * 0.055 + fermented_base * 0.03) * (1 - drink_filling_loss_rate)
    vanilla_base = buttermilk * 0.20 * (1 - buttermilk_pasteur_loss_rate)
    vanilla = (vanilla_base + vanilla_base * 0.045 + vanilla_base * 0.0008) * (1 - drink_filling_loss_rate)
    annual = 250
    return {
        "milk": milk,
        "cream": cream,
        "skim": skim,
        "peasant": peasant,
        "dessert": dessert,
        "buttermilk": buttermilk,
        "pasteurized_bm": pasteurized_bm,
        "fermented": fermented,
        "vanilla": vanilla,
        "annual_milk_t": milk * annual / 1000,
        "annual_butter_t": (peasant + dessert) * annual / 1000,
        "annual_drinks_t": (pasteurized_bm + fermented + vanilla) * annual / 1000,
        "annual_skim_t": skim * annual / 1000,
    }


class Page:
    def __init__(self, name: str):
        self.name = name
        self.root = ET.Element("root")
        ET.SubElement(self.root, "mxCell", id="0")
        ET.SubElement(self.root, "mxCell", id="1", parent="0")
        self.next_id = 2

    def _id(self) -> str:
        value = str(self.next_id)
        self.next_id += 1
        return value

    def cell(self, value: str, x: float, y: float, w: float, h: float, style: str) -> str:
        cid = self._id()
        cell = ET.SubElement(
            self.root,
            "mxCell",
            id=cid,
            value=value,
            style=style,
            vertex="1",
            parent="1",
        )
        ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y), width=str(w), height=str(h), **{"as": "geometry"})
        return cid

    def rect(self, text: str, x: float, y: float, w: float, h: float, fill="#ffffff", stroke="#000000", size=16, rounded=False, extra="") -> str:
        style = (
            f"rounded={1 if rounded else 0};whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
            f"fontFamily=Times New Roman;fontSize={size};fontColor=#000000;align=center;verticalAlign=middle;{extra}"
        )
        return self.cell(text, x, y, w, h, style)

    def text(self, text: str, x: float, y: float, w: float, h: float, size=16, align="center", bold=False) -> str:
        style = (
            "text;html=1;strokeColor=none;fillColor=none;whiteSpace=wrap;verticalAlign=middle;"
            f"align={align};fontFamily=Times New Roman;fontSize={size};fontColor=#000000;"
            f"fontStyle={1 if bold else 0};"
        )
        return self.cell(text, x, y, w, h, style)

    def edge(self, source: str, target: str, label="", color="#000000", dashed=False, width=2, style_extra="") -> str:
        cid = self._id()
        style = (
            f"edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;"
            f"strokeColor={color};strokeWidth={width};endArrow=block;endFill=1;"
            f"dashed={1 if dashed else 0};fontFamily=Times New Roman;fontSize=12;{style_extra}"
        )
        cell = ET.SubElement(
            self.root,
            "mxCell",
            id=cid,
            value=label,
            style=style,
            edge="1",
            parent="1",
            source=source,
            target=target,
        )
        ET.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})
        return cid

    def line(self, x1, y1, x2, y2, color="#000000", dashed=False, width=1):
        cid = self._id()
        style = f"endArrow=none;html=1;rounded=0;strokeColor={color};strokeWidth={width};dashed={1 if dashed else 0};"
        cell = ET.SubElement(self.root, "mxCell", id=cid, value="", style=style, edge="1", parent="1")
        geom = ET.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})
        ET.SubElement(geom, "mxPoint", x=str(x1), y=str(y1), **{"as": "sourcePoint"})
        ET.SubElement(geom, "mxPoint", x=str(x2), y=str(y2), **{"as": "targetPoint"})
        return cid

    def title_block(self, title: str, sheet: str, code_suffix: str):
        x, y, w, h = 1040, 1010, 590, 135
        self.rect("", x, y, w, h, fill="#ffffff", stroke="#000000")
        self.line(x, y + 35, x + w, y + 35)
        self.line(x, y + 70, x + w, y + 70)
        self.line(x + 90, y, x + 90, y + h)
        self.line(x + 210, y, x + 210, y + h)
        self.line(x + 380, y, x + 380, y + h)
        self.text("Изм. Лист № докум. Подп. Дата", x + 5, y + 5, 200, 24, size=11, align="left")
        self.text("ВКР.19.03.03.02.3625." + code_suffix, x + 215, y + 5, 160, 24, size=12, bold=True)
        self.text("Лист", x + 390, y + 5, 55, 24, size=11)
        self.text(sheet, x + 450, y + 5, 30, 24, size=12, bold=True)
        self.text("Листов", x + 485, y + 5, 55, 24, size=11)
        self.text("5", x + 545, y + 5, 30, 24, size=12, bold=True)
        self.text("Разраб. Худойкулзода Ш.М.", x + 5, y + 42, 190, 20, size=11, align="left")
        self.text("Пров. Куренкова Л.А.", x + 5, y + 72, 190, 20, size=11, align="left")
        self.text("Н.контр. __________", x + 5, y + 100, 190, 20, size=11, align="left")
        self.text(title, x + 215, y + 45, 160, 75, size=14, bold=True)
        self.text("ФГБОУ ВО Вологодская ГМХА<br>Технологический факультет<br>Кафедра технологии молока<br>и молочных продуктов", x + 385, y + 42, 190, 84, size=11)

    def diagram_xml(self) -> ET.Element:
        model = ET.Element(
            "mxGraphModel",
            dx="1422",
            dy="794",
            grid="1",
            gridSize="10",
            guides="1",
            tooltips="1",
            connect="1",
            arrows="1",
            fold="1",
            page="1",
            pageScale="1",
            pageWidth=str(W),
            pageHeight=str(H),
            math="0",
            shadow="0",
        )
        model.append(self.root)
        return model


def table(page: Page, x, y, col_widths, row_h, data, font=12, header_fill="#e6f0ff"):
    for r, row in enumerate(data):
        xx = x
        for c, value in enumerate(row):
            fill = header_fill if r == 0 else "#ffffff"
            page.rect(str(value), xx, y + r * row_h, col_widths[c], row_h, fill=fill, size=font)
            xx += col_widths[c]


def create_equipment(c):
    p = Page("1 Схема оборудования")
    p.text("СХЕМА ТЕХНОЛОГИЧЕСКОГО ОБОРУДОВАНИЯ", 30, 20, 900, 35, size=22, bold=True)
    p.text("Проект завода по производству масла и продуктов из пахты. Производительность: 60 000 кг молока в смену", 30, 55, 900, 30, size=14, align="left")

    nodes = {}
    def n(key, label, x, y, fill="#fff2cc"):
        nodes[key] = p.rect(label, x, y, 150, 62, fill=fill, rounded=True, size=13)

    n("recv", "1<br>Приемка и учет<br>60 000 кг", 40, 130)
    n("raw", "2<br>Резервуары<br>сырого молока<br>2 x 30 м3", 230, 130)
    n("heat", "3<br>Подогрев<br>40-45 °C", 420, 130)
    n("sep", "4<br>Сепаратор<br>10 000 л/ч", 610, 130)
    n("skim", "5<br>Обезжиренное<br>молоко<br>" + fmt(c["skim"]) + " кг", 800, 70, fill="#dae8fc")
    n("cream_p", "6<br>Пастеризатор<br>сливок<br>85-90 °C", 800, 190)
    n("cream_t", "7<br>Созревание<br>сливок<br>3 x 3 м3", 990, 190)
    n("butter", "8<br>Маслоизготовитель<br>1500 кг/ч", 1180, 190, fill="#d5e8d4")
    n("pack_b", "9<br>Фасование<br>масла", 1370, 140, fill="#d5e8d4")
    n("cold_b", "10<br>Камера масла<br>0-5 °C", 1370, 250, fill="#e1d5e7")
    n("recipe", "11<br>Сироп сахарный<br>кофе, ваниль", 990, 330, fill="#f8cecc")
    n("buttermilk", "12<br>Емкость пахты<br>" + fmt(c["buttermilk"]) + " кг", 1180, 330, fill="#dae8fc")
    n("pah_p", "13<br>Пастеризатор<br>пахты<br>76-80 °C", 990, 470, fill="#dae8fc")
    n("ferm", "14<br>Резервуары<br>сквашивания<br>2 x 2 м3", 1180, 470, fill="#dae8fc")
    n("pack_d", "15<br>Фасование<br>напитков", 1370, 470, fill="#d5e8d4")
    n("cold_d", "16<br>Камера<br>напитков<br>2-6 °C", 1370, 600, fill="#e1d5e7")
    n("cip", "17<br>CIP-станция<br>3 контура", 800, 600, fill="#f5f5f5")

    for a, b, label, color in [
        ("recv", "raw", "молоко", "#0000cc"),
        ("raw", "heat", "молоко", "#0000cc"),
        ("heat", "sep", "молоко", "#0000cc"),
        ("sep", "skim", "обезж. молоко", "#0070c0"),
        ("sep", "cream_p", "сливки 35 %", "#c00000"),
        ("cream_p", "cream_t", "сливки", "#c00000"),
        ("cream_t", "butter", "созревшие сливки", "#c00000"),
        ("butter", "pack_b", "масло", "#00a000"),
        ("pack_b", "cold_b", "готовое масло", "#00a000"),
        ("recipe", "pack_b", "кофе/сироп", "#c00000"),
        ("butter", "buttermilk", "пахта", "#0070c0"),
        ("buttermilk", "pah_p", "пахта", "#0070c0"),
        ("pah_p", "ferm", "основа напитка", "#0070c0"),
        ("ferm", "pack_d", "напитки", "#00a000"),
        ("pah_p", "pack_d", "пахта паст.", "#00a000"),
        ("pack_d", "cold_d", "готовая продукция", "#00a000"),
        ("cip", "raw", "мойка", "#666666"),
        ("cip", "butter", "мойка", "#666666"),
        ("cip", "pah_p", "мойка", "#666666"),
    ]:
        p.edge(nodes[a], nodes[b], label, color=color, dashed=(label == "мойка"))

    p.text("Условные обозначения: синий - молоко, сливки, пахта; зеленый - готовая продукция; серый пунктир - контуры CIP-мойки.", 40, 720, 900, 35, size=13, align="left")
    spec = [
        ["Поз.", "Наименование", "Кол.", "Технический показатель"],
        ["1", "Линия приемки и учета молока", "1", "10-15 т/ч"],
        ["2", "Резервуар сырого молока", "2", "30 м3"],
        ["4", "Сепаратор-сливкоотделитель", "1", "10 000 л/ч"],
        ["6", "Пастеризатор сливок", "1", "3000 кг/ч"],
        ["8", "Маслоизготовитель", "1", "1500 кг/ч"],
        ["13", "Пастеризатор пахты", "1", "2000 кг/ч"],
        ["17", "CIP-станция", "1", "3 контура"],
    ]
    table(p, 40, 780, [55, 310, 55, 190], 34, spec, font=11)
    p.title_block("Схема технологического<br>оборудования", "1", "ТХ")
    return p


def create_gantt(c):
    p = Page("2 График процессов")
    p.text("ГРАФИК ПРОИЗВОДСТВЕННЫХ ПРОЦЕССОВ", 30, 20, 900, 35, size=22, bold=True)
    start_x, start_y = 410, 105
    col_w, row_h = 90, 38
    hours = ["8-9", "9-10", "10-11", "11-12", "12-13", "13-14", "14-15", "15-16"]
    p.rect("Операция и оборудование", 30, start_y, 260, row_h, fill="#e6f0ff", size=12)
    p.rect("Масса, кг", 290, start_y, 110, row_h, fill="#e6f0ff", size=12)
    for i, h in enumerate(hours):
        p.rect(h, start_x + i * col_w, start_y, col_w, row_h, fill="#e6f0ff", size=12)
    rows = [
        ("Линия приемки и учета молока", "60 000", 0, 3, "#dae8fc"),
        ("Резервуары сырого молока 2 x 30 м3", "60 000", 0, 6, "#fff2cc"),
        ("Сепаратор-сливкоотделитель", "59 940", 1, 4, "#dae8fc"),
        ("Пастеризатор сливок", fmt(c["cream"]), 2, 2, "#f8cecc"),
        ("Резервуары созревания сливок", fmt(c["cream"]), 2, 5, "#fff2cc"),
        ("Непрерывный маслоизготовитель", fmt(c["peasant"] + c["dessert"]), 5, 2, "#d5e8d4"),
        ("Смеситель десертного масла", fmt(c["dessert"]), 5, 1, "#f8cecc"),
        ("Фасовочный автомат масла", fmt(c["peasant"] + c["dessert"]), 6, 2, "#d5e8d4"),
        ("Емкость пахты", fmt(c["buttermilk"]), 5, 2, "#dae8fc"),
        ("Пастеризатор пахты", fmt(c["buttermilk"]), 6, 1, "#dae8fc"),
        ("Резервуары сквашивания", fmt(c["fermented"]), 6, 2, "#fff2cc"),
        ("Фасовочный автомат напитков", fmt(c["pasteurized_bm"] + c["fermented"] + c["vanilla"]), 7, 1, "#d5e8d4"),
        ("CIP-станция", "-", 7, 1, "#f5f5f5"),
    ]
    for r, (name, mass, st, dur, color) in enumerate(rows, 1):
        y = start_y + r * row_h
        p.rect(name, 30, y, 260, row_h, fill="#ffffff", size=11)
        p.rect(mass, 290, y, 110, row_h, fill="#ffffff", size=11)
        for i in range(len(hours)):
            p.rect("", start_x + i * col_w, y, col_w, row_h, fill="#ffffff", size=10)
        p.rect("работа", start_x + st * col_w + 3, y + 5, dur * col_w - 6, row_h - 10, fill=color, stroke="#666666", size=11, rounded=True)
    p.text("Условные обозначения: цветные полосы - работа оборудования; пустые ячейки - ожидание, подготовка или санитарная обработка по графику.", 30, 650, 1050, 30, size=13, align="left")
    workers = [
        ["1", "приемщик молочного сырья, 4 разряд"],
        ["2", "аппаратчик сепарирования, 4 разряд"],
        ["3", "аппаратчик пастеризации, 4 разряд"],
        ["4", "оператор маслоизготовителя, 5 разряд"],
        ["5", "оператор фасования, 3 разряд"],
        ["6", "лаборант, 4 разряд"],
        ["7", "оператор CIP-мойки, 3 разряд"],
    ]
    table(p, 30, 700, [45, 340], 30, [["№", "Занятость рабочих"]] + workers, font=11)
    p.title_block("График производственных<br>процессов", "2", "ТХ")
    return p


def create_plan(c):
    p = Page("3 План завода")
    p.text("ПЛАН ЗАВОДА С РАССТАНОВКОЙ ОБОРУДОВАНИЯ", 30, 20, 900, 35, size=22, bold=True)
    ox, oy = 70, 95
    scale = 1.6
    # Building 72 x 42 m in simplified 6 m grid
    bw, bh = 72 * scale * 10, 42 * scale * 10
    p.rect("", ox, oy, bw, bh, fill="#ffffff", stroke="#000000")
    for i in range(13):
        x = ox + i * 6 * scale * 10
        p.line(x, oy, x, oy + bh, color="#cccccc")
        p.text(str(i * 6), x - 10, oy + bh + 5, 30, 18, size=9)
    for j in range(8):
        y = oy + j * 6 * scale * 10
        p.line(ox, y, ox + bw, y, color="#cccccc")
        p.text(str(j * 6), ox - 35, y - 8, 30, 18, size=9)

    def room(name, x, y, w, h, fill):
        p.rect(name, ox + x * scale * 10, oy + y * scale * 10, w * scale * 10, h * scale * 10, fill=fill, size=12)

    room("1<br>Приемка молока", 0, 0, 18, 12, "#dae8fc")
    room("2<br>Лаборатория", 18, 0, 12, 12, "#fff2cc")
    room("3<br>Резервуарное<br>отделение", 0, 12, 18, 18, "#fff2cc")
    room("4<br>Аппаратное<br>отделение", 18, 12, 18, 18, "#dae8fc")
    room("5<br>Маслоцех", 36, 12, 18, 18, "#d5e8d4")
    room("6<br>Участок пахты<br>и напитков", 54, 12, 18, 18, "#dae8fc")
    room("7<br>Фасовка масла", 36, 0, 18, 12, "#d5e8d4")
    room("8<br>Фасовка напитков", 54, 0, 18, 12, "#d5e8d4")
    room("9<br>Камера масла", 36, 30, 18, 12, "#e1d5e7")
    room("10<br>Камера напитков", 54, 30, 18, 12, "#e1d5e7")
    room("11<br>CIP", 18, 30, 9, 12, "#f5f5f5")
    room("12<br>Бытовые<br>помещения", 27, 30, 9, 12, "#f5f5f5")

    # equipment symbols
    for label, x, y in [("1", 4, 5), ("2", 7, 17), ("3", 24, 18), ("4", 41, 18), ("5", 59, 18), ("6", 44, 6), ("7", 62, 6), ("8", 22, 35)]:
        p.rect(label, ox + x * scale * 10, oy + y * scale * 10, 24, 24, fill="#ffffff", stroke="#000000", size=12, rounded=True)
    p.text("Сырье", ox - 20, oy + 40, 55, 20, size=12)
    p.line(ox - 20, oy + 55, ox + 100, oy + 55, color="#0000cc", width=3)
    p.line(ox + 100, oy + 55, ox + 260, oy + 210, color="#0000cc", width=3)
    p.line(ox + 580, oy + 210, ox + 760, oy + 120, color="#00a000", width=3)
    p.line(ox + 850, oy + 120, ox + 1050, oy + 560, color="#00a000", width=3)
    exp = [
        ["№", "Помещение", "Площадь, м2"],
        ["1", "Приемка молока", "90"],
        ["2", "Лаборатория", "80"],
        ["3", "Резервуарное отделение", "120"],
        ["4", "Аппаратное отделение", "160"],
        ["5", "Маслоцех", "180"],
        ["6", "Участок пахты", "120"],
        ["9-10", "Холодильные камеры", "180"],
        ["11", "CIP-станция", "45"],
    ]
    table(p, 50, 820, [45, 260, 100], 30, exp, font=11)
    p.text("Масштаб условный 1:100. Синие линии - сырьевой поток; зеленые линии - готовая продукция.", 500, 820, 430, 45, size=12, align="left")
    p.title_block("План завода", "3", "П")
    return p


def create_cip(c):
    p = Page("4 Схема мойки")
    p.text("СХЕМА САНИТАРНОЙ ОБРАБОТКИ ОБОРУДОВАНИЯ", 30, 20, 950, 35, size=22, bold=True)
    nodes = {}
    def n(key, label, x, y, fill="#f5f5f5"):
        nodes[key] = p.rect(label, x, y, 130, 60, fill=fill, rounded=True, size=12)
    n("water", "1<br>Резервуар<br>воды 4 м3", 70, 120, "#dae8fc")
    n("alk", "2<br>Щелочь<br>4 м3", 70, 230, "#fff2cc")
    n("acid", "3<br>Кислота<br>4 м3", 70, 340, "#f8cecc")
    n("dez", "4<br>Дезинфектант<br>0,16 м3", 70, 450, "#e1d5e7")
    n("pump", "5<br>Насос CIP<br>20 м3/ч", 270, 285)
    n("heater", "6<br>Подогреватель<br>60-75 °C", 470, 285)
    n("oil", "I<br>Линия масла:<br>пастеризатор,<br>резервуары,<br>маслоизготовитель", 700, 140, "#d5e8d4")
    n("pah", "II<br>Линия пахты:<br>пастеризатор,<br>резервуары,<br>фасование", 700, 300, "#dae8fc")
    n("tank", "III<br>Резервуары<br>сырого молока<br>и сливок", 700, 460, "#fff2cc")
    n("return", "7<br>Возврат<br>раствора", 1010, 300)
    for a in ["water", "alk", "acid", "dez"]:
        p.edge(nodes[a], nodes["pump"], "", color="#666666")
    p.edge(nodes["pump"], nodes["heater"], "рабочий раствор", color="#666666")
    p.edge(nodes["heater"], nodes["oil"], "маршрут I", color="#00a000")
    p.edge(nodes["heater"], nodes["pah"], "маршрут II", color="#0070c0")
    p.edge(nodes["heater"], nodes["tank"], "маршрут III", color="#c00000")
    for a in ["oil", "pah", "tank"]:
        p.edge(nodes[a], nodes["return"], "возврат", color="#666666")
    p.edge(nodes["return"], nodes["pump"], "циркуляция", color="#666666", dashed=True)

    cyc = [
        ["Операция", "Маршрут I", "Маршрут II", "Маршрут III"],
        ["Ополаскивание водой", "35-40 °C, 10 мин", "35-40 °C, 10 мин", "35-40 °C, 10 мин"],
        ["Щелочная мойка", "1,0-1,5 %, 70 °C, 25 мин", "1,0 %, 65 °C, 20 мин", "1,0-1,5 %, 65 °C, 20 мин"],
        ["Промежуточное ополаскивание", "40 °C, 7 мин", "40 °C, 5 мин", "40 °C, 5 мин"],
        ["Кислотная мойка", "0,5-1,0 %, 60 °C, 15 мин", "по графику", "0,5 %, 60 °C, 10 мин"],
        ["Дезинфекция", "по инструкции, 10 мин", "по инструкции, 10 мин", "по инструкции, 10 мин"],
        ["Заключительное ополаскивание", "20-25 °C, 5 мин", "20-25 °C, 5 мин", "20-25 °C, 5 мин"],
    ]
    table(p, 60, 680, [230, 250, 250, 250], 36, cyc, font=10)
    p.text("Условные обозначения: I - линия масла; II - линия пахты и напитков; III - резервуары сырого молока и сливок.", 60, 950, 760, 30, size=12, align="left")
    p.title_block("Схема мойки<br>оборудования", "4", "ТХ")
    return p


def create_economics(c):
    p = Page("5 Экономический лист")
    p.text("СВОДНАЯ ТАБЛИЦА ТЕХНИКО-ЭКОНОМИЧЕСКИХ ПОКАЗАТЕЛЕЙ", 30, 20, 1000, 35, size=21, bold=True)
    revenue = (
        c["peasant"] * 250 * 480 / 1_000_000
        + c["dessert"] * 250 * 540 / 1_000_000
        + c["pasteurized_bm"] * 250 * 62 / 1_000_000
        + c["fermented"] * 250 * 78 / 1_000_000
        + c["vanilla"] * 250 * 82 / 1_000_000
        + c["skim"] * 250 * 16 / 1_000_000
    )
    costs = 330 + 24 + 36 + 24 + 52 + 30 + 45
    profit = revenue - costs
    net = profit * 0.8
    payback = 495 / (net + 36)
    indicators = [
        ["Показатель", "Значение"],
        ["Переработка молока", f"{fmt(c['annual_milk_t'])} т/год"],
        ["Выпуск масла", f"{fmt(c['annual_butter_t'])} т/год"],
        ["Выпуск продуктов из пахты", f"{fmt(c['annual_drinks_t'])} т/год"],
        ["Реализация обезжиренного молока", f"{fmt(c['annual_skim_t'])} т/год"],
        ["Стоимость молока", "330,00 млн руб./год"],
        ["Годовая выручка", f"{fmt(revenue, 2)} млн руб."],
        ["Годовая себестоимость", f"{fmt(costs, 2)} млн руб."],
        ["Прибыль до налогообложения", f"{fmt(profit, 2)} млн руб."],
        ["Чистая прибыль", f"{fmt(net, 2)} млн руб."],
        ["Капитальные вложения", "495,00 млн руб."],
        ["Срок окупаемости", f"{fmt(payback, 2)} года"],
    ]
    table(p, 60, 100, [360, 220], 38, indicators, font=12)
    products = [
        ("Масло крестьянское", c["peasant"] * 250 / 1000, "#d5e8d4"),
        ("Масло десертное с кофе", c["dessert"] * 250 / 1000, "#f8cecc"),
        ("Пахта пастеризованная", c["pasteurized_bm"] * 250 / 1000, "#dae8fc"),
        ("Кисломолочный напиток", c["fermented"] * 250 / 1000, "#dae8fc"),
        ("Напиток с ванилью", c["vanilla"] * 250 / 1000, "#dae8fc"),
    ]
    p.text("Годовой выпуск продукции, т", 720, 100, 440, 30, size=16, bold=True)
    max_v = max(v for _, v, _ in products)
    for i, (name, value, color) in enumerate(products):
        y = 155 + i * 70
        p.text(name, 690, y, 230, 25, size=12, align="right")
        p.rect("", 940, y, value / max_v * 360, 25, fill=color, stroke="#666666")
        p.text(fmt(value, 1), 1310, y, 80, 25, size=12, align="left")
    p.text("Структура себестоимости, млн руб.", 720, 555, 440, 30, size=16, bold=True)
    cost_items = [("молоко", 330, "#dae8fc"), ("материалы", 24, "#fff2cc"), ("упаковка", 36, "#f8cecc"), ("энергия", 24, "#d5e8d4"), ("труд", 52, "#e1d5e7"), ("прочие", 75, "#f5f5f5")]
    x = 720
    for name, value, color in cost_items:
        w = value / costs * 610
        p.rect(name + "<br>" + fmt(value, 0), x, 610, w, 70, fill=color, stroke="#666666", size=11)
        x += w
    p.text("Ключевой расчет: 15 000 т молока × 0,022 млн руб./т = 330 млн руб./год.", 720, 710, 650, 30, size=13, align="left")
    p.title_block("Сводная таблица технико-<br>экономических показателей", "5", "ТХ")
    return p


def write_drawio(path: Path, pages: list[Page]):
    mxfile = ET.Element(
        "mxfile",
        host="app.diagrams.net",
        modified="2026-05-31T20:28:00.000Z",
        agent="Cursor Cloud",
        version="24.0.0",
        type="device",
    )
    for page in pages:
        diagram = ET.SubElement(mxfile, "diagram", id=page.name.replace(" ", "_"), name=page.name)
        diagram.append(page.diagram_xml())
    ET.indent(mxfile, space="  ")
    path.write_text(ET.tostring(mxfile, encoding="unicode"), encoding="utf-8")


def write_mermaid(c):
    (OUT / "mermaid_equipment_scheme.mmd").write_text(
        """flowchart LR
    A[Молоко-сырье 60 000 кг/смену] --> B[Приемка и учет]
    B --> C[Резервуары сырого молока]
    C --> D[Подогрев 40-45 °C]
    D --> E[Сепаратор-сливкоотделитель]
    E --> F[Обезжиренное молоко]
    E --> G[Сливки 35 %]
    G --> H[Пастеризация сливок 85-90 °C]
    H --> I[Созревание сливок 4-8 °C]
    I --> J[Непрерывный маслоизготовитель]
    J --> K[Масло крестьянское]
    J --> L[Масло десертное с кофе]
    J --> M[Пахта]
    M --> N[Пастеризация пахты 76-80 °C]
    N --> O[Пахта пастеризованная]
    N --> P[Кисломолочный напиток с сахаром]
    N --> Q[Напиток из пахты с ванилью]
""",
        encoding="utf-8",
    )
    (OUT / "mermaid_cip_routes.mmd").write_text(
        """flowchart LR
    W[Вода] --> P[CIP насос]
    S[Щелочной раствор] --> P
    A[Кислотный раствор] --> P
    D[Дезинфектант] --> P
    P --> H[Подогреватель]
    H --> R1[Маршрут I: линия масла]
    H --> R2[Маршрут II: линия пахты]
    H --> R3[Маршрут III: резервуары]
    R1 --> RET[Возврат раствора]
    R2 --> RET
    R3 --> RET
    RET --> P
""",
        encoding="utf-8",
    )


def main():
    OUT.mkdir(exist_ok=True)
    c = calc()
    pages = [
        create_equipment(c),
        create_gantt(c),
        create_plan(c),
        create_cip(c),
        create_economics(c),
    ]
    write_drawio(OUT / "VKR_Khudoykulzoda_graphic_part.drawio", pages)
    for page in pages:
        safe = page.name.lower().replace(" ", "_")
        write_drawio(OUT / f"{safe}.drawio", [page])
    write_mermaid(c)
    (OUT / "README.md").write_text(
        """# Графическая часть ВКР

Файлы подготовлены под тему: «Проект завода по производству масла и продуктов из пахты».

## Что открыть в draw.io

1. `VKR_Khudoykulzoda_graphic_part.drawio` - общий файл на 5 страниц.
2. Отдельные файлы `1_схема_оборудования.drawio`, `2_график_процессов.drawio`, `3_план_завода.drawio`, `4_схема_мойки.drawio`, `5_экономический_лист.drawio`.

## Что перенести в КОМПАС

Эти draw.io-листы можно использовать как эскиз. Для сдачи графической части лучше перенести их в КОМПАС-3D на формат А1 с основной надписью ЕСКД.

## Mermaid

Файлы `mermaid_equipment_scheme.mmd` и `mermaid_cip_routes.mmd` содержат упрощенный код для проверки логики технологической схемы и маршрутов мойки.
""",
        encoding="utf-8",
    )
    print("Generated draw.io drawings in", OUT)


if __name__ == "__main__":
    main()
