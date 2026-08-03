from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models.plan import Plan


class PlanRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, plan_id: int) -> Plan | None:
        """Get a plan by its ID."""
        result = await self._session.execute(select(Plan).where(Plan.id == plan_id))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Plan]:
        """Get all plans, ordered by price."""
        result = await self._session.execute(
            select(Plan).order_by(Plan.price_usd)
        )
        return list(result.scalars().all())

    async def add(self, price_usd: int, duration_days: int) -> Plan:
        """Add a new plan to the database."""
        plan = Plan(price_usd=price_usd, duration_days=duration_days)
        self._session.add(plan)
        await self._session.flush()
        return plan

    async def delete(self, plan: Plan) -> None:
        """Delete a plan from the database."""
        await self._session.delete(plan)
        await self._session.flush()
