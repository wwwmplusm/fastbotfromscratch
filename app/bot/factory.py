import logging

from aiogram import Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent

from app.bot.context import AppContext
from app.bot.middlewares import SessionMiddleware
from app.bot.routers import confirmation, diary, editing, fallback, photo, start

logger = logging.getLogger(__name__)


def build_dispatcher(app: AppContext, session_factory) -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.update.middleware(SessionMiddleware(session_factory, app))
    dispatcher.include_router(start.router)
    dispatcher.include_router(diary.router)
    dispatcher.include_router(photo.router)
    dispatcher.include_router(confirmation.router)
    dispatcher.include_router(editing.router)
    dispatcher.include_router(fallback.router)

    @dispatcher.errors()
    async def on_error(event: ErrorEvent) -> None:
        logger.exception("update failed", exc_info=event.exception)
        update = event.update
        try:
            if update.callback_query is not None:
                await update.callback_query.answer(
                    "Не получилось выполнить действие. Попробуйте ещё раз.",
                    show_alert=True,
                )
            elif update.message is not None:
                await update.message.answer("Не получилось обработать сообщение. Попробуйте ещё раз.")
        except TelegramBadRequest:
            return

    return dispatcher
