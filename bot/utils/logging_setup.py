"""Унифицированная настройка логирования.

Все события (запуск, действия администратора, ошибки, синхронизация)
направляются как в консоль, так и в файл ``logs/bot.log``. Это позволяет
расследовать инциденты безопасности и формировать аудит-трейл.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from bot.config import ROOT_DIR


def setup_logging(level: str = "INFO") -> None:
    log_dir = ROOT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "bot.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(file_handler)

    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
