from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.application.cancel_draft import CancelDraft
from app.application.confirm_entry import ConfirmEntry
from app.application.create_draft import CreateDraftFromPhoto
from app.application.edit_item_weight import EditFoodItemWeight
from app.application.get_daily_diary import GetDailyDiary
from app.application.remove_item import RemoveFoodItem
from app.application.results import (
    AlreadyProcessed,
    Cancelled,
    Confirmed,
    DraftFailed,
    DraftReady,
    EmptyDraft,
    ItemRemoved,
    NotFound,
    WeightUpdated,
)
from app.application.retry_recognition import RetryRecognition
from app.domain.states import EntryStatus
from app.domain.time import local_day_bounds
from app.infrastructure.database.models import Base, FoodEntryORM
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork
from app.services.food_catalog import FoodCatalog
from app.services.nutrition_calculator import NutritionCalculator
from app.services.recognition import RecognitionTimeout, RecognizedItem


class StubRecognizer:
    def __init__(self, items=None, error=None) -> None:
        self.items = items or []
        self.error = error
        self.calls = 0

    async def recognize(self, image, mime_type, user_text):
        del image, mime_type, user_text
        self.calls += 1
        if self.error is not None:
            raise self.error
        return list(self.items)


@pytest.fixture
async def uow():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield SqlAlchemyUnitOfWork(session)
    await engine.dispose()


def calculator() -> NutritionCalculator:
    return NutritionCalculator(FoodCatalog())


async def make_user(uow, telegram_id: int):
    user = await uow.users.get_or_create(telegram_id, "Europe/Moscow")
    await uow.commit()
    return user


@pytest.mark.asyncio
async def test_photo_draft_edit_does_not_call_recognizer_again(uow):
    user = await make_user(uow, 1)
    eaten_at = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)
    stub = StubRecognizer(items=[RecognizedItem("Cooked rice", Decimal("100"), "порция")])
    created = await CreateDraftFromPhoto(uow, stub, calculator(), 1024).start(
        user_id=user.id,
        photo_file_id="file-1",
        eaten_at=eaten_at,
    )
    ready = await CreateDraftFromPhoto(uow, stub, calculator(), 1024).complete(
        entry_id=created.id,
        user_id=user.id,
        image=b"image",
        mime_type="image/jpeg",
        user_text=None,
    )
    assert isinstance(ready, DraftReady)
    assert ready.entry.status == EntryStatus.DRAFT
    assert ready.entry.totals.calories == Decimal("130.0")
    assert stub.calls == 1

    updated = await EditFoodItemWeight(uow).execute(
        user_id=user.id,
        item_id=ready.entry.items[0].id,
        weight_g=Decimal("50"),
    )
    assert isinstance(updated, WeightUpdated)
    assert updated.entry.items[0].weight_g == Decimal("50.0")
    assert updated.entry.totals.calories == Decimal("65.0")
    assert stub.calls == 1

    saved = await ConfirmEntry(uow).execute(entry_id=created.id, user_id=user.id)
    assert isinstance(saved, Confirmed)
    assert saved.entry.status == EntryStatus.CONFIRMED
    assert saved.entry.totals.calories == Decimal("65.0")
    assert saved.entry.confirmed_at is not None


@pytest.mark.asyncio
async def test_repeat_confirm_does_not_duplicate(uow):
    user = await make_user(uow, 2)
    stub = StubRecognizer(items=[RecognizedItem("Яйцо", Decimal("60"), None)])
    draft = await CreateDraftFromPhoto(uow, stub, calculator(), 1024).start(
        user_id=user.id,
        photo_file_id="file",
        eaten_at=datetime(2026, 11, 19, 8, 0, tzinfo=timezone.utc),
    )
    await CreateDraftFromPhoto(uow, stub, calculator(), 1024).complete(
        entry_id=draft.id,
        user_id=user.id,
        image=b"image",
        mime_type="image/jpeg",
        user_text=None,
    )
    first = await ConfirmEntry(uow).execute(entry_id=draft.id, user_id=user.id)
    second = await ConfirmEntry(uow).execute(entry_id=draft.id, user_id=user.id)
    assert isinstance(first, Confirmed)
    assert isinstance(second, AlreadyProcessed)
    assert second.status == EntryStatus.CONFIRMED
    reloaded = await uow.entries.get(draft.id, user.id)
    assert reloaded is not None
    assert reloaded.status == EntryStatus.CONFIRMED
    assert reloaded.confirmed_at == first.entry.confirmed_at
    assert len(reloaded.items) == 1
    count = (await uow.session.execute(select(func.count()).select_from(FoodEntryORM))).scalar_one()
    assert count == 1


@pytest.mark.asyncio
async def test_cancel_and_empty_draft_are_not_confirmed(uow):
    user = await make_user(uow, 3)
    empty = await CreateDraftFromPhoto(uow, StubRecognizer(), calculator(), 1024).start(
        user_id=user.id,
        photo_file_id="file",
        eaten_at=datetime(2026, 11, 19, 9, 0, tzinfo=timezone.utc),
    )
    denied = await ConfirmEntry(uow).execute(entry_id=empty.id, user_id=user.id)
    assert isinstance(denied, EmptyDraft)
    assert (await uow.entries.get(empty.id, user.id)).status == EntryStatus.DRAFT

    cancelled = await CancelDraft(uow).execute(entry_id=empty.id, user_id=user.id)
    assert isinstance(cancelled, Cancelled)
    again = await ConfirmEntry(uow).execute(entry_id=empty.id, user_id=user.id)
    assert isinstance(again, AlreadyProcessed)
    assert again.status == EntryStatus.CANCELLED


@pytest.mark.asyncio
async def test_failed_recognition_keeps_draft_and_previous_items(uow):
    user = await make_user(uow, 4)
    stub = StubRecognizer(items=[RecognizedItem("Рис", Decimal("100"), None)])
    draft = await CreateDraftFromPhoto(uow, stub, calculator(), 1024).start(
        user_id=user.id,
        photo_file_id="file",
        eaten_at=datetime(2026, 11, 19, 10, 0, tzinfo=timezone.utc),
    )
    failed = await CreateDraftFromPhoto(uow, StubRecognizer(error=RecognitionTimeout()), calculator(), 1024).complete(
        entry_id=draft.id,
        user_id=user.id,
        image=b"image",
        mime_type="image/jpeg",
        user_text=None,
    )
    assert isinstance(failed, DraftFailed)
    assert failed.code == "timeout"
    assert failed.entry.status == EntryStatus.DRAFT
    assert failed.entry.items == []

    ready = await RetryRecognition(uow, stub, calculator(), 1024).execute(
        entry_id=draft.id,
        user_id=user.id,
        image=b"image",
        mime_type="image/jpeg",
        user_text=None,
    )
    assert isinstance(ready, DraftReady)
    stub.error = RecognitionTimeout()
    retried = await RetryRecognition(uow, stub, calculator(), 1024).execute(
        entry_id=draft.id,
        user_id=user.id,
        image=b"image",
        mime_type="image/jpeg",
        user_text=None,
    )
    assert isinstance(retried, DraftFailed)
    assert retried.entry.items[0].name == "Рис"
    assert retried.entry.status == EntryStatus.DRAFT


@pytest.mark.asyncio
async def test_other_user_cannot_read_or_change_entry(uow):
    owner = await make_user(uow, 5)
    stranger = await make_user(uow, 6)
    stub = StubRecognizer(items=[RecognizedItem("Яблоко", Decimal("180"), None)])
    draft = await CreateDraftFromPhoto(uow, stub, calculator(), 1024).start(
        user_id=owner.id,
        photo_file_id="file",
        eaten_at=datetime(2026, 11, 19, 11, 0, tzinfo=timezone.utc),
    )
    ready = await CreateDraftFromPhoto(uow, stub, calculator(), 1024).complete(
        entry_id=draft.id,
        user_id=owner.id,
        image=b"image",
        mime_type="image/jpeg",
        user_text=None,
    )
    assert isinstance(ready, DraftReady)
    item_id = ready.entry.items[0].id
    assert await uow.entries.get(draft.id, stranger.id) is None
    hidden = await EditFoodItemWeight(uow).execute(user_id=stranger.id, item_id=item_id, weight_g=Decimal("20"))
    removed = await RemoveFoodItem(uow).execute(user_id=stranger.id, item_id=item_id)
    confirmed = await ConfirmEntry(uow).execute(entry_id=draft.id, user_id=stranger.id)
    assert isinstance(hidden, NotFound)
    assert isinstance(removed, NotFound)
    assert isinstance(confirmed, NotFound)
    reloaded = await uow.entries.get(draft.id, owner.id)
    assert reloaded is not None
    assert reloaded.status == EntryStatus.DRAFT
    assert reloaded.items[0].weight_g == Decimal("180.0")


@pytest.mark.asyncio
async def test_remove_item(uow):
    user = await make_user(uow, 7)
    stub = StubRecognizer(
        items=[
            RecognizedItem("Яблоко", Decimal("100"), None),
            RecognizedItem("Вода", Decimal("200"), None),
        ]
    )
    draft = await CreateDraftFromPhoto(uow, stub, calculator(), 1024).start(
        user_id=user.id,
        photo_file_id="file",
        eaten_at=datetime(2026, 11, 19, 11, 30, tzinfo=timezone.utc),
    )
    ready = await CreateDraftFromPhoto(uow, stub, calculator(), 1024).complete(
        entry_id=draft.id,
        user_id=user.id,
        image=b"image",
        mime_type="image/jpeg",
        user_text=None,
    )
    assert isinstance(ready, DraftReady)
    removed = await RemoveFoodItem(uow).execute(user_id=user.id, item_id=ready.entry.items[0].id)
    assert isinstance(removed, ItemRemoved)
    assert [item.name for item in removed.entry.items] == ["Вода"]
    assert removed.entry.totals.calories == Decimal("0.0")


@pytest.mark.asyncio
async def test_diary_uses_user_local_day_and_only_confirmed(uow):
    user = await make_user(uow, 8)
    other = await make_user(uow, 9)
    start, end = local_day_bounds(date(2026, 11, 19), "Europe/Moscow")
    assert start == datetime(2026, 11, 18, 21, 0, tzinfo=timezone.utc)
    assert end == datetime(2026, 11, 19, 21, 0, tzinfo=timezone.utc)

    async def add_confirmed(owner, eaten_at, name):
        stub = StubRecognizer(items=[RecognizedItem(name, Decimal("100"), None)])
        draft = await CreateDraftFromPhoto(uow, stub, calculator(), 1024).start(
            user_id=owner.id,
            photo_file_id="file",
            eaten_at=eaten_at,
        )
        await CreateDraftFromPhoto(uow, stub, calculator(), 1024).complete(
            entry_id=draft.id,
            user_id=owner.id,
            image=b"image",
            mime_type="image/jpeg",
            user_text=None,
        )
        result = await ConfirmEntry(uow).execute(entry_id=draft.id, user_id=owner.id)
        assert isinstance(result, Confirmed)
        return draft.id

    before = datetime(2026, 11, 18, 20, 59, tzinfo=timezone.utc)
    at_start = datetime(2026, 11, 18, 21, 0, tzinfo=timezone.utc)
    midday = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)
    at_end = datetime(2026, 11, 19, 21, 0, tzinfo=timezone.utc)
    await add_confirmed(user, before, "Гречка")
    early_id = await add_confirmed(user, at_start, "Овсянка")
    late_id = await add_confirmed(user, midday, "Яблоко")
    await add_confirmed(user, at_end, "Чай")
    await add_confirmed(other, midday, "Пицца")

    draft = await CreateDraftFromPhoto(uow, StubRecognizer(), calculator(), 1024).start(
        user_id=user.id,
        photo_file_id="draft",
        eaten_at=midday,
    )
    await CancelDraft(uow).execute(entry_id=draft.id, user_id=user.id)
    await CreateDraftFromPhoto(uow, StubRecognizer(), calculator(), 1024).start(
        user_id=user.id,
        photo_file_id="still-draft",
        eaten_at=midday,
    )

    diary = await GetDailyDiary(uow).execute(user=user, on_date=date(2026, 11, 19))
    assert [entry.id for entry in diary.entries] == [early_id, late_id]
    assert diary.entries[0].eaten_at <= diary.entries[1].eaten_at
    assert diary.totals.calories == diary.entries[0].totals.calories + diary.entries[1].totals.calories


def test_day_bounds_do_not_depend_on_a_hardcoded_server_zone():
    start, end = local_day_bounds(date(2026, 11, 19), "Europe/Moscow")
    assert start.tzinfo == timezone.utc
    assert end - start == __import__("datetime").timedelta(days=1)
