from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from src.bot.keyboards.inline import method_keyboard, plans_keyboard
from src.bot.keyboards.reply import main_keyboard
from src.core.enums import PaymentMethod
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
) -> None:
    @router.message(Command("start"))
    async def cmd_start(message: Message):
        user = message.from_user
        if user is None:
            await message.answer("User not found.")
            return
        await user_service.get_or_create(
            user.id,
            user.username,
        )
        await message.answer("👋 Welcome!", reply_markup=main_keyboard())

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

        # TODO: Add more handlers for payment confirmation, plan selection, etc.
