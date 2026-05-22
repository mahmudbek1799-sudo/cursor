"""Построение аналитических дашбордов на Matplotlib."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Sequence

import matplotlib

matplotlib.use("Agg")  # Безопасный backend без GUI.
import matplotlib.pyplot as plt  # noqa: E402


def build_orders_chart(points: Sequence[tuple[str, int]]) -> bytes:
    """Сформировать PNG-график "Заказы за последние N дней"."""

    if not points:
        points = [(datetime.now().strftime("%Y-%m-%d"), 0)]
    dates = [p[0] for p in points]
    counts = [p[1] for p in points]

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=130)
    bars = ax.bar(dates, counts, color="#3b82f6", edgecolor="#1e3a8a")
    ax.set_title("Динамика заказов мебельного магазина", fontsize=14, weight="bold")
    ax.set_xlabel("Дата", fontsize=11)
    ax.set_ylabel("Количество заказов", fontsize=11)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)
    plt.xticks(rotation=30, ha="right")
    for rect, value in zip(bars, counts):
        ax.text(
            rect.get_x() + rect.get_width() / 2,
            rect.get_height() + 0.05,
            str(value),
            ha="center",
            va="bottom",
            fontsize=10,
            color="#1f2937",
        )
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
