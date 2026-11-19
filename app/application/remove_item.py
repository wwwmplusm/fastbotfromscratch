from uuid import UUID

from app.application.ports import UnitOfWork
from app.application.results import ItemRemoved, NotEditable, NotFound
from app.domain.errors import ItemNotFound
from app.domain.states import EntryStatus


class RemoveFoodItem:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def execute(self, *, user_id: UUID, item_id: UUID) -> ItemRemoved | NotFound | NotEditable:
        entry = await self.uow.entries.get_by_item_for_update(item_id, user_id)
        if entry is None:
            await self.uow.commit()
            return NotFound()
        if entry.status != EntryStatus.DRAFT:
            await self.uow.commit()
            return NotEditable(entry.status)
        try:
            entry.remove_item(item_id)
        except ItemNotFound:
            await self.uow.commit()
            return NotFound()
        await self.uow.entries.save(entry)
        await self.uow.commit()
        return ItemRemoved(entry)
