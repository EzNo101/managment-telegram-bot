from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.core.enums import PaymentMethod
from src.infra.db.models.plan import Plan


def plans_keyboard(plans: list[Plan]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    for plan in plans:
        kb.button(
            text=f"{plan.duration_days} - {plan.price_usd / 100:.2f}$",
            callback_data=f"plan:{plan.id}",
        )
    kb.adjust(1)

    return kb.as_markup()


def pay_keyboard(url: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Pay now", url=url)
    return kb.as_markup()


_METHOD_LABELS = {
    PaymentMethod.BITCOIN: "₿ Bitcoin (BTC)",
    PaymentMethod.USDT: "💵 USDT (TRC20)",
    PaymentMethod.SKRILL: "💸 Skrill",
    PaymentMethod.STRIPE: "💳 Card · Google Pay · Apple Pay · PayPal",
}


def method_keyboard(plan_id: int, methods: set[PaymentMethod]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    for method in PaymentMethod:
        if method in methods:
            kb.button(
                text=_METHOD_LABELS.get(method, method.value),
                callback_data=f"pay:{plan_id}:{method.name.lower()}",
            )
    kb.adjust(1)

    return kb.as_markup()
