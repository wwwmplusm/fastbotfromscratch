import logging
from datetime import datetime
from uuid import UUID

from app.application.fill_draft import fill_draft_from_image
from app.application.ports import UnitOfWork
from app.application.results import DraftFailed, DraftReady, NotEditable, NotFound
from app.domain.entry import FoodEntry
from app.domain.states import EntryStatus
from app.services.nutrition_calculator import NutritionCalculator
from app.services.recognition import FoodRecognizer

logger = logging.getLogger(__name__)


class CreateDraftFromPhoto:
    def __init__(
        self,
        uow: UnitOfWork,
        recognizer: FoodRecognizer,
        calculator: NutritionCalculator,
        max_bytes: int,
    ) -> None:
        self.uow = uow
        self.recognizer = recognizer
        self.calculator = calculator
        self.max_bytes = max_bytes

    async def start(self, *, user_id: UUID, photo_file_id: str, eaten_at: datetime) -> FoodEntry:
        entry = FoodEntry.create_draft(
            user_id=user_id,
            photo_file_id=photo_file_id,
            eaten_at=eaten_at,
        )
        await self.uow.entries.add(entry)
        await self.uow.commit()
        logger.info("draft created entry=%s user=%s", entry.id, user_id)
        return entry

    async def complete(
        self,
        *,
        entry_id: UUID,
        user_id: UUID,
        image: bytes,
        mime_type: str,
        user_text: str | None,
    ) -> DraftReady | DraftFailed | NotFound | NotEditable:
        return await fill_draft_from_image(
            self.uow,
            self.recognizer,
            self.calculator,
            entry_id=entry_id,
            user_id=user_id,
            image=image,
            mime_type=mime_type,
            user_text=user_text,
            max_bytes=self.max_bytes,
        )


async def attach_card_message(
    uow: UnitOfWork,
    *,
    entry_id: UUID,
    user_id: UUID,
    chat_id: int,
    message_id: int,
) -> None:
    entry = await uow.entries.get_for_update(entry_id, user_id)
    if entry is None or entry.status != EntryStatus.DRAFT:
        await uow.commit()
        return
    entry.chat_id = chat_id
    entry.message_id = message_id
    await uow.entries.save(entry)
    await uow.commit()
