import time

from aiogram import Router
from aiogram.enums import ChatType
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
            "/adminplans - list plans with ids\n"
            "/addplan <price_cents> <days> - add a plan\n"
            "/delplan <plan_id> - delete a plan\n"
            "\nGroup moderation:\n"
            "/ban (reply) [+ days] - kick from group + is_banned in DB\n"
            "/ban @username [+ days] - ban by username\n"
            "/unban (reply) or @username - unban from group + DB"
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

    @router.message(Command("unban"))
    async def cmd_unban(message: Message) -> None:
        if message.text is None:
            return
        parts = message.text.split()

        if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            if message.from_user is None:
                return
            member = await message.chat.get_member(message.from_user.id)
            if member.status.value not in ("creator", "administrator"):
                return
            target = None
            reply = message.reply_to_message
            if reply is not None and reply.from_user is not None:
                target = reply.from_user.id
            elif len(parts) >= 2:
                username = parts[1].lstrip("@")
                try:
                    user = await user_service.get_by_username(username)
                except UserNotFound:
                    user = None
                if user is not None:
                    target = user.telegram_id
            if target is None:
                await message.answer("Reply to the user's message or pass @username.")
                return
            await message.chat.unban(target)
            try:
                await user_service.unban(target)
            except UserNotFound:
                pass
            await message.answer(f"User {target} unbanned.")
            return

        if not await _is_admin(message):
            return
        if len(parts) < 2:
            await message.answer("Usage: /unban <telegram_id>")
            return
        try:
            await user_service.unban(int(parts[1]))
        except ValueError:
            await message.answer("telegram_id must be an integer.")
            return
        except UserNotFound:
            await message.answer("User not found.")
            return
        await message.answer(f"User {parts[1]} unbanned.")

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

    @router.message(Command("ban"))
    async def cmd_ban(message: Message) -> None:
        if message.from_user is None:
            return
        member = await message.chat.get_member(message.from_user.id)
        if member.status.value not in ("creator", "administrator"):
            return
        if message.text is None:
            return
        parts = message.text.split()
        target = None
        username = None
        days = 0

        reply = message.reply_to_message
        if reply is not None and reply.from_user is not None:
            target = reply.from_user.id
            username = reply.from_user.username
            if len(parts) > 1:
                try:
                    days = int(parts[1])
                except ValueError:
                    await message.answer("days must be an integer.")
                    return
        elif len(parts) >= 2:
            username = parts[1].lstrip("@")
            if len(parts) > 2:
                try:
                    days = int(parts[2])
                except ValueError:
                    await message.answer("days must be an integer.")
                    return
            try:
                user = await user_service.get_by_username(username)
            except UserNotFound:
                user = None
            if user is not None:
                target = user.telegram_id

        if target is None:
            await message.answer("Reply to the user's message or pass @username.")
            return

        until_date = int(time.time()) + days * 86400 if days > 0 else None
        await message.chat.ban(target, until_date=until_date)
        await user_service.ban_or_create(target, username)
        await message.answer(f"Banned user {target} for {days} days.")
