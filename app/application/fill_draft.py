import logging
from uuid import UUID

from app.application.ports import UnitOfWork
from app.application.results import DraftFailed, DraftReady, NotEditable, NotFound
from app.domain.states import EntryStatus
from app.services.nutrition_calculator import NutritionCalculator
from app.services.recognition import FoodRecognizer, RecognitionError

logger = logging.getLogger(__name__)


def clean_context(text: str | None) -> str | None:
    if text is None:
        return None
    cleaned = "".join(ch for ch in text if ch.isprintable() or ch in "\n\t")
    cleaned = " ".join(cleaned.split())
    return cleaned[:500] or None


async def mark_recognition_failed(
    uow: UnitOfWork,
    entry_id: UUID,
    user_id: UUID,
    code: str,
) -> DraftFailed | NotFound | NotEditable:
    entry = await uow.entries.get_for_update(entry_id, user_id)
    if entry is None:
        await uow.commit()
        return NotFound()
    if entry.status != EntryStatus.DRAFT:
        await uow.commit()
        return NotEditable(entry.status)
    return await _store_error(uow, entry, code)


async def fill_draft_from_image(
    uow: UnitOfWork,
    recognizer: FoodRecognizer,
    calculator: NutritionCalculator,
    *,
    entry_id: UUID,
    user_id: UUID,
    image: bytes,
    mime_type: str,
    user_text: str | None,
    max_bytes: int,
) -> DraftReady | DraftFailed | NotFound | NotEditable:
    entry = await uow.entries.get_for_update(entry_id, user_id)
    if entry is None:
        await uow.commit()
        return NotFound()
    if entry.status != EntryStatus.DRAFT:
        await uow.commit()
        return NotEditable(entry.status)
    if not image or len(image) > max_bytes:
        return await _store_error(uow, entry, "download_failed")
    try:
        recognized = await recognizer.recognize(image, mime_type, clean_context(user_text))
    except RecognitionError as exc:
        logger.info("recognition failed entry=%s code=%s", entry_id, exc.code)
        return await _store_error(uow, entry, exc.code)

    items = [
        calculator.build_item(
            entry.id,
            index,
            item.name,
            item.estimated_weight_g,
            item.recognition_note,
        )
        for index, item in enumerate(recognized)
    ]
    entry.replace_items(items)
    entry.recognition_error = None
    await uow.entries.save(entry)
    await uow.commit()
    logger.info("draft filled entry=%s items=%s", entry_id, len(items))
    return DraftReady(entry)


async def _store_error(uow: UnitOfWork, entry, code: str) -> DraftFailed:
    entry.recognition_error = code[:40]
    await uow.entries.save(entry)
    await uow.commit()
    return DraftFailed(entry, code)
