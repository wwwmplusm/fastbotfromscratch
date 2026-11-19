from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks.entry_callbacks import DiaryCB


def diary_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Обновить", callback_data=DiaryCB(a="refresh").pack())],
        ]
    )
