from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

if TYPE_CHECKING:
    from src.infra.db.models.payment import Payment
    from src.infra.db.models.subscription import Subscription

from src.core.enums import PaymentMethod, PaymentStatus
from src.core.exceptions import PaymentNotFound, PlanNotFound, UserNotFound
from src.infra.db.uow import UnitOfWork
from src.services.subscription import SubscriptionService


class PaymentService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        subscription_service: SubscriptionService,
    ):
        self._session_factory = session_factory
        self._sub_service = subscription_service

    async def create(
        self,
        user_id: int,
        plan_id: int,
        method: PaymentMethod,
    ) -> Payment:
        """Create a pending payment for a user and plan.

        With a payment gateway integrated, this is also where you would call
        ``provider.create_invoice(...)`` and store its reference.
        """
        async with UnitOfWork(self._session_factory) as uow:
            user = await uow.users.get_by_id(user_id)
            if not user:
                raise UserNotFound(f"User with id {user_id} not found")
            plan = await uow.plans.get_by_id(plan_id)
            if not plan:
                raise PlanNotFound(f"Plan with id {plan_id} not found")

            return await uow.payments.add(
                user_id=user.id,
                plan_id=plan.id,
                amount_usd=plan.price_usd,
                method=method,
            )

    async def confirm(self, provider_ref: str) -> Subscription | None:
        """Confirm a paid payment and activate the subscription.

        Idempotent: if the payment is already ``PAID``, does nothing and
        returns ``None``, so a duplicate webhook never extends the
        subscription twice.
        """
        async with UnitOfWork(self._session_factory) as uow:
            payment = await uow.payments.get_by_provider_ref(provider_ref)
            if not payment:
                raise PaymentNotFound(f"Payment with ref {provider_ref} not found")
            if payment.status == PaymentStatus.PAID:
                return None

            payment.status = PaymentStatus.PAID
            payment.paid_at = datetime.now(UTC)

            plan = await uow.plans.get_by_id(payment.plan_id)
            if not plan:
                raise PlanNotFound(f"Plan with id {payment.plan_id} not found")

            sub = await self._sub_service.activate(
                payment.user_id,
                plan,
                uow=uow,
            )
            payment.subscription_id = sub.id
            return sub

    async def get_by_user(self, user_id: int) -> list[Payment]:
        """Get all payments of a user, newest first."""
        async with UnitOfWork(self._session_factory) as uow:
            return await uow.payments.get_by_user(user_id)
