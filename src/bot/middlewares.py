from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.services.user import UserService


class BanMiddleware(BaseMiddleware):
    """Silently drop updates from banned users (admins are exempt)."""

    def __init__(self, user_service: UserService):
        self._user_service = user_service

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is not None:
            is_banned = await self._user_service.is_banned(user.id)
            is_admin = await self._user_service.is_admin(user.id)
            if is_banned and not is_admin:
                return None
        return await handler(event, data)
