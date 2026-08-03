from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

if TYPE_CHECKING:
    from src.infra.db.models.plan import Plan
    from src.infra.db.models.subscription import Subscription

from src.core.enums import SubscriptionStatus
from src.core.exceptions import SubscriptionNotFound
from src.infra.db.uow import UnitOfWork


class SubscriptionService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def get_by_id(self, subscription_id: int) -> Subscription:
        """Get a subscription by its ID in database."""
        async with UnitOfWork(self._session_factory) as uow:
            subscription = await uow.subscriptions.get_by_id(subscription_id)
            if not subscription:
                raise SubscriptionNotFound(
                    f"Subscription with id {subscription_id} not found"
                )
            return subscription

    async def get_active(self) -> list[Subscription]:
        """Get all active subscriptions."""
        async with UnitOfWork(self._session_factory) as uow:
            return await uow.subscriptions.get_all_active()

    async def get_expired(self) -> list[Subscription]:
        """Get all active subscriptions that have already ended."""
        async with UnitOfWork(self._session_factory) as uow:
            return await uow.subscriptions.get_expired()

    async def get_active_by_user(self, user_id: int) -> Subscription | None:
        """Get the currently active subscription for a user, if any."""
        async with UnitOfWork(self._session_factory) as uow:
            return await uow.subscriptions.get_active_by_user(user_id)

    async def activate(
        self,
        user_id: int,
        plan: Plan,
        uow: UnitOfWork | None = None,
    ) -> Subscription:
        """Activate a subscription, extending an active one or creating a new one.

        If the user already has an active subscription, its end date is extended
        by the plan duration. Otherwise a new subscription starts from now.

        When called from within another service transaction, pass the open ``uow``
        so all changes share a single transaction.
        """
        async def _run(u: UnitOfWork) -> Subscription:
            existing = await u.subscriptions.get_active_by_user(user_id)
            now = datetime.now(UTC)
            if existing:
                existing.end_date += timedelta(days=plan.duration_days)
                return existing
            return await u.subscriptions.add(
                user_id,
                plan.id,
                now,
                now + timedelta(days=plan.duration_days),
            )

        if uow is not None:
            return await _run(uow)
        async with UnitOfWork(self._session_factory) as u:
            return await _run(u)

    async def expire_all(self) -> None:
        """Mark all ended active subscriptions as expired."""
        async with UnitOfWork(self._session_factory) as uow:
            for sub in await uow.subscriptions.get_expired():
                sub.status = SubscriptionStatus.EXPIRED

    async def add(self, subscription: Subscription) -> None:
        """Add a new subscription to the database."""
        async with UnitOfWork(self._session_factory) as uow:
            await uow.subscriptions.add(
                user_id=subscription.user_id,
                plan_id=subscription.plan_id,
                start_date=subscription.start_date,
                end_date=subscription.end_date,
            )
