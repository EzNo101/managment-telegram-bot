from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.core.exceptions import PlanNotFound, UserNotFound
from src.services.plan import PlanService
from src.services.user import UserService


def register_admin_handlers(
    router: Router,
    user_service: UserService,
    plan_service: PlanService,
) -> None:
    async def _is_admin(message: Message) -> bool:
        user = message.from_user
        if user is None:
            return False
        return await user_service.is_admin(user.id)

    @router.message(Command("admin"))
    async def cmd_admin(message: Message) -> None:
        if not await _is_admin(message):
            return
        await message.answer(
            "🛠 Admin panel:\n"
            "/users - list all users\n"
            "/ban <tg_id> - ban a user\n"
            "/unban <tg_id> - unban a user\n"
            "/adminplans - list plans with ids\n"
            "/addplan <price_cents> <days> - add a plan\n"
            "/delplan <plan_id> - delete a plan"
        )

    @router.message(Command("users"))
    async def cmd_users(message: Message) -> None:
        if not await _is_admin(message):
            return
        users = await user_service.get_all()
        if not users:
            await message.answer("No users yet.")
            return
        lines = [
            f"@{u.username or '-'} tg={u.telegram_id}"
            f"{' 👑' if u.is_admin else ''}{' 🚫' if u.is_banned else ''}"
            for u in users
        ]
        await message.answer("\n".join(lines))

    @router.message(Command("ban"))
    async def cmd_ban(message: Message) -> None:
        if message.text is None:
            return
        if not await _is_admin(message):
            return
        args = message.text.split()
        if len(args) < 2:
            await message.answer("Usage: /ban <telegram_id>")
            return
        try:
            await user_service.ban(int(args[1]))
        except ValueError:
            await message.answer("telegram_id must be an integer.")
            return
        except UserNotFound:
            await message.answer("User not found.")
            return
        await message.answer(f"User {args[1]} banned.")

    @router.message(Command("unban"))
    async def cmd_unban(message: Message) -> None:
        if not await _is_admin(message):
            return
        if message.text is None:
            return
        args = message.text.split()
        if len(args) < 2:
            await message.answer("Usage: /unban <telegram_id>")
            return
        try:
            await user_service.unban(int(args[1]))
        except ValueError:
            await message.answer("telegram_id must be an integer.")
            return
        except UserNotFound:
            await message.answer("User not found.")
            return
        await message.answer(f"User {args[1]} unbanned.")

    @router.message(Command("adminplans"))
    async def cmd_adminplans(message: Message) -> None:
        if not await _is_admin(message):
            return
        plans = await plan_service.get_all()
        if not plans:
            await message.answer("No plans yet.")
            return
        lines = [
            f"id={p.id}  ${p.price_usd / 100:.2f} / {p.duration_days} days"
            for p in plans
        ]
        await message.answer("\n".join(lines))

    @router.message(Command("addplan"))
    async def cmd_addplan(message: Message) -> None:
        if not await _is_admin(message):
            return
        if message.text is None:
            return
        args = message.text.split()
        if len(args) < 3:
            await message.answer("Usage: /addplan <price_cents> <days>")
            return
        try:
            price, days = int(args[1]), int(args[2])
        except ValueError:
            await message.answer("price_cents and days must be integers.")
            return
        plan = await plan_service.add(price, days)
        await message.answer(
            f"Plan added: id={plan.id} ${price / 100:.2f} / {days} days"
        )

    @router.message(Command("delplan"))
    async def cmd_delplan(message: Message) -> None:
        if not await _is_admin(message):
            return
        if message.text is None:
            return
        args = message.text.split()
        if len(args) < 2:
            await message.answer("Usage: /delplan <plan_id>")
            return
        try:
            await plan_service.delete(int(args[1]))
        except ValueError:
            await message.answer("plan_id must be an integer.")
            return
        except PlanNotFound:
            await message.answer("Plan not found.")
            return
        await message.answer(f"Plan {args[1]} deleted.")
