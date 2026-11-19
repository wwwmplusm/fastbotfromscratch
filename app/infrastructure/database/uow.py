from app.infrastructure.repositories.entries import SqlEntryRepository
from app.infrastructure.repositories.users import SqlUserRepository


class SqlAlchemyUnitOfWork:
    def __init__(self, session) -> None:
        self.session = session
        self.entries = SqlEntryRepository(session)
        self.users = SqlUserRepository(session)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
