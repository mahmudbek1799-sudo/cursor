ПРИЛОЖЕНИЕ 1
(обязательное)
Фрагменты программного кода

В приложении приведены только основные фрагменты программного кода, которые отражают ключевые элементы реализации проекта: настройки приложения, работу с базой данных, получение данных с веб-страницы и формирование аналитического графика. Полные служебные обработчики интерфейса Telegram-бота в приложение не включены, так как они перегружают пояснительную записку и не относятся к минимальному набору, указанному в техническом задании.

1. Файл config.py

В файле config.py хранится класс Settings, который отвечает за чтение параметров окружения. Отдельно указывается параметр proxy_url, используемый при необходимости подключения через прокси-сервер.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    proxy_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
```

2. Файл database.py

В файле database.py приведены только функции init_schema, upsert_order и apply_discount. Они демонстрируют создание структуры базы данных, добавление или обновление заказа и применение скидки к заказу.

```python
import sqlite3
from pathlib import Path


DB_PATH = Path("data/app.db")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_schema() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                total REAL NOT NULL,
                discount REAL NOT NULL DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def upsert_order(order_id: int, user_id: int, title: str, total: float) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO orders (order_id, user_id, title, total)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(order_id) DO UPDATE SET
                user_id = excluded.user_id,
                title = excluded.title,
                total = excluded.total,
                updated_at = CURRENT_TIMESTAMP
            """,
            (order_id, user_id, title, total),
        )
        conn.commit()


def apply_discount(order_id: int, percent: float) -> float:
    if not 0 <= percent <= 100:
        raise ValueError("Размер скидки должен быть от 0 до 100 процентов")

    with get_connection() as conn:
        row = conn.execute(
            "SELECT total FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Заказ не найден")

        total = float(row[0])
        discount = round(total * percent / 100, 2)
        conn.execute(
            "UPDATE orders SET discount = ?, updated_at = CURRENT_TIMESTAMP WHERE order_id = ?",
            (discount, order_id),
        )
        conn.commit()
        return round(total - discount, 2)
```

3. Файл parser.py

В файле parser.py оставлен только фрагмент, показывающий разбор HTML-страницы с использованием BeautifulSoup. Такой фрагмент отражает принцип извлечения данных из разметки без включения лишней служебной логики.

```python
from bs4 import BeautifulSoup


def parse_orders_page(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    result: list[dict[str, str]] = []

    for row in soup.select("table.orders tbody tr"):
        cells = [cell.get_text(strip=True) for cell in row.select("td")]
        if len(cells) < 4:
            continue

        result.append(
            {
                "order_id": cells[0],
                "client": cells[1],
                "title": cells[2],
                "total": cells[3].replace(" ", "").replace(",", "."),
            }
        )

    return result
```

4. Файл analytics.py

В файле analytics.py приведен только фрагмент генерации графика средствами matplotlib. Он показывает, как на основе агрегированных данных формируется изображение для дальнейшей отправки пользователю или сохранения в отчете.

```python
from pathlib import Path

import matplotlib.pyplot as plt


def build_orders_chart(data: dict[str, float], output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    labels = list(data.keys())
    values = list(data.values())

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(labels, values, color="#4C78A8")
    ax.set_title("Сумма заказов по категориям")
    ax.set_xlabel("Категория")
    ax.set_ylabel("Сумма, руб.")
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)

    return output
```
