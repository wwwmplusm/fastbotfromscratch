from aiogram import BaseMiddleware

from app.bot.context import AppContext
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


class SessionMiddleware(BaseMiddleware):
    def __init__(self, session_factory, app: AppContext) -> None:
        self.session_factory = session_factory
        self.app = app

    async def __call__(self, handler, event, data):
        data["app"] = self.app
        async with self.session_factory() as session:
            data["uow"] = SqlAlchemyUnitOfWork(session)
            try:
                return await handler(event, data)
            except Exception:
                await session.rollback()
                raise
