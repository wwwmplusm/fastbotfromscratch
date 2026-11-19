from dataclasses import dataclass
from datetime import date

from app.domain.entry import FoodEntry
from app.domain.nutrition import Nutrition
from app.domain.states import EntryStatus


@dataclass(frozen=True)
class NotFound:
    pass


@dataclass(frozen=True)
class NotEditable:
    status: EntryStatus


@dataclass(frozen=True)
class AlreadyProcessed:
    status: EntryStatus


@dataclass(frozen=True)
class EmptyDraft:
    entry: FoodEntry


@dataclass(frozen=True)
class DraftReady:
    entry: FoodEntry


@dataclass(frozen=True)
class DraftFailed:
    entry: FoodEntry
    code: str


@dataclass(frozen=True)
class Confirmed:
    entry: FoodEntry


@dataclass(frozen=True)
class Cancelled:
    entry: FoodEntry


@dataclass(frozen=True)
class WeightUpdated:
    entry: FoodEntry


@dataclass(frozen=True)
class ItemRemoved:
    entry: FoodEntry


@dataclass(frozen=True)
class InvalidItemWeight:
    pass


@dataclass(frozen=True)
class DailyDiary:
    day: date
    timezone: str
    entries: list[FoodEntry]

    @property
    def totals(self) -> Nutrition:
        return Nutrition.total(entry.totals for entry in self.entries)
