"""Пакет пользовательских фильтров aiogram."""

from .antispam import AntiSpamFilter
from .badwords import BadWordsFilter
from .links import LinksFilter

__all__ = ["AntiSpamFilter", "BadWordsFilter", "LinksFilter"]
