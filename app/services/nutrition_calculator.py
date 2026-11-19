from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.food_item import FoodItem
from app.domain.weight import validate_weight
from app.services.food_catalog import FoodCatalog


def clean_food_name(name: str) -> str:
    return " ".join(name.split())[:200]


class NutritionCalculator:
    def __init__(self, catalog: FoodCatalog) -> None:
        self.catalog = catalog

    def build_item(
        self,
        entry_id: UUID,
        position: int,
        name: str,
        weight_g: Decimal,
        recognition_note: str | None,
    ) -> FoodItem:
        weight = validate_weight(weight_g)
        hit = self.catalog.lookup(name)
        return FoodItem(
            id=uuid4(),
            entry_id=entry_id,
            position=position,
            name=clean_food_name(name),
            weight_g=weight,
            nutrition=hit.per_100g.for_weight(weight),
            per_100g=hit.per_100g,
            nutrition_source=hit.source,
            recognition_note=recognition_note,
        )
