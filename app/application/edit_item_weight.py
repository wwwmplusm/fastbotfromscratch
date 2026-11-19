from decimal import Decimal
from uuid import UUID

from app.application.ports import UnitOfWork
from app.application.results import InvalidItemWeight, NotEditable, NotFound, WeightUpdated
from app.domain.errors import InvalidWeight, ItemNotFound
from app.domain.states import EntryStatus


class EditFoodItemWeight:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def execute(
        self,
        *,
        user_id: UUID,
        item_id: UUID,
        weight_g: Decimal,
    ) -> WeightUpdated | NotFound | NotEditable | InvalidItemWeight:
        entry = await self.uow.entries.get_by_item_for_update(item_id, user_id)
        if entry is None:
            await self.uow.commit()
            return NotFound()
        if entry.status != EntryStatus.DRAFT:
            await self.uow.commit()
            return NotEditable(entry.status)
        try:
            entry.change_weight(item_id, weight_g)
        except InvalidWeight:
            await self.uow.commit()
            return InvalidItemWeight()
        except ItemNotFound:
            await self.uow.commit()
            return NotFound()
        await self.uow.entries.save(entry)
        await self.uow.commit()
        return WeightUpdated(entry)
