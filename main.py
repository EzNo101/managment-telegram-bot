import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiohttp import web
from apscheduler.schedulers.asyncio import (  # pyright: ignore[reportMissingTypeStubs]
    AsyncIOScheduler,
)

from src.bot.handlers.admin import register_admin_handlers
from src.bot.handlers.handlers import register_handlers
from src.bot.middlewares import BanMiddleware
from src.core.config import settings
from src.core.enums import PaymentMethod, PaymentStatus
from src.core.exceptions import PaymentNotFound
from src.infra.db.session import AsyncSessionLocal
from src.providers.nowpayments import NowPaymentsProvider
from src.providers.protocol import PaymentProvider
from src.providers.skrill import SkrillProvider
from src.providers.stripe import StripeProvider
from src.services.invite_link import InviteLinkService
from src.services.payment import PaymentService
from src.services.plan import PlanService
from src.services.subscription import SubscriptionService
from src.services.user import UserService
from src.services.workers import Worker


async def main():
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    nowpayments_provider = NowPaymentsProvider(
        api_key=settings.NOWPAYMENTS_API_KEY,
        ipn_secret=settings.NOWPAYMENTS_IPN_SECRET,
        ipn_callback_url=f"{settings.NOWPAYMENTS_WEBHOOK_URL}/webhook/nowpayments",
    )
    providers: dict[PaymentMethod, PaymentProvider] = {
        PaymentMethod.BITCOIN: nowpayments_provider,
        PaymentMethod.USDT: nowpayments_provider,
    }
    stripe_provider: StripeProvider | None = None
    if settings.STRIPE_SECRET_KEY:
        stripe_provider = StripeProvider(
            api_key=settings.STRIPE_SECRET_KEY,
            webhook_secret=settings.STRIPE_WEBHOOK_SECRET,
            success_url=settings.STRIPE_SUCCESS_URL,
            cancel_url=settings.STRIPE_CANCEL_URL,
        )
        providers.update({PaymentMethod.STRIPE: stripe_provider})

    skrill_provider: SkrillProvider | None = None
    if settings.SKRILL_SECRET_WORD:
        skrill_provider = SkrillProvider(
            pay_to_email=settings.SKRILL_PAY_TO_EMAIL,
            merchant_id=settings.SKRILL_MERCHANT_ID,
            secret_word=settings.SKRILL_SECRET_WORD,
            status_url=f"{settings.SKRILL_WEBHOOK_URL}/webhook/skrill",
            return_url=settings.SKRILL_RETURN_URL,
            cancel_url=settings.SKRILL_CANCEL_URL,
        )
        providers.update({PaymentMethod.SKRILL: skrill_provider})

    user_service = UserService(AsyncSessionLocal)
    plan_service = PlanService(AsyncSessionLocal)
    subscription_service = SubscriptionService(AsyncSessionLocal)
    payment_service = PaymentService(AsyncSessionLocal, subscription_service, providers)
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

    dp.message.outer_middleware(BanMiddleware(user_service))
    dp.callback_query.outer_middleware(BanMiddleware(user_service))

    async def confirm_and_grant(provider_ref: str) -> None:
        sub = await payment_service.confirm(provider_ref)
        if sub is None:
            return
        user = await user_service.get_by_id(sub.user_id)
        link = await invite_link_service.grant(sub.user_id, user.telegram_id, sub.id)
        await bot.send_message(
            user.telegram_id,
            f"🎉 Payment confirmed! Your access to the VIP channel:\n{link.url}",
        )

    # webhook for NOWPayments
    async def nowpayments_webhook(request: web.Request) -> web.Response:
        data = await request.json()
        headers = dict(request.headers)
        if not nowpayments_provider.verify_webhook(data, headers):
            return web.Response(status=401)
        provider_ref = str(data.get("invoice_id") or data.get("payment_id"))
        status_str = data.get("payment_status")

        try:
            if status_str == PaymentStatus.PAID.value:
                await confirm_and_grant(provider_ref)
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

    # webhook for Stripe (if configured)
    web_app = web.Application()
    web_app.router.add_post("/webhook/nowpayments", nowpayments_webhook)

    if skrill_provider is not None:
        # Skrill status: 2 processed, -1 cancelled, -2 failed, -3 chargeback
        async def skrill_webhook(request: web.Request) -> web.Response:
            data = dict(await request.post())
            if not skrill_provider.verify_webhook(data, dict(request.headers)):
                return web.Response(status=401)
            provider_ref = data.get("transaction_id")
            status = data.get("status")
            try:
                if status == "2":
                    await confirm_and_grant(provider_ref)
                elif status == "-3":
                    await payment_service.set_status(provider_ref, PaymentStatus.REFUNDED)
                elif status == "-2":
                    await payment_service.set_status(provider_ref, PaymentStatus.FAILED)
                elif status == "-1":
                    await payment_service.set_status(provider_ref, PaymentStatus.EXPIRED)
            except PaymentNotFound:
                return web.Response(status=404)
            return web.Response(status=200)

        web_app.router.add_post("/webhook/skrill", skrill_webhook)

    if stripe_provider is not None:
        async def stripe_webhook(request: web.Request) -> web.Response:
            body = await request.read()
            event = stripe_provider.verify_webhook(body, dict(request.headers))
            if event is None:
                return web.Response(status=401)
            event_type = event.get("type")
            session = event.get("data", {}).get("object", {})

            try:
                if (
                    event_type == "checkout.session.completed"
                    and session.get("payment_status") == "paid"
                ):
                    await confirm_and_grant(str(session["id"]))
                elif event_type == "checkout.session.expired":
                    await payment_service.set_status(
                        str(session["id"]), PaymentStatus.EXPIRED
                    )
                elif event_type == "payment_intent.payment_failed":
                    await payment_service.set_status(
                        str(session["id"]), PaymentStatus.FAILED
                    )
            except PaymentNotFound:
                return web.Response(status=404)
            return web.Response(status=200)

        web_app.router.add_post("/webhook/stripe", stripe_webhook)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=8080)
    await site.start()

    worker = Worker(bot, AsyncSessionLocal)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(worker.expire_subs, "interval", minutes=10)  #  pyright: ignore[reportUnknownMemberType]
    scheduler.add_job(worker.stale_payments, "interval", hours=1)  #  pyright: ignore[reportUnknownMemberType]
    scheduler.add_job(worker.renew_reminders, "interval", hours=1)  #  pyright: ignore[reportUnknownMemberType]
    scheduler.start()

    await dp.start_polling(bot)  # type: ignore[arg-type]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
