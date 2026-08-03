from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.exceptions import PlanNotFound
from src.infra.db.models.plan import Plan
from src.infra.db.uow import UnitOfWork


class PlanService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def get_by_id(self, plan_id: int) -> Plan:
        """Get a plan by its ID in database."""
        async with UnitOfWork(self._session_factory) as uow:
            plan = await uow.plans.get_by_id(plan_id)
            if not plan:
                raise PlanNotFound(f"Plan with id {plan_id} not found")
            return plan

    async def get_all(self) -> list[Plan]:
        """Get all plans."""
        async with UnitOfWork(self._session_factory) as uow:
            return await uow.plans.get_all()

    async def add(self, price_usd: int, duration_days: int) -> Plan:
        """Add a new plan to the database."""
        async with UnitOfWork(self._session_factory) as uow:
            return await uow.plans.add(price_usd, duration_days)

    async def delete(self, plan_id: int) -> None:
        """Delete a plan from the database."""
        async with UnitOfWork(self._session_factory) as uow:
            plan = await uow.plans.get_by_id(plan_id)
            if not plan:
                raise PlanNotFound(f"Plan with id {plan_id} not found")
            await uow.plans.delete(plan)
