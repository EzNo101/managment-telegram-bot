from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, user_id: int) -> User | None:
        """Get a user by their ID."""
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_tg_id(self, tg_id: int) -> User | None:
        """Get a user by their Telegram ID."""
        result = await self._session.execute(
            select(User).where(
                User.telegram_id == tg_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Get a user by their username."""
        result = await self._session.execute(
            select(User).where(
                User.username == username,
            )
        )
        return result.scalar_one_or_none()

    async def add(self, tg_id: int, username: str | None) -> User:
        """Add a new user to the database."""
        user = User(telegram_id=tg_id, username=username)
        self._session.add(user)
        await self._session.flush()
        return user

    async def delete(self, user: User) -> None:
        """Delete a user from the database."""
        await self._session.delete(user)
        await self._session.flush()
