from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Plans")],
            [KeyboardButton(text="📋 My subscription"), KeyboardButton(text="❓ Help")],
        ],
        resize_keyboard=True,
    )
