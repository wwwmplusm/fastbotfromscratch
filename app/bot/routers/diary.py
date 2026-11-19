from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.application.get_daily_diary import GetDailyDiary
from app.application.ports import UnitOfWork
from app.bot.callbacks.entry_callbacks import DiaryCB
from app.bot.context import AppContext
from app.bot.keyboards.diary_keyboard import diary_keyboard
from app.bot.rendering import render_diary
from app.bot.ui import clip

router = Router()


@router.message(Command("today"))
async def today(message: Message, state: FSMContext, uow: UnitOfWork, app: AppContext) -> None:
    await state.clear()
    if message.from_user is None:
        return
    text = await _diary_text(uow, message.from_user.id, app)
    await message.answer(text, reply_markup=diary_keyboard())


@router.callback_query(DiaryCB.filter())
async def today_callback(
    callback: CallbackQuery,
    callback_data: DiaryCB,
    bot: Bot,
    state: FSMContext,
    uow: UnitOfWork,
    app: AppContext,
) -> None:
    await state.clear()
    if callback.from_user is None:
        await callback.answer()
        return
    text = await _diary_text(uow, callback.from_user.id, app)
    markup = diary_keyboard()
    if callback_data.a == "refresh" and callback.message is not None:
        try:
            await callback.message.edit_text(clip(text), reply_markup=markup)
        except TelegramBadRequest as exc:
            if "message is not modified" not in exc.message.lower():
                await callback.message.answer(clip(text), reply_markup=markup)
    elif callback.message is not None:
        await callback.message.answer(clip(text), reply_markup=markup)
    else:
        await bot.send_message(callback.from_user.id, clip(text), reply_markup=markup)
    await callback.answer()


async def _diary_text(uow: UnitOfWork, telegram_id: int, app: AppContext) -> str:
    user = await uow.users.get_or_create(telegram_id, app.settings.default_timezone)
    diary = await GetDailyDiary(uow).execute(user=user)
    return render_diary(diary)
