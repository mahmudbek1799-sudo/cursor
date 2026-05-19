"""Единая точка настройки логирования.

Используем стандартный ``logging`` с двумя обработчиками: вывод в консоль
(уровень INFO) и ротация файла ``errors.log`` (уровень WARNING). Конкретный
путь к файлу берётся из ``config.settings.log_file``.
"""

from __future__ import annotations

import logging
import sys
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
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream = logging.StreamHandler(sys.stdout)
    stream.setLevel(logging.INFO)
    stream.setFormatter(fmt)

    file_h = RotatingFileHandler(
        log_file, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_h.setLevel(logging.WARNING)
    file_h.setFormatter(fmt)

    root.handlers.clear()
    root.addHandler(stream)
    root.addHandler(file_h)

    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    _INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
