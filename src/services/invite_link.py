from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.config import settings
from src.infra.db.uow import UnitOfWork

if TYPE_CHECKING:
    from src.infra.db.models.invite_link import InviteLink


class InviteLinkService:
    def __init__(
        self,
        bot: Bot,
        session_factory: async_sessionmaker[AsyncSession],
    ):
        self._bot = bot
        self._session_factory = session_factory

    async def grant(self, user_id: int, tg_id: int, subscription_id: int) -> InviteLink:
        """Grant a user access to the VIP channel.

        Revokes any previous invite links the user still has and creates a
        fresh one-time link. Also clears a previous kick so the user can join.
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=settings.INVITE_EXPIRE_SECONDS)

        try:
            await self._bot.unban_chat_member(settings.CHANNEL_ID, tg_id)
        except TelegramAPIError:
            pass

        async with UnitOfWork(self._session_factory) as uow:
            for old in await uow.invite_links.get_active_by_user(user_id):
                try:
                    await self._bot.revoke_chat_invite_link(
                        settings.CHANNEL_ID, old.url
                    )
                except TelegramAPIError:
                    pass
                await uow.invite_links.mark_revoked(old)

            invite = await self._bot.create_chat_invite_link(
                chat_id=settings.CHANNEL_ID,
                member_limit=1,
                expire_date=int(expires_at.timestamp()),
            )

            return await uow.invite_links.add(
                user_id=user_id,
                subscription_id=subscription_id,
                url=invite.invite_link,
                expires_at=expires_at,
            )

    async def get_active_by_user(self, user_id: int) -> InviteLink | None:
        """Return the newest non-revoked invite link for a user, if any."""
        async with UnitOfWork(self._session_factory) as uow:
            links = await uow.invite_links.get_active_by_user(user_id)
            return links[0] if links else None