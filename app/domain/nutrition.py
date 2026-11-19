from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

QUANTUM = Decimal("0.1")


def quantize_amount(value: object) -> Decimal:
    return Decimal(str(value)).quantize(QUANTUM, rounding=ROUND_HALF_UP)


class Nutrition:
    __slots__ = ("calories", "protein", "fat", "carbohydrates")

    def __init__(
        self,
        calories: Decimal,
        protein: Decimal,
        fat: Decimal,
        carbohydrates: Decimal,
    ) -> None:
        self.calories = calories
        self.protein = protein
        self.fat = fat
        self.carbohydrates = carbohydrates

    @classmethod
    def of(cls, calories: str, protein: str, fat: str, carbohydrates: str) -> "Nutrition":
        return cls(Decimal(calories), Decimal(protein), Decimal(fat), Decimal(carbohydrates))

    @classmethod
    def zero(cls) -> "Nutrition":
        return cls(Decimal("0.0"), Decimal("0.0"), Decimal("0.0"), Decimal("0.0"))

    def for_weight(self, weight_g: Decimal) -> "Nutrition":
        factor = weight_g / Decimal(100)
        return Nutrition(
            quantize_amount(self.calories * factor),
            quantize_amount(self.protein * factor),
            quantize_amount(self.fat * factor),
            quantize_amount(self.carbohydrates * factor),
        )

    @staticmethod
    def total(items: Iterable["Nutrition"]) -> "Nutrition":
        calories = protein = fat = carbohydrates = Decimal(0)
        for item in items:
            calories += item.calories
            protein += item.protein
            fat += item.fat
            carbohydrates += item.carbohydrates
        return Nutrition(
            quantize_amount(calories),
            quantize_amount(protein),
            quantize_amount(fat),
            quantize_amount(carbohydrates),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Nutrition):
            return NotImplemented
        return (
            self.calories == other.calories
            and self.protein == other.protein
            and self.fat == other.fat
            and self.carbohydrates == other.carbohydrates
        )

    def __repr__(self) -> str:
        return (
            f"Nutrition(calories={self.calories}, protein={self.protein}, "
            f"fat={self.fat}, carbohydrates={self.carbohydrates})"
        )
