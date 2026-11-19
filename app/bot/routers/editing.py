from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.application.edit_item_weight import EditFoodItemWeight
from app.application.ports import UnitOfWork
from app.application.remove_item import RemoveFoodItem
from app.application.results import InvalidItemWeight, ItemRemoved, NotEditable, NotFound, WeightUpdated
from app.bot.callbacks.entry_callbacks import EntryAction, EntryCB, ItemAction, ItemCB
from app.bot.context import AppContext
from app.bot.keyboards.draft_keyboard import draft_keyboard, edit_menu_keyboard, weight_keyboard
from app.bot.rendering import render_edit_menu, render_weight_prompt
from app.bot.states import DraftEdit
from app.bot.ui import ALREADY, NOT_FOUND, card_target, edit_or_send, parse_uuid, persist_card_message, show_draft
from app.domain.states import EntryStatus
from app.domain.weight import parse_weight_text, validate_weight
from app.domain.errors import InvalidWeight

router = Router()


@router.callback_query(EntryCB.filter(), EntryAction("ed"))
async def open_edit_menu(
    callback: CallbackQuery,
    callback_data: EntryCB,
    bot: Bot,
    state: FSMContext,
    uow: UnitOfWork,
    app: AppContext,
) -> None:
    await state.clear()
    entry = await _load_draft(callback, callback_data.eid, uow, app)
    if entry is None:
        return
    await uow.commit()
    await _edit_card(bot, uow, entry, callback, render_edit_menu(entry), edit_menu_keyboard(entry))
    await callback.answer()


@router.callback_query(EntryCB.filter(), EntryAction("bk"))
async def back_to_draft(
    callback: CallbackQuery,
    callback_data: EntryCB,
    bot: Bot,
    state: FSMContext,
    uow: UnitOfWork,
    app: AppContext,
) -> None:
    await state.clear()
    entry = await _load_draft(callback, callback_data.eid, uow, app)
    if entry is None:
        return
    user = await uow.users.get_or_create(callback.from_user.id, app.settings.default_timezone)
    await uow.commit()
    await show_draft(bot, uow, user, entry, draft_keyboard(entry))
    await callback.answer()


@router.callback_query(ItemCB.filter(), ItemAction("w"))
async def ask_weight(
    callback: CallbackQuery,
    callback_data: ItemCB,
    bot: Bot,
    state: FSMContext,
    uow: UnitOfWork,
    app: AppContext,
) -> None:
    if callback.from_user is None:
        await callback.answer()
        return
    item_id = parse_uuid(callback_data.iid)
    if item_id is None:
        await callback.answer("Кнопка устарела.", show_alert=True)
        return
    user = await uow.users.get_or_create(callback.from_user.id, app.settings.default_timezone)
    entry = await uow.entries.get_by_item_for_update(item_id, user.id)
    if entry is None:
        await uow.commit()
        await callback.answer(NOT_FOUND, show_alert=True)
        return
    if entry.status != EntryStatus.DRAFT:
        await uow.commit()
        await callback.answer(ALREADY, show_alert=True)
        return
    item = next(candidate for candidate in entry.items if candidate.id == item_id)
    await uow.commit()
    await state.set_state(DraftEdit.waiting_weight)
    await state.update_data(item_id=str(item.id), entry_id=str(entry.id))
    await _edit_card(bot, uow, entry, callback, render_weight_prompt(item), weight_keyboard(entry.id))
    await callback.answer()


@router.callback_query(ItemCB.filter(), ItemAction("x"))
async def remove_item(
    callback: CallbackQuery,
    callback_data: ItemCB,
    bot: Bot,
    state: FSMContext,
    uow: UnitOfWork,
    app: AppContext,
) -> None:
    await state.clear()
    if callback.from_user is None:
        await callback.answer()
        return
    item_id = parse_uuid(callback_data.iid)
    if item_id is None:
        await callback.answer("Кнопка устарела.", show_alert=True)
        return
    user = await uow.users.get_or_create(callback.from_user.id, app.settings.default_timezone)
    result = await RemoveFoodItem(uow).execute(user_id=user.id, item_id=item_id)
    if isinstance(result, NotFound):
        await callback.answer(NOT_FOUND, show_alert=True)
        return
    if isinstance(result, NotEditable):
        await callback.answer(ALREADY, show_alert=True)
        return
    if not isinstance(result, ItemRemoved):
        await callback.answer()
        return
    await show_draft(bot, uow, user, result.entry, draft_keyboard(result.entry))
    await callback.answer("Позиция убрана")


@router.message(StateFilter(DraftEdit.waiting_weight), F.text, ~F.text.startswith("/"))
async def set_weight(message: Message, bot: Bot, state: FSMContext, uow: UnitOfWork, app: AppContext) -> None:
    if message.from_user is None or message.text is None:
        return
    parsed = parse_weight_text(message.text)
    if parsed is None:
        await message.answer("Введите вес числом в граммах, например 150.")
        return
    try:
        weight = validate_weight(parsed)
    except InvalidWeight:
        await message.answer("Вес должен быть от 1 до 5000 граммов.")
        return
    data = await state.get_data()
    item_id = parse_uuid(str(data.get("item_id", "")))
    if item_id is None:
        await state.clear()
        await message.answer("Не вижу, какую позицию менять. Откройте «Изменить» ещё раз.")
        return
    user = await uow.users.get_or_create(message.from_user.id, app.settings.default_timezone)
    result = await EditFoodItemWeight(uow).execute(user_id=user.id, item_id=item_id, weight_g=weight)
    if isinstance(result, InvalidItemWeight):
        await message.answer("Вес должен быть от 1 до 5000 граммов.")
        return
    if isinstance(result, NotFound):
        await state.clear()
        await message.answer(NOT_FOUND)
        return
    if isinstance(result, NotEditable):
        await state.clear()
        await message.answer(ALREADY)
        return
    if not isinstance(result, WeightUpdated):
        return
    await state.clear()
    await show_draft(bot, uow, user, result.entry, draft_keyboard(result.entry))
    try:
        await message.delete()
    except Exception:
        return


async def _load_draft(callback: CallbackQuery, raw_entry_id: str, uow: UnitOfWork, app: AppContext):
    if callback.from_user is None:
        await callback.answer()
        return None
    entry_id = parse_uuid(raw_entry_id)
    if entry_id is None:
        await callback.answer("Кнопка устарела.", show_alert=True)
        return None
    user = await uow.users.get_or_create(callback.from_user.id, app.settings.default_timezone)
    entry = await uow.entries.get(entry_id, user.id)
    if entry is None:
        await uow.commit()
        await callback.answer(NOT_FOUND, show_alert=True)
        return None
    if entry.status != EntryStatus.DRAFT:
        await uow.commit()
        await callback.answer(ALREADY, show_alert=True)
        return None
    return entry


async def _edit_card(bot: Bot, uow: UnitOfWork, entry, callback: CallbackQuery, text: str, markup) -> None:
    fallback_chat = callback.message.chat.id if callback.message else None
    fallback_message = callback.message.message_id if callback.message else None
    target = card_target(entry, fallback_chat, fallback_message)
    if target is None:
        return
    chat_id, message_id = target
    new_chat, new_message = await edit_or_send(bot, chat_id, message_id, text, markup)
    await persist_card_message(uow, entry, new_chat, new_message)
