from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.config import settings
from src.core.enums import PaymentStatus, SubscriptionStatus
from src.infra.db.uow import UnitOfWork

logger = logging.getLogger(__name__)


class Worker:
    def __init__(
        self,
        bot: Bot,
        session_factory: async_sessionmaker[AsyncSession],
    ):
        self._bot = bot
        self._session_factory = session_factory

    async def expire_subs(self) -> None:
        """Mark ended subscriptions as expired and kick users out of the channel."""
        async with UnitOfWork(self._session_factory) as uow:
            expired = await uow.subscriptions.get_expired()
            logger.info("expire_subs: found %d expired subscription(s)", len(expired))
            for sub in expired:
                user = await uow.users.get_by_id(sub.user_id)
                if user is None:
                    continue
                sub.status = SubscriptionStatus.EXPIRED
                try:
                    await self._bot.ban_chat_member(
                        settings.CHANNEL_ID, user.telegram_id
                    )
                except TelegramAPIError:
                    pass
                try:
                    await self._bot.send_message(
                        user.telegram_id,
                        "⏰ Your access to the VIP channel has expired.",
                    )
                except TelegramAPIError:
                    pass

    async def stale_payments(self) -> None:
        """Expire pending payments that have been sitting too long and notify users."""
        threshold = datetime.now(UTC) - timedelta(hours=settings.STALE_PAYMENT_TTL_HOURS)
        async with UnitOfWork(self._session_factory) as uow:
            stale = await uow.payments.get_stale(threshold)
            logger.info("stale_payments: found %d stale payment(s)", len(stale))
            for payment in stale:
                payment.status = PaymentStatus.EXPIRED
                user = await uow.users.get_by_id(payment.user_id)
                if user is None:
                    continue
                try:
                    await self._bot.send_message(
                        user.telegram_id,
                        "⚠️ Your payment has not been completed and was cancelled.",
                    )
                except TelegramAPIError:
                    pass

    async def renew_reminders(self) -> None:
        """Remind users whose subscription expires soon."""
        within = timedelta(days=settings.REMIND_DAYS_BEFORE)
        now = datetime.now(UTC)
        async with UnitOfWork(self._session_factory) as uow:
            expiring = await uow.subscriptions.get_expiring_soon(within)
            logger.info("renew_reminders: found %d expiring subscription(s)", len(expiring))
            for sub in expiring:
                user = await uow.users.get_by_id(sub.user_id)
                if user is None:
                    continue
                sub.reminded_at = now
                try:
                    await self._bot.send_message(
                        user.telegram_id,
                        f"🔔 Your subscription expires {sub.end_date:%Y-%m-%d %H:%M} "
                        "UTC. Use /plans to renew and keep access!",
                    )
                except TelegramAPIError:
                    continue