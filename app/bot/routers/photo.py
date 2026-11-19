import logging
from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.application.create_draft import CreateDraftFromPhoto, attach_card_message
from app.application.fill_draft import mark_recognition_failed
from app.application.ports import UnitOfWork
from app.application.retry_recognition import RetryRecognition
from app.bot.callbacks.entry_callbacks import EntryAction, EntryCB
from app.bot.context import AppContext
from app.bot.files import DownloadError, download_photo
from app.bot.keyboards.draft_keyboard import draft_keyboard, failure_keyboard
from app.bot.rendering import render_analyzing
from app.bot.ui import (
    NOT_FOUND,
    edit_or_send,
    parse_uuid,
    show_recognition_result,
)
from app.domain.states import EntryStatus

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.photo)
async def on_photo(message: Message, bot: Bot, state: FSMContext, uow: UnitOfWork, app: AppContext) -> None:
    await state.clear()
    if message.from_user is None or not message.photo:
        return
    photo = message.photo[-1]
    if photo.file_size and photo.file_size > app.settings.max_image_bytes:
        await message.answer("Фото больше 8 МБ. Пришлите снимок поменьше.")
        return

    user = await uow.users.get_or_create(message.from_user.id, app.settings.default_timezone)
    draft = await CreateDraftFromPhoto(uow, app.recognizer, app.calculator, app.settings.max_image_bytes).start(
        user_id=user.id,
        photo_file_id=photo.file_id,
        eaten_at=datetime.now(timezone.utc),
    )
    sent = await message.answer(render_analyzing())
    draft.chat_id = sent.chat.id
    draft.message_id = sent.message_id
    await attach_card_message(
        uow,
        entry_id=draft.id,
        user_id=user.id,
        chat_id=sent.chat.id,
        message_id=sent.message_id,
    )
    await bot.send_chat_action(message.chat.id, "typing")
    try:
        image = await download_photo(bot, photo.file_id, app.settings.max_image_bytes)
        result = await CreateDraftFromPhoto(
            uow, app.recognizer, app.calculator, app.settings.max_image_bytes
        ).complete(
            entry_id=draft.id,
            user_id=user.id,
            image=image,
            mime_type="image/jpeg",
            user_text=message.caption,
        )
    except DownloadError:
        result = await mark_recognition_failed(uow, draft.id, user.id, "download_failed")
    except Exception:
        logger.exception("photo pipeline failed entry=%s", draft.id)
        await uow.rollback()
        result = await mark_recognition_failed(uow, draft.id, user.id, "unexpected")

    await show_recognition_result(
        bot,
        uow,
        user,
        result,
        draft_keyboard,
        failure_keyboard,
        fallback_chat_id=sent.chat.id,
        fallback_message_id=sent.message_id,
    )


@router.callback_query(EntryCB.filter(), EntryAction("re"))
async def retry(callback: CallbackQuery, callback_data: EntryCB, bot: Bot, state: FSMContext, uow: UnitOfWork, app: AppContext) -> None:
    await state.clear()
    if callback.from_user is None:
        await callback.answer()
        return
    entry_id = parse_uuid(callback_data.eid)
    if entry_id is None:
        await callback.answer("Кнопка устарела.", show_alert=True)
        return
    user = await uow.users.get_or_create(callback.from_user.id, app.settings.default_timezone)
    entry = await uow.entries.get(entry_id, user.id)
    if entry is None:
        await uow.commit()
        await callback.answer(NOT_FOUND, show_alert=True)
        return
    if entry.status != EntryStatus.DRAFT or not entry.photo_file_id:
        await uow.commit()
        await callback.answer("Этот черновик уже нельзя распознать заново.", show_alert=True)
        return
    await uow.commit()
    await callback.answer()
    chat_id = entry.chat_id or (callback.message.chat.id if callback.message else callback.from_user.id)
    message_id = entry.message_id if entry.chat_id is not None else (callback.message.message_id if callback.message else None)
    await edit_or_send(bot, chat_id, message_id, render_analyzing(), None)
    await bot.send_chat_action(chat_id, "typing")
    try:
        image = await download_photo(bot, entry.photo_file_id, app.settings.max_image_bytes)
        result = await RetryRecognition(uow, app.recognizer, app.calculator, app.settings.max_image_bytes).execute(
            entry_id=entry.id,
            user_id=user.id,
            image=image,
            mime_type="image/jpeg",
            user_text=None,
        )
    except DownloadError:
        result = await mark_recognition_failed(uow, entry.id, user.id, "download_failed")
    except Exception:
        logger.exception("retry failed entry=%s", entry.id)
        await uow.rollback()
        result = await mark_recognition_failed(uow, entry.id, user.id, "unexpected")
    await show_recognition_result(
        bot,
        uow,
        user,
        result,
        draft_keyboard,
        failure_keyboard,
        fallback_chat_id=chat_id,
        fallback_message_id=message_id,
    )
