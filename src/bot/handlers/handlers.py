from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards.inline import method_keyboard, plans_keyboard
from src.bot.keyboards.reply import main_keyboard
from src.core.enums import PaymentMethod
from src.services.invite_link import InviteLinkService
from src.services.payment import PaymentService
from src.services.plan import PlanService
from src.services.subscription import SubscriptionService
from src.services.user import UserService


def register_handlers(
    router: Router,
    user_service: UserService,
    plan_service: PlanService,
    payment_service: PaymentService,
    subscription_service: SubscriptionService,
    invite_link_service: InviteLinkService,
) -> None:
    @router.message(Command("start"))
    async def cmd_start(message: Message) -> None:
        user = message.from_user
        if user is None:
            await message.answer("User not found.")
            return
        await user_service.get_or_create(
            user.id,
            user.username,
        )
        await message.answer("👋 Welcome!", reply_markup=main_keyboard())

    @router.message(Command("invite"))
    async def cmd_invite(message: Message) -> None:
        user = message.from_user
        if user is None:
            return
        db_user = await user_service.get_or_create(user.id, user.username)
        sub = await subscription_service.get_active_by_user(db_user.id)
        if sub is None:
            await message.answer("You have no active subscription.")
            return
        link = await invite_link_service.get_active_by_user(db_user.id)
        if link is None:
            link = await invite_link_service.grant(db_user.id, user.id, sub.id)
        await message.answer(f"🔑 Your access to the VIP channel:\n{link.url}")

    async def show_plans(message: Message) -> None:
        plans = await plan_service.get_all()
        await message.answer("Choose a plan:", reply_markup=plans_keyboard(plans))

    @router.message(Command("plans"))
    async def cmd_plans(message: Message) -> None:
        await show_plans(message)

    @router.message(F.text == "🛒 Plans")
    async def btn_plans(message: Message) -> None:
        await show_plans(message)

    @router.message(F.text == "📋 My subscription")
    async def btn_subscription(message: Message) -> None:
        user = message.from_user
        if user is None:
            return
        db_user = await user_service.get_or_create(user.id, user.username)
        sub = await subscription_service.get_active_by_user(db_user.id)
        if sub is None:
            await message.answer("You have no active subscription.")
        else:
            await message.answer(
                f"✅ Your subscription is active until {sub.end_date:%Y-%m-%d %H:%M} UTC"
            )

    @router.message(F.text == "❓ Help")
    async def btn_help(message: Message) -> None:
        await message.answer(
            "🛒 Use /plans to buy a subscription.\n📋 /status shows your subscription."
        )

    @router.callback_query(F.data.startswith("plan:"))
    async def cb_plan(callback: CallbackQuery) -> None:
        await callback.answer()
        data = callback.data
        if data is None:
            return
        message = callback.message
        if message is None:
            return
        plan_id = int(data.split(":")[1])
        await message.answer(
            "Choose payment method:",
            reply_markup=method_keyboard(plan_id, set(PaymentMethod)),
        )

    @router.callback_query(F.data.startswith("pay:"))
    async def cb_pay(callback: CallbackQuery) -> None:
        await callback.answer()
        data = callback.data
        if data is None:
            return
        message = callback.message
        if message is None:
            return
        _, plan_id, method_name = data.split(":")
        method = PaymentMethod[method_name.upper()]

        db_user = await user_service.get_or_create(
            callback.from_user.id,
            callback.from_user.username,
        )

        try:
            payment = await payment_service.create(db_user.id, int(plan_id), method)
        except ValueError:
            await message.answer("This payment method is not available yet.")
            return

        await message.answer(f"Pay here: {payment.pay_url}")
