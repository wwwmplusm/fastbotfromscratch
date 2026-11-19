from datetime import datetime, timezone

from app.domain.entry import FoodEntry
from app.domain.food_item import FoodItem
from app.domain.nutrition import Nutrition, quantize_amount
from app.domain.states import EntrySource, EntryStatus, NutritionSource
from app.domain.user import User
from app.infrastructure.database.models import FoodEntryItemORM, FoodEntryORM, UserORM


def aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def user_to_orm(user: User) -> UserORM:
    return UserORM(
        id=user.id,
        telegram_id=user.telegram_id,
        timezone=user.timezone,
        created_at=user.created_at,
    )


def user_to_domain(row: UserORM) -> User:
    return User(
        id=row.id,
        telegram_id=row.telegram_id,
        timezone=row.timezone,
        created_at=aware(row.created_at),
    )


def _nutrition(calories, protein, fat, carbohydrates) -> Nutrition:
    return Nutrition(
        quantize_amount(calories),
        quantize_amount(protein),
        quantize_amount(fat),
        quantize_amount(carbohydrates),
    )


def item_to_domain(row: FoodEntryItemORM) -> FoodItem:
    return FoodItem(
        id=row.id,
        entry_id=row.entry_id,
        position=row.position,
        name=row.name,
        weight_g=quantize_amount(row.weight_g),
        nutrition=_nutrition(row.calories, row.protein, row.fat, row.carbohydrates),
        per_100g=_nutrition(
            row.calories_per_100g,
            row.protein_per_100g,
            row.fat_per_100g,
            row.carbohydrates_per_100g,
        ),
        nutrition_source=NutritionSource(row.nutrition_source),
        recognition_note=row.recognition_note,
    )


def apply_item(row: FoodEntryItemORM, item: FoodItem) -> None:
    row.entry_id = item.entry_id
    row.position = item.position
    row.name = item.name
    row.weight_g = item.weight_g
    row.calories = item.nutrition.calories
    row.protein = item.nutrition.protein
    row.fat = item.nutrition.fat
    row.carbohydrates = item.nutrition.carbohydrates
    row.calories_per_100g = item.per_100g.calories
    row.protein_per_100g = item.per_100g.protein
    row.fat_per_100g = item.per_100g.fat
    row.carbohydrates_per_100g = item.per_100g.carbohydrates
    row.nutrition_source = item.nutrition_source.value
    row.recognition_note = item.recognition_note


def item_to_orm(item: FoodItem) -> FoodEntryItemORM:
    row = FoodEntryItemORM(id=item.id)
    apply_item(row, item)
    return row


def apply_entry(row: FoodEntryORM, entry: FoodEntry) -> None:
    row.status = entry.status.value
    row.source = entry.source.value
    row.photo_file_id = entry.photo_file_id
    row.eaten_at = entry.eaten_at
    row.created_at = entry.created_at
    row.confirmed_at = entry.confirmed_at
    row.calories = entry.totals.calories
    row.protein = entry.totals.protein
    row.fat = entry.totals.fat
    row.carbohydrates = entry.totals.carbohydrates
    row.chat_id = entry.chat_id
    row.message_id = entry.message_id
    row.recognition_error = entry.recognition_error

    existing = {item.id: item for item in list(row.items)}
    incoming = {item.id for item in entry.items}
    for item_id, item_row in existing.items():
        if item_id not in incoming:
            row.items.remove(item_row)
    for item in entry.items:
        current = existing.get(item.id)
        if current is None:
            row.items.append(item_to_orm(item))
        else:
            apply_item(current, item)


def entry_to_orm(entry: FoodEntry) -> FoodEntryORM:
    row = FoodEntryORM(
        id=entry.id,
        user_id=entry.user_id,
        status=entry.status.value,
        source=entry.source.value,
        photo_file_id=entry.photo_file_id,
        eaten_at=entry.eaten_at,
        created_at=entry.created_at,
        confirmed_at=entry.confirmed_at,
        calories=entry.totals.calories,
        protein=entry.totals.protein,
        fat=entry.totals.fat,
        carbohydrates=entry.totals.carbohydrates,
        chat_id=entry.chat_id,
        message_id=entry.message_id,
        recognition_error=entry.recognition_error,
    )
    row.items = [item_to_orm(item) for item in entry.items]
    return row


def entry_to_domain(row: FoodEntryORM) -> FoodEntry:
    items = [item_to_domain(item) for item in sorted(row.items, key=lambda item: item.position)]
    return FoodEntry(
        id=row.id,
        user_id=row.user_id,
        status=EntryStatus(row.status),
        source=EntrySource(row.source),
        photo_file_id=row.photo_file_id,
        eaten_at=aware(row.eaten_at),
        created_at=aware(row.created_at),
        confirmed_at=aware(row.confirmed_at) if row.confirmed_at is not None else None,
        items=items,
        totals=_nutrition(row.calories, row.protein, row.fat, row.carbohydrates),
        chat_id=row.chat_id,
        message_id=row.message_id,
        recognition_error=row.recognition_error,
    )
