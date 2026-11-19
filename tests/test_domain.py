from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.entry import FoodEntry
from app.domain.errors import EmptyEntry, InvalidTransition, InvalidWeight
from app.domain.food_item import FoodItem
from app.domain.nutrition import Nutrition
from app.domain.states import EntryStatus, NutritionSource
from app.domain.weight import parse_weight_text, validate_weight


def _item(entry_id, per_100: Nutrition, weight: str = "100") -> FoodItem:
    weight_g = Decimal(weight)
    return FoodItem(
        id=uuid4(),
        entry_id=entry_id,
        position=0,
        name="Тест",
        weight_g=weight_g,
        nutrition=per_100.for_weight(weight_g),
        per_100g=per_100,
        nutrition_source=NutritionSource.MANUAL,
    )


def test_weight_scales_nutrients_from_per_100g():
    per_100 = Nutrition.of("130", "2.7", "0.3", "28")
    scaled = per_100.for_weight(Decimal("150"))
    assert scaled.calories == Decimal("195.0")
    assert scaled.protein == Decimal("4.1")
    assert scaled.carbohydrates == Decimal("42.0")


def test_totals_sum_items():
    first = Nutrition.of("10.0", "1.0", "2.0", "3.0")
    second = Nutrition.of("0.5", "0.5", "0.5", "0.5")
    assert Nutrition.total([first, second]) == Nutrition.of("10.5", "1.5", "2.5", "3.5")


def test_weight_text_and_range():
    assert parse_weight_text("150,5 г") == Decimal("150.5")
    assert parse_weight_text("200гр") == Decimal("200")
    assert parse_weight_text("много") is None
    assert validate_weight(Decimal("150.55")) == Decimal("150.6")
    with pytest.raises(InvalidWeight):
        validate_weight(Decimal("0"))
    with pytest.raises(InvalidWeight):
        validate_weight(Decimal("5000.1"))


def test_change_weight_uses_stored_per_100g_and_updates_total():
    entry = FoodEntry.create_draft(user_id=uuid4(), photo_file_id="f", eaten_at=datetime.now(timezone.utc))
    per_100 = Nutrition.of("80", "1", "2", "3")
    entry.replace_items([_item(entry.id, per_100)])
    entry.change_weight(entry.items[0].id, Decimal("250"))
    assert entry.items[0].weight_g == Decimal("250.0")
    assert entry.items[0].nutrition.calories == Decimal("200.0")
    assert entry.totals.calories == Decimal("200.0")


def test_confirm_and_cancel_transitions():
    entry = FoodEntry.create_draft(user_id=uuid4(), photo_file_id="f", eaten_at=datetime.now(timezone.utc))
    with pytest.raises(EmptyEntry):
        entry.confirm(datetime.now(timezone.utc))
    entry.replace_items([_item(entry.id, Nutrition.of("10", "1", "1", "1"))])
    entry.confirm(datetime.now(timezone.utc))
    assert entry.status == EntryStatus.CONFIRMED
    with pytest.raises(InvalidTransition):
        entry.cancel()
    with pytest.raises(InvalidTransition):
        entry.change_weight(entry.items[0].id, Decimal("50"))


def test_remove_item_recalculates():
    entry = FoodEntry.create_draft(user_id=uuid4(), photo_file_id="f", eaten_at=datetime.now(timezone.utc))
    first = _item(entry.id, Nutrition.of("10", "1", "1", "1"))
    second = _item(entry.id, Nutrition.of("5", "1", "1", "1"))
    entry.replace_items([first, second])
    entry.remove_item(first.id)
    assert len(entry.items) == 1
    assert entry.items[0].position == 0
    assert entry.totals.calories == Decimal("5.0")
