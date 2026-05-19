"""Регистрация всех роутеров aiogram."""

from aiogram import Router

from . import admins, setup, users


def get_root_router() -> Router:
    """Собирает корневой роутер с подключёнными подмодулями."""
    root = Router(name="root")
    root.include_router(setup.router)
    root.include_router(admins.router)
    root.include_router(users.router)
    return root


__all__ = ["get_root_router"]
