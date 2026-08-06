from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.infra.db.repositories.invite_link import InviteLinkRepository
from src.infra.db.repositories.payment import PaymentRepository
from src.infra.db.repositories.plan import PlanRepository
from src.infra.db.repositories.subscription import SubscriptionRepository
from src.infra.db.repositories.user import UserRepository


class UnitOfWork:
    """
    Async Unit of Work.

    Usage:
        async with UnitOfWork(session_factory) as uow:
            user = await uow.users.get(user_id)
            ...
            # commit automatically on exit if no exception occurred
    """

    users: UserRepository
    payments: PaymentRepository
    subscriptions: SubscriptionRepository
    plans: PlanRepository
    invite_links: InviteLinkRepository

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.users = UserRepository(self._session)
        self.plans = PlanRepository(self._session)
        self.payments = PaymentRepository(self._session)
        self.subscriptions = SubscriptionRepository(self._session)
        self.invite_links = InviteLinkRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        session = self._session
        assert session is not None, "UnitOfWork used outside 'async with' block"
        try:
            if exc_type is None:
                await self.commit()
            else:
                await self.rollback()
        finally:
            await session.close()
            self._session = None

    async def commit(self) -> None:
        """Явний коміт. Можна викликати вручну всередині блоку, якщо потрібно."""
        session = self._session
        assert session is not None, "UnitOfWork used outside 'async with' block"
        try:
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    async def rollback(self) -> None:
        session = self._session
        assert session is not None, "UnitOfWork used outside 'async with' block"
        await session.rollback()
