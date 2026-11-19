import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup

from app.application.create_draft import attach_card_message
from app.application.ports import UnitOfWork
from app.application.results import DraftFailed, DraftReady, NotEditable, NotFound
from app.domain.entry import FoodEntry
from app.domain.states import EntryStatus
from app.domain.user import User
from app.bot.rendering import render_draft, render_failure

logger = logging.getLogger(__name__)

NOT_FOUND = "Запись не найдена или уже недоступна."
ALREADY = "Эта запись уже обработана и больше не редактируется."
EMPTY = "В черновике нет позиций. Повторите анализ или отмените его."
MESSAGE_LIMIT = 4000


def clip(text: str) -> str:
    if len(text) <= MESSAGE_LIMIT:
        return text
    return text[: MESSAGE_LIMIT - 1] + "…"


def parse_uuid(value: str):
    from uuid import UUID

    try:
        return UUID(value)
    except ValueError:
        return None


async def edit_or_send(
    bot: Bot,
    chat_id: int,
    message_id: int | None,
    text: str,
    markup: InlineKeyboardMarkup | None,
) -> tuple[int, int]:
    text = clip(text)
    if message_id is not None:
        try:
            await bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=markup)
            return chat_id, message_id
        except TelegramBadRequest as exc:
            if "message is not modified" in exc.message.lower():
                return chat_id, message_id
            logger.info("telegram edit failed, sending a new message")
    sent = await bot.send_message(chat_id, text, reply_markup=markup)
    return sent.chat.id, sent.message_id


def card_target(entry: FoodEntry, chat_id: int | None, message_id: int | None) -> tuple[int, int | None] | None:
    resolved_chat = entry.chat_id if entry.chat_id is not None else chat_id
    resolved_message = entry.message_id if entry.chat_id is not None else message_id
    if resolved_chat is None:
        return None
    return resolved_chat, resolved_message


async def persist_card_message(uow: UnitOfWork, entry: FoodEntry, chat_id: int, message_id: int) -> None:
    if entry.status != EntryStatus.DRAFT:
        return
    if entry.chat_id == chat_id and entry.message_id == message_id:
        return
    await attach_card_message(
        uow,
        entry_id=entry.id,
        user_id=entry.user_id,
        chat_id=chat_id,
        message_id=message_id,
    )


async def show_draft(bot: Bot, uow: UnitOfWork, user: User, entry: FoodEntry, markup) -> None:
    target = card_target(entry, entry.chat_id, entry.message_id)
    if target is None:
        return
    chat_id, message_id = target
    new_chat, new_message = await edit_or_send(
        bot,
        chat_id,
        message_id,
        render_draft(entry, user.timezone),
        markup,
    )
    await persist_card_message(uow, entry, new_chat, new_message)


async def show_recognition_result(
    bot: Bot,
    uow: UnitOfWork,
    user: User,
    result: DraftReady | DraftFailed | NotFound | NotEditable,
    markup_for_ready,
    markup_for_failure,
    *,
    fallback_chat_id: int | None = None,
    fallback_message_id: int | None = None,
) -> None:
    if isinstance(result, (NotFound, NotEditable)):
        return
    entry = result.entry
    if isinstance(result, DraftFailed) and not entry.items:
        text = render_failure(result.code)
        markup = markup_for_failure(entry.id)
    elif isinstance(result, DraftFailed):
        text = (
            "Не удалось обновить распознавание. Ниже предыдущий вариант.\n\n"
            + render_draft(entry, user.timezone)
        )
        markup = markup_for_ready(entry)
    else:
        text = render_draft(entry, user.timezone)
        markup = markup_for_ready(entry)
    target = card_target(entry, fallback_chat_id, fallback_message_id)
    if target is None:
        return
    chat_id, message_id = target
    new_chat, new_message = await edit_or_send(bot, chat_id, message_id, text, markup)
    await persist_card_message(uow, entry, new_chat, new_message)
