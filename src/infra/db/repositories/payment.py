from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import PaymentMethod
from src.infra.db.models.payment import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, payment_id: int) -> Payment | None:
        """Get a payment by its ID."""
        result = await self._session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_provider_ref(self, provider_ref: str) -> Payment | None:
        """Get a payment by the external provider reference."""
        result = await self._session.execute(
            select(Payment).where(Payment.provider_ref == provider_ref)
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: int) -> list[Payment]:
        """Get all payments for a user, newest first."""
        result = await self._session.execute(
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.id.desc())
        )
        return list(result.scalars().all())

    async def add(
        self,
        user_id: int,
        plan_id: int,
        amount_usd: int,
        method: PaymentMethod,
        provider_ref: str | None = None,
    ) -> Payment:
        """Add a new payment."""
        payment = Payment(
            user_id=user_id,
            plan_id=plan_id,
            amount_usd=amount_usd,
            method=method,
            provider_ref=provider_ref,
        )
        self._session.add(payment)
        await self._session.flush()
        return payment
