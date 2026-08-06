from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.config import settings
from src.core.exceptions import UserNotFound
from src.infra.db.uow import UnitOfWork

if TYPE_CHECKING:
    from src.infra.db.models.user import User


class UserService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def get_by_id(self, user_id: int) -> User:
        """Get a user by their ID in database."""
        async with UnitOfWork(self._session_factory) as uow:
            user = await uow.users.get_by_id(user_id)
            if not user:
                raise UserNotFound(f"User with id {user_id} not found")
            return user

    async def get_by_tg_id(self, tg_id: int) -> User:
        """Get a user by their Telegram ID."""
        async with UnitOfWork(self._session_factory) as uow:
            user = await uow.users.get_by_tg_id(tg_id)
            if not user:
                raise UserNotFound(f"User with Telegram ID {tg_id} not found")
            return user

    async def get_by_username(self, username: str) -> User:
        """Get a user by their username."""
        async with UnitOfWork(self._session_factory) as uow:
            user = await uow.users.get_by_username(username)
            if not user:
                raise UserNotFound(f"User with username {username} not found")
            return user

    async def get_all(self) -> list[User]:
        """Get all users."""
        async with UnitOfWork(self._session_factory) as uow:
            return await uow.users.get_all()

    async def get_banned(self) -> list[User]:
        """Get all banned users."""
        async with UnitOfWork(self._session_factory) as uow:
            return await uow.users.get_banned()

    async def get_or_create(self, tg_id: int, username: str | None) -> User:
        """Get a user by Telegram ID, creating them if they don't exist yet.

        Also syncs the username in case the user changed or removed it.
        """
        async with UnitOfWork(self._session_factory) as uow:
            user = await uow.users.get_by_tg_id(tg_id)
            if user is None:
                return await uow.users.add(tg_id, username)
            if user.username != username:
                user.username = username
            return user

    async def ban(self, tg_id: int) -> None:
        """Ban a user."""
        async with UnitOfWork(self._session_factory) as uow:
            user = await uow.users.get_by_tg_id(tg_id)
            if not user:
                raise UserNotFound(f"User with Telegram ID {tg_id} not found")
            user.is_banned = True

    async def ban_or_create(
        self, tg_id: int, username: str | None = None
    ) -> User:
        """Ban a user in DB, creating the record if it doesn't exist yet."""
        async with UnitOfWork(self._session_factory) as uow:
            user = await uow.users.get_by_tg_id(tg_id)
            if user is None:
                user = await uow.users.add(tg_id, username)
            user.is_banned = True
            return user

    async def unban(self, tg_id: int) -> None:
        """Unban a user."""
        async with UnitOfWork(self._session_factory) as uow:
            user = await uow.users.get_by_tg_id(tg_id)
            if not user:
                raise UserNotFound(f"User with Telegram ID {tg_id} not found")
            user.is_banned = False

    async def set_admin(self, tg_id: int, is_admin: bool) -> None:
        """Grant or revoke admin rights."""
        async with UnitOfWork(self._session_factory) as uow:
            user = await uow.users.get_by_tg_id(tg_id)
            if not user:
                raise UserNotFound(f"User with Telegram ID {tg_id} not found")
            user.is_admin = is_admin

    async def is_admin(self, tg_id: int) -> bool:
        """Check if a user is an admin (from config or the database flag)."""
        if tg_id in settings.ADMIN_IDS:
            return True
        async with UnitOfWork(self._session_factory) as uow:
            user = await uow.users.get_by_tg_id(tg_id)
            return bool(user and user.is_admin)

    async def is_banned(self, tg_id: int) -> bool:
        """Check if a user is banned."""
        async with UnitOfWork(self._session_factory) as uow:
            user = await uow.users.get_by_tg_id(tg_id)
            return bool(user and user.is_banned)
