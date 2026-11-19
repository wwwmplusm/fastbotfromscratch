from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks.entry_callbacks import DiaryCB, EntryCB, ItemCB
from app.bot.rendering import item_button_label
from app.domain.entry import FoodEntry


def draft_keyboard(entry: FoodEntry) -> InlineKeyboardMarkup:
    if entry.items:
        first_row = [
            InlineKeyboardButton(text="Изменить", callback_data=EntryCB(a="ed", eid=str(entry.id)).pack()),
            InlineKeyboardButton(text="Сохранить", callback_data=EntryCB(a="ok", eid=str(entry.id)).pack()),
        ]
    else:
        first_row = [
            InlineKeyboardButton(text="Повторить анализ", callback_data=EntryCB(a="re", eid=str(entry.id)).pack()),
        ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            first_row,
            [InlineKeyboardButton(text="Отмена", callback_data=EntryCB(a="no", eid=str(entry.id)).pack())],
        ]
    )


def failure_keyboard(entry_id: UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Повторить анализ", callback_data=EntryCB(a="re", eid=str(entry_id)).pack())],
            [InlineKeyboardButton(text="Отмена", callback_data=EntryCB(a="no", eid=str(entry_id)).pack())],
        ]
    )


def edit_menu_keyboard(entry: FoodEntry) -> InlineKeyboardMarkup:
    rows = []
    for item in entry.items:
        rows.append(
            [
                InlineKeyboardButton(text=item_button_label(item), callback_data=ItemCB(a="w", iid=str(item.id)).pack()),
                InlineKeyboardButton(text="✕", callback_data=ItemCB(a="x", iid=str(item.id)).pack()),
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="Повторить анализ", callback_data=EntryCB(a="re", eid=str(entry.id)).pack())]
    )
    rows.append([InlineKeyboardButton(text="Назад", callback_data=EntryCB(a="bk", eid=str(entry.id)).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def weight_keyboard(entry_id: UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data=EntryCB(a="bk", eid=str(entry_id)).pack())],
        ]
    )


def confirmed_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Дневник за сегодня", callback_data=DiaryCB(a="open").pack())],
        ]
    )
