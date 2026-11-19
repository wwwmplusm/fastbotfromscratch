import logging
from datetime import datetime, timezone
from uuid import UUID

from app.application.ports import UnitOfWork
from app.application.results import AlreadyProcessed, Confirmed, EmptyDraft, NotFound
from app.domain.states import EntryStatus

logger = logging.getLogger(__name__)


class ConfirmEntry:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def execute(self, *, entry_id: UUID, user_id: UUID) -> Confirmed | AlreadyProcessed | EmptyDraft | NotFound:
        entry = await self.uow.entries.get_for_update(entry_id, user_id)
        if entry is None:
            await self.uow.commit()
            return NotFound()
        if entry.status != EntryStatus.DRAFT:
            await self.uow.commit()
            return AlreadyProcessed(entry.status)
        if not entry.items:
            await self.uow.commit()
            return EmptyDraft(entry)
        entry.confirm(datetime.now(timezone.utc))
        await self.uow.entries.save(entry)
        await self.uow.commit()
        logger.info("entry confirmed entry=%s user=%s", entry_id, user_id)
        return Confirmed(entry)
