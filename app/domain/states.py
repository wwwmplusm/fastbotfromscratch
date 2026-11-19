from enum import StrEnum


class EntryStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class EntrySource(StrEnum):
    PHOTO = "photo"


class NutritionSource(StrEnum):
    CATALOG = "catalog"
    ESTIMATED = "estimated"
    MANUAL = "manual"
