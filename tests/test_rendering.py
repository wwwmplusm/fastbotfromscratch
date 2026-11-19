from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.bot.callbacks.entry_callbacks import EntryCB, ItemCB
from app.bot.keyboards.draft_keyboard import draft_keyboard
from app.bot.rendering import ESTIMATE_FOOTER, render_cancelled, render_diary, render_draft
from app.application.results import DailyDiary
from app.domain.entry import FoodEntry
from app.domain.food_item import FoodItem
from app.domain.nutrition import Nutrition
from app.domain.states import NutritionSource


def _entry() -> FoodEntry:
    entry = FoodEntry.create_draft(
        user_id=uuid4(),
        photo_file_id="file",
        eaten_at=datetime(2026, 11, 19, 15, 4, tzinfo=timezone.utc),
    )
    per_100 = Nutrition.of("100", "10", "5", "12")
    entry.replace_items(
        [
            FoodItem(
                id=uuid4(),
                entry_id=entry.id,
                position=0,
                name="Рис",
                weight_g=Decimal("100"),
                nutrition=per_100.for_weight(Decimal("100")),
                per_100g=per_100,
                nutrition_source=NutritionSource.CATALOG,
            )
        ]
    )
    return entry


def test_draft_card_says_the_result_is_an_estimate():
    text = render_draft(_entry(), "Europe/Moscow")
    assert "Рис" in text
    assert ESTIMATE_FOOTER in text
    assert "Сохранить" not in text


def test_cancelled_text_does_not_claim_a_diary_entry():
    assert "ничего не записано" in render_cancelled()


def test_callback_payload_fits_telegram_limit():
    entry = _entry()
    for button_row in draft_keyboard(entry).inline_keyboard:
        for button in button_row:
            assert len(button.callback_data.encode()) <= 64
    assert len(EntryCB(a="ok", eid=str(uuid4())).pack().encode()) <= 64
    assert len(ItemCB(a="w", iid=str(uuid4())).pack().encode()) <= 64


def test_diary_lists_only_what_it_was_given_and_keeps_the_estimate_line():
    entry = _entry()
    entry.confirm(datetime(2026, 11, 19, 15, 5, tzinfo=timezone.utc))
    text = render_diary(DailyDiary(day=entry.eaten_at.date(), timezone="Europe/Moscow", entries=[entry]))
    assert "Рис 100 г" in text
    assert "Итого за день" in text
    assert ESTIMATE_FOOTER in text
