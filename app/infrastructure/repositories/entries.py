from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.domain.entry import FoodEntry
from app.domain.states import EntryStatus
from app.infrastructure.database.models import FoodEntryItemORM, FoodEntryORM
from app.infrastructure.repositories.mappers import apply_entry, entry_to_domain, entry_to_orm


class SqlEntryRepository:
    def __init__(self, session) -> None:
        self.session = session

    async def add(self, entry: FoodEntry) -> None:
        self.session.add(entry_to_orm(entry))
        await self.session.flush()

    async def get(self, entry_id: UUID, user_id: UUID) -> FoodEntry | None:
        return await self._one(entry_id, user_id, lock=False)

    async def get_for_update(self, entry_id: UUID, user_id: UUID) -> FoodEntry | None:
        return await self._one(entry_id, user_id, lock=True)

    async def get_by_item_for_update(self, item_id: UUID, user_id: UUID) -> FoodEntry | None:
        stmt = (
            select(FoodEntryORM)
            .join(FoodEntryORM.items)
            .where(FoodEntryItemORM.id == item_id, FoodEntryORM.user_id == user_id)
            .options(selectinload(FoodEntryORM.items))
        )
        row = (await self.session.execute(self._lock(stmt, joined=True))).scalars().unique().one_or_none()
        if row is None:
            return None
        return entry_to_domain(row)

    async def save(self, entry: FoodEntry) -> None:
        row = await self.session.get(
            FoodEntryORM,
            entry.id,
            options=(selectinload(FoodEntryORM.items),),
            populate_existing=True,
        )
        if row is None:
            raise LookupError("entry is not persisted")
        if row.user_id != entry.user_id:
            raise PermissionError("owner mismatch")
        apply_entry(row, entry)
        await self.session.flush()

    async def list_confirmed(
        self,
        user_id: UUID,
        start: datetime,
        end: datetime,
    ) -> list[FoodEntry]:
        stmt = (
            select(FoodEntryORM)
            .where(
                FoodEntryORM.user_id == user_id,
                FoodEntryORM.status == EntryStatus.CONFIRMED.value,
                FoodEntryORM.eaten_at >= start,
                FoodEntryORM.eaten_at < end,
            )
            .order_by(FoodEntryORM.eaten_at.asc(), FoodEntryORM.id.asc())
            .options(selectinload(FoodEntryORM.items))
            .execution_options(populate_existing=True)
        )
        rows = (await self.session.execute(stmt)).scalars().unique().all()
        return [entry_to_domain(row) for row in rows]

    async def _one(self, entry_id: UUID, user_id: UUID, *, lock: bool) -> FoodEntry | None:
        stmt = (
            select(FoodEntryORM)
            .where(FoodEntryORM.id == entry_id, FoodEntryORM.user_id == user_id)
            .options(selectinload(FoodEntryORM.items))
        )
        if lock:
            stmt = self._lock(stmt, joined=False)
        else:
            stmt = stmt.execution_options(populate_existing=True)
        row = (await self.session.execute(stmt)).scalars().unique().one_or_none()
        if row is None:
            return None
        return entry_to_domain(row)

    def _lock(self, stmt, *, joined: bool):
        # Row locks are the concurrency control on PostgreSQL. SQLite tests cover the status checks.
        stmt = stmt.execution_options(populate_existing=True)
        bind = self.session.bind
        if bind is None or bind.dialect.name != "postgresql":
            return stmt
        if joined:
            return stmt.with_for_update(of=FoodEntryORM)
        return stmt.with_for_update()
