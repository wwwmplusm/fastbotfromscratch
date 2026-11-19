from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.domain.user import User
from app.infrastructure.database.models import UserORM
from app.infrastructure.repositories.mappers import user_to_domain, user_to_orm


class SqlUserRepository:
    def __init__(self, session) -> None:
        self.session = session

    async def get_or_create(self, telegram_id: int, timezone_name: str) -> User:
        existing = await self._by_telegram(telegram_id)
        if existing is not None:
            return existing
        user = User(
            id=uuid4(),
            telegram_id=telegram_id,
            timezone=timezone_name,
            created_at=datetime.now(timezone.utc),
        )
        try:
            async with self.session.begin_nested():
                self.session.add(user_to_orm(user))
                await self.session.flush()
        except IntegrityError:
            loaded = await self._by_telegram(telegram_id)
            if loaded is None:
                raise
            return loaded
        return user

    async def _by_telegram(self, telegram_id: int) -> User | None:
        stmt = select(UserORM).where(UserORM.telegram_id == telegram_id)
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return user_to_domain(row)
