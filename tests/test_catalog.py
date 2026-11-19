from decimal import Decimal

from app.domain.states import NutritionSource
from app.services.food_catalog import FoodCatalog
from app.services.nutrition_calculator import NutritionCalculator


def test_catalog_matches_english_and_russian_names():
    catalog = FoodCatalog()
    rice = catalog.lookup("Cooked rice")
    chicken = catalog.lookup("Chicken breast")
    fried = catalog.lookup("жареная курица")
    unknown = catalog.lookup("зырькф неизвестное блюдо")
    assert rice.source == NutritionSource.CATALOG
    assert chicken.source == NutritionSource.CATALOG
    assert fried.source == NutritionSource.CATALOG
    assert fried.per_100g.calories == Decimal("240")
    assert unknown.source == NutritionSource.ESTIMATED
    assert unknown.per_100g.calories == Decimal("150")


def test_calculator_scales_catalog_food_and_keeps_recognized_name():
    calculator = NutritionCalculator(FoodCatalog())
    item = calculator.build_item(
        __import__("uuid").uuid4(),
        0,
        "Cooked rice",
        Decimal("150"),
        "Estimated from visible portion",
    )
    assert item.name == "Cooked rice"
    assert item.nutrition.calories == Decimal("195.0")
    assert item.nutrition_source == NutritionSource.CATALOG
    assert item.per_100g.calories == Decimal("130")


def test_unknown_food_is_marked_estimated():
    calculator = NutritionCalculator(FoodCatalog())
    item = calculator.build_item(__import__("uuid").uuid4(), 0, "Зырькф", Decimal("100"), None)
    assert item.name == "Зырькф"
    assert item.nutrition_source == NutritionSource.ESTIMATED
    assert item.nutrition.calories == Decimal("150.0")
