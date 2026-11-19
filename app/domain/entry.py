from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.errors import EmptyEntry, InvalidTransition, ItemNotFound
from app.domain.food_item import FoodItem
from app.domain.nutrition import Nutrition
from app.domain.states import EntrySource, EntryStatus
from app.domain.weight import validate_weight


@dataclass
class FoodEntry:
    id: UUID
    user_id: UUID
    status: EntryStatus
    source: EntrySource
    photo_file_id: str | None
    eaten_at: datetime
    created_at: datetime
    confirmed_at: datetime | None
    items: list[FoodItem] = field(default_factory=list)
    totals: Nutrition = field(default_factory=Nutrition.zero)
    chat_id: int | None = None
    message_id: int | None = None
    recognition_error: str | None = None

    @classmethod
    def create_draft(
        cls,
        *,
        user_id: UUID,
        photo_file_id: str,
        eaten_at: datetime,
    ) -> "FoodEntry":
        return cls(
            id=uuid4(),
            user_id=user_id,
            status=EntryStatus.DRAFT,
            source=EntrySource.PHOTO,
            photo_file_id=photo_file_id,
            eaten_at=eaten_at,
            created_at=eaten_at,
            confirmed_at=None,
        )

    def replace_items(self, items: list[FoodItem]) -> None:
        self._ensure_draft()
        self.items = list(items)
        for index, item in enumerate(self.items):
            item.position = index
            item.entry_id = self.id
        self.recalculate_totals()

    def change_weight(self, item_id: UUID, weight_g: Decimal) -> None:
        self._ensure_draft()
        item = self._get_item(item_id)
        item.weight_g = validate_weight(weight_g)
        item.nutrition = item.per_100g.for_weight(item.weight_g)
        self.recalculate_totals()

    def remove_item(self, item_id: UUID) -> None:
        self._ensure_draft()
        if not any(item.id == item_id for item in self.items):
            raise ItemNotFound(str(item_id))
        self.items = [item for item in self.items if item.id != item_id]
        for index, item in enumerate(self.items):
            item.position = index
        self.recalculate_totals()

    def confirm(self, at: datetime) -> None:
        self._ensure_draft()
        if not self.items:
            raise EmptyEntry("draft has no items")
        self.recalculate_totals()
        self.status = EntryStatus.CONFIRMED
        self.confirmed_at = at

    def cancel(self) -> None:
        self._ensure_draft()
        self.status = EntryStatus.CANCELLED

    def recalculate_totals(self) -> None:
        self.totals = Nutrition.total(item.nutrition for item in self.items)

    def _ensure_draft(self) -> None:
        if self.status != EntryStatus.DRAFT:
            raise InvalidTransition(f"entry is {self.status.value}")

    def _get_item(self, item_id: UUID) -> FoodItem:
        for item in self.items:
            if item.id == item_id:
                return item
        raise ItemNotFound(str(item_id))
