from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.entry import FoodEntry
from app.domain.user import User


class EntryRepository(Protocol):
    async def add(self, entry: FoodEntry) -> None: ...

    async def get(self, entry_id: UUID, user_id: UUID) -> FoodEntry | None: ...

    async def get_for_update(self, entry_id: UUID, user_id: UUID) -> FoodEntry | None: ...

    async def get_by_item_for_update(self, item_id: UUID, user_id: UUID) -> FoodEntry | None: ...

    async def save(self, entry: FoodEntry) -> None: ...

    async def list_confirmed(self, user_id: UUID, start: datetime, end: datetime) -> list[FoodEntry]: ...


class UserRepository(Protocol):
    async def get_or_create(self, telegram_id: int, timezone_name: str) -> User: ...


class UnitOfWork(Protocol):
    entries: EntryRepository
    users: UserRepository

    async def commit(self) -> None: ...
