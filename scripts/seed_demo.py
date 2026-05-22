"""Наполнение БД демонстрационными данными для защиты ВКР.

Запуск:

    python scripts/seed_demo.py
"""

from __future__ import annotations

import asyncio
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bot.database.db import ORDER_STATUSES, Database, get_db  # noqa: E402


CATALOG = [
    ("Диван «Стокгольм»", 65990),
    ("Кровать «Норд» 160×200", 42990),
    ("Стол обеденный «Орегон»", 24990),
    ("Шкаф-купе «Капри» 2.0м", 38990),
    ("Кресло «Лофт»", 17990),
    ("Комод «Прованс»", 21990),
    ("Стул «Венский» (2 шт.)", 9990),
    ("Тумба ТВ «Бергамо»", 15990),
]
NAMES = ["Иванов И. И.", "Петрова А. С.", "Сидоров К. В.",
         "Козлов М. Д.", "Орлова Е. П.", "Лебедев Д. Н.",
         "Соколова М. И.", "Морозов А. А."]
STREETS = ["ул. Ленина, 15, кв. 12", "пр. Победы, 87, кв. 4",
           "ул. Мира, 3, кв. 56", "ул. Гагарина, 21, кв. 99",
           "ул. Советская, 44, кв. 7"]


async def main() -> None:
    db: Database = get_db()
    await db.init_schema()
    random.seed(42)

    categories = ["диван", "кровать", "стол", "шкаф", "кресло",
                  "комод", "стул", "тумба"]
    for idx, (title, price) in enumerate(CATALOG, start=1):
        cat = "другое"
        for c in categories:
            if c in title.lower():
                cat = c
                break
        sku = f"DEMO-{1000 + idx}"
        await db.upsert_product({
            "sku": sku,
            "title": title,
            "category": cat,
            "price": float(price),
            "stock": random.randint(3, 18),
            "description": f"{title} — современная модель из коллекции 2026 года.",
            "is_active": 1,
        })

    await db.add_discount(kind="percent", value=10, product_id=None,
                          valid_to=(datetime.now() + timedelta(days=7))
                          .isoformat(sep=" ", timespec="seconds"))
    diván = await db.get_product_by_sku("DEMO-1001")
    if diván is not None:
        await db.add_discount(kind="fixed", value=5000, product_id=diván.id)

    now = datetime.now()
    for i in range(60):
        created = now - timedelta(days=random.randint(0, 13),
                                  hours=random.randint(0, 23))
        items_sample = random.sample(CATALOG, k=random.randint(1, 3))
        items_lines, total = [], 0.0
        for title, price in items_sample:
            qty = random.randint(1, 2)
            items_lines.append(f"• {title} × {qty}")
            total += price * qty
        status = random.choices(
            ORDER_STATUSES,
            weights=[0.25, 0.2, 0.15, 0.3, 0.1],
        )[0]
        await db.upsert_order(
            {
                "external_id": f"SEED-{1000 + i}",
                "customer_name": random.choice(NAMES),
                "customer_phone": f"+7 (9{random.randint(10,99)}) "
                                  f"{random.randint(100,999)}-"
                                  f"{random.randint(10,99)}-"
                                  f"{random.randint(10,99)}",
                "customer_telegram_id": None,
                "address": random.choice(STREETS),
                "items": "\n".join(items_lines),
                "total": total,
                "status": status,
                "comment": "",
            }
        )
        # Подкорректируем дату создания, чтобы график был наглядным.
        async with db.connect() as conn:
            await conn.execute(
                "UPDATE orders SET created_at = ?, updated_at = ? "
                "WHERE external_id = ?",
                (created.isoformat(sep=" ", timespec="seconds"),
                 created.isoformat(sep=" ", timespec="seconds"),
                 f"SEED-{1000 + i}"),
            )
            await conn.commit()
    print("✅ Засеяно 60 демонстрационных заказов в", db.path)


if __name__ == "__main__":
    asyncio.run(main())
