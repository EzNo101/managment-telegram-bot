from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import SubscriptionStatus
from src.infra.db.models.subscription import Subscription


class SubscriptionRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, subscription_id: int) -> Subscription | None:
        """Get a subscription by its ID."""
        result = await self._session.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        return result.scalar_one_or_none()

    async def get_active_by_user(self, user_id: int) -> Subscription | None:
        """Get the currently active subscription for a user, if any."""
        result = await self._session.execute(
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.end_date > datetime.now(UTC),
            )
            .order_by(Subscription.end_date.desc())
        )
        return result.scalars().first()

    async def get_all_active(self) -> list[Subscription]:
        """Get all active subscriptions."""
        result = await self._session.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.end_date > datetime.now(UTC),
            )
        )
        return list(result.scalars().all())

    async def get_expired(self) -> list[Subscription]:
        """Get all active subscriptions that have already ended."""
        result = await self._session.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.end_date < datetime.now(UTC),
            )
        )
        return list(result.scalars().all())

    async def add(
        self,
        user_id: int,
        plan_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> Subscription:
        """Add a new subscription."""
        subscription = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            start_date=start_date,
            end_date=end_date,
        )
        self._session.add(subscription)
        await self._session.flush()
        return subscription
