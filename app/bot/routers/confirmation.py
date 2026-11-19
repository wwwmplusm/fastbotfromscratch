from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.application.cancel_draft import CancelDraft
from app.application.confirm_entry import ConfirmEntry
from app.application.ports import UnitOfWork
from app.application.results import AlreadyProcessed, Cancelled, Confirmed, EmptyDraft, NotFound
from app.bot.callbacks.entry_callbacks import EntryAction, EntryCB
from app.bot.context import AppContext
from app.bot.keyboards.draft_keyboard import confirmed_keyboard
from app.bot.rendering import render_cancelled, render_confirmed
from app.bot.ui import ALREADY, EMPTY, NOT_FOUND, card_target, edit_or_send, parse_uuid

router = Router()


@router.callback_query(EntryCB.filter(), EntryAction("ok"))
async def confirm(
    callback: CallbackQuery,
    callback_data: EntryCB,
    bot: Bot,
    state: FSMContext,
    uow: UnitOfWork,
    app: AppContext,
) -> None:
    await state.clear()
    if callback.from_user is None:
        await callback.answer()
        return
    entry_id = parse_uuid(callback_data.eid)
    if entry_id is None:
        await callback.answer("Кнопка устарела.", show_alert=True)
        return
    user = await uow.users.get_or_create(callback.from_user.id, app.settings.default_timezone)
    result = await ConfirmEntry(uow).execute(entry_id=entry_id, user_id=user.id)
    if isinstance(result, NotFound):
        await callback.answer(NOT_FOUND, show_alert=True)
        return
    if isinstance(result, AlreadyProcessed):
        await callback.answer(ALREADY, show_alert=True)
        return
    if isinstance(result, EmptyDraft):
        await callback.answer(EMPTY, show_alert=True)
        return
    if not isinstance(result, Confirmed):
        await callback.answer()
        return
    await _replace_card(bot, result.entry, callback, render_confirmed(result.entry, user.timezone), confirmed_keyboard())
    await callback.answer("Сохранено в дневник")


@router.callback_query(EntryCB.filter(), EntryAction("no"))
async def cancel(
    callback: CallbackQuery,
    callback_data: EntryCB,
    bot: Bot,
    state: FSMContext,
    uow: UnitOfWork,
    app: AppContext,
) -> None:
    await state.clear()
    if callback.from_user is None:
        await callback.answer()
        return
    entry_id = parse_uuid(callback_data.eid)
    if entry_id is None:
        await callback.answer("Кнопка устарела.", show_alert=True)
        return
    user = await uow.users.get_or_create(callback.from_user.id, app.settings.default_timezone)
    result = await CancelDraft(uow).execute(entry_id=entry_id, user_id=user.id)
    if isinstance(result, NotFound):
        await callback.answer(NOT_FOUND, show_alert=True)
        return
    if isinstance(result, AlreadyProcessed):
        await callback.answer(ALREADY, show_alert=True)
        return
    if not isinstance(result, Cancelled):
        await callback.answer()
        return
    await _replace_card(bot, result.entry, callback, render_cancelled(), None)
    await callback.answer("Черновик отменён")


async def _replace_card(bot: Bot, entry, callback: CallbackQuery, text: str, markup) -> None:
    fallback_chat = callback.message.chat.id if callback.message else None
    fallback_message = callback.message.message_id if callback.message else None
    target = card_target(entry, fallback_chat, fallback_message)
    if target is None:
        return
    chat_id, message_id = target
    await edit_or_send(bot, chat_id, message_id, text, markup)
