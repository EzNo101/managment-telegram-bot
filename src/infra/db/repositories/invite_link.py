from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models.invite_link import InviteLink


class InviteLinkRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, link_id: int) -> InviteLink | None:
        """Get an invite link by its ID."""
        result = await self._session.execute(
            select(InviteLink).where(InviteLink.id == link_id)
        )
        return result.scalar_one_or_none()

    async def get_active_by_user(self, user_id: int) -> list[InviteLink]:
        """Get all non-revoked invite links of a user, newest first."""
        result = await self._session.execute(
            select(InviteLink)
            .where(
                InviteLink.user_id == user_id,
                InviteLink.is_revoked.is_(False),
            )
            .order_by(InviteLink.id.desc())
        )
        return list(result.scalars().all())

    async def add(
        self,
        user_id: int,
        url: str,
        subscription_id: int | None = None,
        expires_at: datetime | None = None,
    ) -> InviteLink:
        """Store a new invite link in the database."""
        link = InviteLink(
            user_id=user_id,
            subscription_id=subscription_id,
            url=url,
            expires_at=expires_at,
        )
        self._session.add(link)
        await self._session.flush()
        return link

    async def mark_revoked(self, link: InviteLink) -> None:
        """Mark an invite link as revoked."""
        link.is_revoked = True
