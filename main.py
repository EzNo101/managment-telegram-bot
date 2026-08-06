import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.bot.handlers.admin import register_admin_handlers
from src.bot.handlers.handlers import register_handlers
from src.core.config import settings
from src.core.enums import PaymentStatus
from src.core.exceptions import PaymentNotFound
from src.infra.db.session import AsyncSessionLocal
from src.providers.nowpayments import NowPaymentsProvider
from src.services.invite_link import InviteLinkService
from src.services.payment import PaymentService
from src.services.plan import PlanService
from src.services.subscription import SubscriptionService
from src.services.user import UserService
from src.services.workers import Worker


async def main():
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    provider = NowPaymentsProvider(
        api_key=settings.NOWPAYMENTS_API_KEY,
        ipn_secret=settings.NOWPAYMENTS_IPN_SECRET,
        ipn_callback_url=f"{settings.NOWPAYMENTS_WEBHOOK_URL}/webhook/nowpayments",
    )

    user_service = UserService(AsyncSessionLocal)
    plan_service = PlanService(AsyncSessionLocal)
    subscription_service = SubscriptionService(AsyncSessionLocal)
    payment_service = PaymentService(AsyncSessionLocal, subscription_service, provider)
    invite_link_service = InviteLinkService(bot, AsyncSessionLocal)

    router = Router()
    register_handlers(
        router,
        user_service,
        plan_service,
        payment_service,
        subscription_service,
        invite_link_service,
    )
    register_admin_handlers(router, user_service, plan_service)
    dp.include_router(router)

    # webhook for NOWPayments
    async def nowpayments_webhook(request: web.Request) -> web.Response:
        data = await request.json()
        headers = dict(request.headers)
        if not provider.verify_webhook(data, headers):
            return web.Response(status=401)
        provider_ref = str(data.get("invoice_id") or data.get("payment_id"))
        status_str = data.get("payment_status")

        try:
            if status_str == PaymentStatus.PAID.value:
                sub = await payment_service.confirm(provider_ref)
                if sub is not None:
                    user = await user_service.get_by_id(sub.user_id)
                    link = await invite_link_service.grant(
                        sub.user_id, user.telegram_id, sub.id
                    )
                    await bot.send_message(
                        user.telegram_id,
                        f"🎉 Payment confirmed! Your access to the VIP channel:\n{link.url}",
                    )
            elif status_str in {
                PaymentStatus.FAILED.value,
                PaymentStatus.EXPIRED.value,
                PaymentStatus.REFUNDED.value,
            }:
                await payment_service.set_status(
                    provider_ref, PaymentStatus(status_str)
                )
        except PaymentNotFound:
            return web.Response(status=404)
        return web.Response(status=200)

    web_app = web.Application()
    web_app.router.add_post("/webhook/nowpayments", nowpayments_webhook)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=8080)
    await site.start()

    worker = Worker(bot, AsyncSessionLocal)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(worker.expire_subs, "interval", minutes=10)
    scheduler.add_job(worker.stale_payments, "interval", hours=1)
    scheduler.add_job(worker.renew_reminders, "interval", hours=1)
    scheduler.start()

    await dp.start_polling(bot)  # type: ignore[arg-type]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
