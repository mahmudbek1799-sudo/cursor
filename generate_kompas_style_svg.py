from __future__ import annotations

from pathlib import Path


OUT = Path("drawings/kompas_style_svg")
W, H = 841, 594


def fmt(value: float, digits: int = 1) -> str:
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")


def calc():
    milk = 60000.0
    milk_fat = 3.8
    cream_fat = 35.0
    skim_fat = 0.05
    milk_after_sep = milk * 0.999
    cream = milk_after_sep * (milk_fat - skim_fat) / (cream_fat - skim_fat)
    skim = milk_after_sep - cream
    cream_after_p = cream * 0.998
    fat = cream_after_p * 0.35 * 0.995
    peasant = fat * 0.75 / 0.725 * 0.997
    dessert = fat * 0.25 / 0.52 * 0.997
    buttermilk = (cream_after_p - fat * 0.75 / 0.725 - fat * 0.25 / 0.52) * 0.995
    pah = buttermilk * 0.5 * 0.998 * 0.998
    ferm_base = buttermilk * 0.3 * 0.998
    ferm = (ferm_base + ferm_base * 0.055 + ferm_base * 0.03) * 0.998
    van_base = buttermilk * 0.2 * 0.998
    vanilla = (van_base + van_base * 0.045 + van_base * 0.0008) * 0.998
    return {
        "milk": milk,
        "cream": cream,
        "skim": skim,
        "peasant": peasant,
        "dessert": dessert,
        "buttermilk": buttermilk,
        "pah": pah,
        "ferm": ferm,
        "vanilla": vanilla,
    }


class SVG:
    def __init__(self, title: str, sheet: int, code: str):
        self.title = title
        self.sheet = sheet
        self.code = code
        self.items: list[str] = []
        self.defs()
        self.border()
        self.title_block()

    def defs(self):
        self.items.append(
            '<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">'
            '<path d="M0,0 L7,3 L0,6 Z" fill="black"/></marker></defs>'
        )

    def text(self, x, y, text, size=4, anchor="middle", bold=False, rotate=None):
        weight = "bold" if bold else "normal"
        transform = f' transform="rotate({rotate} {x} {y})"' if rotate else ""
        lines = str(text).split("<br>")
        for i, line in enumerate(lines):
            self.items.append(
                f'<text x="{x}" y="{y + i * size * 1.25}" font-family="Times New Roman" '
                f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}"{transform}>{esc(line)}</text>'
            )

    def rect(self, x, y, w, h, fill="white", sw=0.35):
        self.items.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="black" stroke-width="{sw}"/>')

    def line(self, x1, y1, x2, y2, sw=0.35, dash=False, arrow=False):
        d = ' stroke-dasharray="3 2"' if dash else ""
        m = ' marker-end="url(#arr)"' if arrow else ""
        self.items.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="black" stroke-width="{sw}"{d}{m}/>')

    def poly(self, points, fill="none", sw=0.35, arrow=False, dash=False):
        pts = " ".join(f"{x},{y}" for x, y in points)
        m = ' marker-end="url(#arr)"' if arrow else ""
        d = ' stroke-dasharray="3 2"' if dash else ""
        self.items.append(f'<polyline points="{pts}" fill="{fill}" stroke="black" stroke-width="{sw}"{m}{d}/>')

    def border(self):
        self.rect(10, 10, W - 20, H - 20, fill="none", sw=0.7)
        self.rect(20, 20, W - 40, H - 40, fill="none", sw=0.35)

    def title_block(self):
        x, y, w, h = 555, 500, 255, 64
        self.rect(x, y, w, h, fill="white", sw=0.45)
        for yy in [512, 524, 544]:
            self.line(x, yy, x + w, yy)
        for xx in [590, 645, 725, 760, 785]:
            self.line(xx, y, xx, y + h)
        self.text(x + 5, y + 8, "Изм. Лист № докум. Подп. Дата", size=3, anchor="start")
        self.text(595, y + 8, f"ВКР.19.03.03.02.3625.{self.code}", size=3.2, anchor="start", bold=True)
        self.text(742, y + 8, "Лист", size=3)
        self.text(772, y + 8, str(self.sheet), size=3.8, bold=True)
        self.text(798, y + 8, "5", size=3.8, bold=True)
        self.text(x + 5, y + 520 - 500, "Разраб. Худойкулзода Ш.М.", size=3, anchor="start")
        self.text(x + 5, y + 534 - 500, "Пров. Куренкова Л.А.", size=3, anchor="start")
        self.text(x + 5, y + 556 - 500, "Н.контр. __________", size=3, anchor="start")
        self.text(686, 532, self.title, size=4, bold=True)
        self.text(768, 535, "ФГБОУ ВО Вологодская ГМХА<br>Кафедра технологии молока<br>и молочных продуктов", size=3)

    def table(self, x, y, widths, rh, rows, size=3.2):
        yy = y
        for r, row in enumerate(rows):
            xx = x
            for c, val in enumerate(row):
                self.rect(xx, yy, widths[c], rh, fill="#f3f3f3" if r == 0 else "white")
                self.text(xx + widths[c] / 2, yy + rh / 2 + size / 3, val, size=size)
                xx += widths[c]
            yy += rh

    def save(self, path: Path):
        path.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">'
            + "".join(self.items)
            + "</svg>",
            encoding="utf-8",
        )


def esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def equipment(c):
    s = SVG("Схема технологического<br>оборудования", 1, "ТХ")
    s.text(30, 28, "СХЕМА ТЕХНОЛОГИЧЕСКОГО ОБОРУДОВАНИЯ", size=6, anchor="start", bold=True)
    nodes = [
        ("1", "Приемка<br>молока", 35, 70), ("2", "Резервуар<br>сырого молока", 125, 70),
        ("3", "Подогрев", 215, 70), ("4", "Сепаратор", 305, 70), ("5", "Обезж.<br>молоко", 395, 40),
        ("6", "Пастеризатор<br>сливок", 395, 105), ("7", "Созревание<br>сливок", 495, 105),
        ("8", "Масло-<br>изготовитель", 595, 105), ("9", "Фасование<br>масла", 695, 75),
        ("10", "Камера<br>масла", 695, 145), ("11", "Рецептурный<br>узел", 495, 190),
        ("12", "Емкость<br>пахты", 595, 190), ("13", "Пастеризатор<br>пахты", 495, 270),
        ("14", "Резервуары<br>сквашивания", 595, 270), ("15", "Фасование<br>напитков", 695, 270),
        ("16", "Камера<br>напитков", 695, 345), ("17", "CIP-<br>станция", 395, 345),
    ]
    pos = {}
    for num, name, x, y in nodes:
        s.rect(x, y, 58, 30)
        s.text(x + 29, y + 10, f"{num}<br>{name}", size=3)
        pos[num] = (x, y)
    for a, b in [("1","2"),("2","3"),("3","4"),("4","5"),("4","6"),("6","7"),("7","8"),("8","9"),("9","10"),("11","9"),("8","12"),("12","13"),("13","14"),("13","15"),("14","15"),("15","16")]:
        x1, y1 = pos[a]; x2, y2 = pos[b]
        s.poly([(x1+58, y1+15), (x2, y2+15)], arrow=True)
    for a, b in [("17","2"),("17","8"),("17","13")]:
        x1, y1 = pos[a]; x2, y2 = pos[b]
        s.poly([(x1+29, y1), (x1+29, y2+15), (x2, y2+15)], dash=True, arrow=True)
    s.table(35, 410, [18, 95, 22, 50], 10, [
        ["Поз.", "Наименование оборудования", "Кол.", "Тех. показатель"],
        ["1", "Линия приемки и учета молока", "1", "10-15 т/ч"],
        ["2", "Резервуар сырого молока", "2", "30 м3"],
        ["4", "Сепаратор-сливкоотделитель", "1", "10 000 л/ч"],
        ["6", "Пастеризатор сливок", "1", "3000 кг/ч"],
        ["8", "Непрерывный маслоизготовитель", "1", "1500 кг/ч"],
        ["13", "Пастеризатор пахты", "1", "2000 кг/ч"],
        ["17", "CIP-станция", "1", "3 контура"],
    ])
    s.text(240, 412, f"Молоко: {fmt(c['milk'],0)} кг/смену; сливки: {fmt(c['cream'])} кг; масло: {fmt(c['peasant']+c['dessert'])} кг; пахта: {fmt(c['buttermilk'])} кг", size=3.3, anchor="start")
    return s


def gantt(c):
    s = SVG("График производственных<br>процессов", 2, "ТХ")
    s.text(30, 28, "ГРАФИК ПРОИЗВОДСТВЕННЫХ ПРОЦЕССОВ", size=6, anchor="start", bold=True)
    x0, y0 = 25, 55
    hours = ["8-9","9-10","10-11","11-12","12-13","13-14","14-15","15-16","16-17"]
    s.table(x0, y0, [95, 32, 44] + [45]*len(hours), 11, [["Операция", "Масса", "Оборудование"] + hours], size=3)
    rows = [
        ("Приемка молока", "60000", "Линия приемки", 0, 3),
        ("Резервирование молока", "60000", "РМ 30 м3", 0, 6),
        ("Сепарирование молока", "59940", "Сепаратор", 1, 4),
        ("Пастеризация сливок", fmt(c["cream"]), "ППОУ сливок", 2, 2),
        ("Созревание сливок", fmt(c["cream"]), "Резервуары", 2, 5),
        ("Маслоизготовление", fmt(c["peasant"]+c["dessert"]), "Маслоизг.", 5, 2),
        ("Фасование масла", fmt(c["peasant"]+c["dessert"]), "Автомат", 6, 2),
        ("Пастеризация пахты", fmt(c["buttermilk"]), "ППОУ пахты", 6, 1),
        ("Сквашивание напитка", fmt(c["ferm"]), "Резервуар", 6, 3),
        ("Фасование напитков", fmt(c["pah"]+c["ferm"]+c["vanilla"]), "Автомат", 8, 1),
        ("CIP-мойка", "-", "CIP", 8, 1),
    ]
    for i, row in enumerate(rows):
        y = y0 + 11*(i+1)
        s.table(x0, y, [95, 32, 44] + [45]*len(hours), 11, [[row[0], row[1], row[2]] + [""]*len(hours)], size=2.7)
        bx = x0 + 95 + 32 + 44 + row[3]*45 + 2
        s.rect(bx, y+2, row[4]*45-4, 7, fill="#dddddd")
        s.text(bx + (row[4]*45-4)/2, y+7, "работа", size=2.5)
    s.table(35, 250, [18, 135], 9, [["№", "Рабочий"], ["1", "приемщик молочного сырья"], ["2", "аппаратчик сепарирования"], ["3", "аппаратчик пастеризации"], ["4", "оператор маслоизготовителя"], ["5", "оператор фасования"], ["6", "оператор CIP-мойки"]])
    return s


def plan(c):
    s = SVG("План завода", 3, "П")
    s.text(30, 28, "ПЛАН ЗАВОДА С РАССТАНОВКОЙ ОБОРУДОВАНИЯ", size=6, anchor="start", bold=True)
    x, y, k = 40, 55, 7
    rooms = [
        ("1 Приемка",0,0,18,12),("2 Лаборатория",18,0,12,12),("7 Фасовка масла",36,0,18,12),("8 Фасовка напитков",54,0,18,12),
        ("3 Резервуарное",0,12,18,18),("4 Аппаратное",18,12,18,18),("5 Маслоцех",36,12,18,18),("6 Участок пахты",54,12,18,18),
        ("11 CIP",18,30,9,12),("12 Бытовые",27,30,9,12),("9 Камера масла",36,30,18,12),("10 Камера напитков",54,30,18,12),
    ]
    s.rect(x,y,72*k,42*k,fill="none")
    for name, rx, ry, rw, rh in rooms:
        s.rect(x+rx*k, y+ry*k, rw*k, rh*k)
        s.text(x+rx*k+rw*k/2, y+ry*k+rh*k/2, name, size=3)
    for i in range(13):
        s.line(x+i*6*k, y, x+i*6*k, y+42*k, dash=True)
    for j in range(8):
        s.line(x, y+j*6*k, x+72*k, y+j*6*k, dash=True)
    s.poly([(20,100),(x+40,100),(x+180,170),(x+310,170),(x+440,110),(x+560,110)], arrow=True)
    s.text(20,95,"сырье",size=3,anchor="start")
    s.poly([(x+440,260),(x+560,330),(x+620,330)], arrow=True)
    s.text(x+615,325,"готовая<br>продукция",size=3,anchor="start")
    s.table(40, 380, [18, 120, 35], 9, [["№","Помещение","Площадь"],["1","Приемка молока","90"],["2","Лаборатория","80"],["4","Аппаратное отделение","160"],["5","Маслоцех","180"],["6","Участок пахты","120"],["9-10","Холодильные камеры","180"]])
    s.text(320, 385, "Масштаб условный 1:100. Сетка колонн 6 x 6 м.", size=3.3, anchor="start")
    return s


def cip(c):
    s = SVG("Схема мойки<br>оборудования", 4, "ТХ")
    s.text(30, 28, "СХЕМА САНИТАРНОЙ ОБРАБОТКИ ОБОРУДОВАНИЯ", size=6, anchor="start", bold=True)
    boxes = [("1 Вода",60,70),("2 Щелочь",60,120),("3 Кислота",60,170),("4 Дезинф.",60,220),("5 Насос",190,145),("6 Подогрев.",310,145),("I Линия масла",470,80),("II Линия пахты",470,155),("III Резервуары",470,230),("7 Возврат",650,155)]
    pos={}
    for t,x,y in boxes:
        s.rect(x,y,70,28); s.text(x+35,y+16,t,size=3); pos[t.split()[0]]=(x,y)
    for a in ["1","2","3","4"]:
        x1,y1=pos[a]; x2,y2=pos["5"]; s.poly([(x1+70,y1+14),(x2,y2+14)],arrow=True)
    for a,b in [("5","6"),("6","I"),("6","II"),("6","III"),("I","7"),("II","7"),("III","7"),("7","5")]:
        x1,y1=pos[a]; x2,y2=pos[b]; s.poly([(x1+70,y1+14),(x2,y2+14)],arrow=True,dash=(a=="7"))
    s.table(35, 330, [110,150,150,150], 10, [
        ["Операция","Маршрут I","Маршрут II","Маршрут III"],
        ["Ополаскивание","35-40 °C, 10 мин","35-40 °C, 10 мин","35-40 °C, 10 мин"],
        ["Щелочная мойка","1,0-1,5 %, 70 °C","1,0 %, 65 °C","1,0-1,5 %, 65 °C"],
        ["Кислотная мойка","0,5-1,0 %, 60 °C","по графику","0,5 %, 60 °C"],
        ["Дезинфекция","10 мин","10 мин","10 мин"],
        ["Ополаскивание","20-25 °C, 5 мин","20-25 °C, 5 мин","20-25 °C, 5 мин"],
    ])
    return s


def economy(c):
    s = SVG("Сводная таблица технико-<br>экономических показателей", 5, "ТХ")
    s.text(30,28,"СВОДНАЯ ТАБЛИЦА ТЕХНИКО-ЭКОНОМИЧЕСКИХ ПОКАЗАТЕЛЕЙ",size=6,anchor="start",bold=True)
    revenue = c["peasant"]*250*480/1e6 + c["dessert"]*250*540/1e6 + c["pah"]*250*62/1e6 + c["ferm"]*250*78/1e6 + c["vanilla"]*250*82/1e6 + c["skim"]*250*16/1e6
    costs = 541
    profit = revenue-costs
    rows = [["Показатели","Значения"],["Капитальные вложения, млн руб.","495,00"],["Годовая переработка молока, т","15000"],["Стоимость молока, млн руб.","330,00"],["Выпуск масла, т/год",fmt((c["peasant"]+c["dessert"])*250/1000)],["Выпуск продуктов из пахты, т/год",fmt((c["pah"]+c["ferm"]+c["vanilla"])*250/1000)],["Годовая выручка, млн руб.",fmt(revenue,2)],["Годовая себестоимость, млн руб.",fmt(costs,2)],["Прибыль до налогообложения, млн руб.",fmt(profit,2)],["Срок окупаемости, год",fmt(495/(profit*0.8+36),2)]]
    s.table(45,70,[150,90],12,rows,size=3.4)
    # simple bar chart
    items=[("Молоко",330),("Материалы",24),("Упаковка",36),("Энергия",24),("Труд",52),("Прочие",75)]
    s.text(360,75,"Структура себестоимости, млн руб.",size=4,bold=True)
    maxv=max(v for _,v in items)
    for i,(name,val) in enumerate(items):
        y=100+i*22
        s.text(350,y+6,name,size=3,anchor="end")
        s.rect(360,y,val/maxv*220,10,fill="#dddddd")
        s.text(590,y+8,fmt(val,0),size=3,anchor="start")
    s.text(360,260,"Расчет: 15 000 т x 0,022 млн руб./т = 330 млн руб.",size=4,anchor="start")
    return s


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    c = calc()
    pages = [
        ("01_equipment_scheme_kompas_style.svg", equipment(c)),
        ("02_process_graph_kompas_style.svg", gantt(c)),
        ("03_plant_plan_kompas_style.svg", plan(c)),
        ("04_cip_washing_kompas_style.svg", cip(c)),
        ("05_economic_sheet_kompas_style.svg", economy(c)),
    ]
    for name, svg in pages:
        svg.save(OUT / name)
    (OUT / "README.md").write_text(
        "Эти SVG-листы сделаны ближе к присланным примерам: формат А1, рамка, основная надпись, таблицы и плотная компоновка. "
        "Их можно открыть в браузере, Inkscape, LibreOffice Draw или импортировать как подложку при перерисовке в КОМПАС.\n",
        encoding="utf-8",
    )
    print("Generated KOMPAS-style SVG sheets in", OUT)


if __name__ == "__main__":
    main()
