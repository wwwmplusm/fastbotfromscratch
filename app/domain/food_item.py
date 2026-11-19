from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.domain.nutrition import Nutrition
from app.domain.states import NutritionSource


@dataclass
class FoodItem:
    id: UUID
    entry_id: UUID
    position: int
    name: str
    weight_g: Decimal
    nutrition: Nutrition
    per_100g: Nutrition
    nutrition_source: NutritionSource
    recognition_note: str | None = None
