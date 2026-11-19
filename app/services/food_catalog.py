import re
from dataclasses import dataclass

from app.domain.nutrition import Nutrition
from app.domain.states import NutritionSource

_NAME_CLEAN = re.compile(r"[^0-9a-zа-я]+")


def normalize_name(value: str) -> str:
    folded = value.lower().replace("ё", "е")
    cleaned = _NAME_CLEAN.sub(" ", folded)
    return " ".join(cleaned.split())


@dataclass(frozen=True)
class FoodRecord:
    name: str
    aliases: tuple[str, ...]
    per_100g: Nutrition


@dataclass(frozen=True)
class CatalogHit:
    per_100g: Nutrition
    source: NutritionSource


def _n(calories: str, protein: str, fat: str, carbohydrates: str) -> Nutrition:
    return Nutrition.of(calories, protein, fat, carbohydrates)


GENERIC_PER_100G = _n("150", "8", "6", "15")

# Values are approximate per 100 g of the edible portion. The product presents them as estimates.
DEFAULT_RECORDS: tuple[FoodRecord, ...] = (
    FoodRecord("Рис отварной", ("рис", "cooked rice", "white rice", "rice"), _n("130", "2.7", "0.3", "28")),
    FoodRecord("Гречка отварная", ("гречка", "buckwheat"), _n("110", "4.2", "1.1", "21")),
    FoodRecord("Овсянка", ("овсяная каша", "овсянка", "oatmeal"), _n("88", "3", "1.7", "15")),
    FoodRecord("Макароны отварные", ("макароны", "паста", "pasta"), _n("135", "5", "1.1", "25")),
    FoodRecord("Картофель варёный", ("картофель", "картошка", "boiled potato", "potato"), _n("82", "2", "0.1", "17")),
    FoodRecord(
        "Картофель жареный",
        ("жареная картошка", "жареный картофель", "fried potato"),
        _n("192", "2.8", "9.5", "24"),
    ),
    FoodRecord("Хлеб", ("хлеб", "bread"), _n("265", "8", "3.2", "49")),
    FoodRecord("Хлеб чёрный", ("черный хлеб", "ржаной хлеб", "rye bread"), _n("200", "6.6", "1.2", "40")),
    FoodRecord("Лаваш", ("лаваш", "lavash"), _n("275", "9", "1", "56")),
    FoodRecord("Куриная грудка", ("куриная грудка", "курица", "chicken breast", "chicken"), _n("165", "31", "3.6", "0")),
    FoodRecord("Курица жареная", ("жареная курица", "fried chicken"), _n("240", "25", "14", "0")),
    FoodRecord("Индейка", ("индейка", "turkey"), _n("160", "29", "3.5", "0")),
    FoodRecord("Говядина", ("говядина", "beef"), _n("250", "26", "15", "0")),
    FoodRecord("Свинина", ("свинина", "pork"), _n("242", "27", "14", "0")),
    FoodRecord("Фарш", ("фарш", "minced meat"), _n("220", "20", "15", "0")),
    FoodRecord("Котлета", ("котлета", "cutlet"), _n("260", "18", "18", "8")),
    FoodRecord("Сосиски", ("сосиски", "сосиска", "sausage"), _n("260", "11", "23", "2")),
    FoodRecord("Лосось", ("лосось", "семга", "salmon"), _n("208", "20", "13", "0")),
    FoodRecord("Треска", ("треска", "cod"), _n("82", "18", "0.7", "0")),
    FoodRecord("Тунец", ("тунец", "tuna"), _n("132", "29", "1", "0")),
    FoodRecord("Креветки", ("креветки", "shrimp"), _n("99", "24", "0.3", "0.2")),
    FoodRecord("Яйцо", ("яйцо", "яйца", "egg"), _n("155", "13", "11", "1.1")),
    FoodRecord("Яичница", ("яичница", "fried egg"), _n("196", "14", "15", "1")),
    FoodRecord("Омлет", ("омлет", "omelette"), _n("180", "12", "14", "1.5")),
    FoodRecord("Творог", ("творог", "cottage cheese"), _n("120", "17", "5", "2")),
    FoodRecord("Йогурт", ("йогурт", "yogurt"), _n("60", "4", "2", "6")),
    FoodRecord("Молоко", ("молоко", "milk"), _n("60", "3.2", "3.2", "4.7")),
    FoodRecord("Сыр", ("сыр", "cheese"), _n("350", "25", "27", "0")),
    FoodRecord("Сметана", ("сметана", "sour cream"), _n("200", "2.5", "20", "3")),
    FoodRecord("Огурец", ("огурец", "cucumber"), _n("15", "0.7", "0.1", "3")),
    FoodRecord("Помидор", ("помидор", "томат", "tomato"), _n("18", "0.9", "0.2", "3.9")),
    FoodRecord("Салат листовой", ("салат", "lettuce"), _n("15", "1.4", "0.2", "2.9")),
    FoodRecord("Салат овощной", ("овощной салат", "vegetable salad"), _n("50", "1.2", "2.5", "6")),
    FoodRecord("Капуста", ("капуста", "cabbage"), _n("25", "1.3", "0.1", "5.8")),
    FoodRecord("Морковь", ("морковь", "carrot"), _n("41", "0.9", "0.2", "10")),
    FoodRecord("Брокколи", ("брокколи", "broccoli"), _n("34", "2.8", "0.4", "7")),
    FoodRecord("Яблоко", ("яблоко", "apple"), _n("52", "0.3", "0.2", "14")),
    FoodRecord("Банан", ("банан", "banana"), _n("89", "1.1", "0.3", "23")),
    FoodRecord("Масло растительное", ("растительное масло", "vegetable oil"), _n("884", "0", "100", "0")),
    FoodRecord("Масло сливочное", ("сливочное масло", "butter"), _n("717", "0.9", "81", "0.1")),
    FoodRecord("Борщ", ("борщ", "borscht"), _n("45", "1.8", "2", "5")),
    FoodRecord("Куриный суп", ("куриный суп", "суп", "chicken soup", "soup"), _n("40", "3", "1.5", "3")),
    FoodRecord("Плов", ("плов", "pilaf", "plov"), _n("180", "7", "7", "22")),
    FoodRecord("Пельмени", ("пельмени", "pelmeni"), _n("250", "12", "12", "24")),
    FoodRecord("Пицца", ("пицца", "pizza"), _n("266", "11", "10", "33")),
    FoodRecord("Бургер", ("бургер", "гамбургер", "burger"), _n("250", "13", "12", "22")),
    FoodRecord("Шаурма", ("шаурма", "шаверма", "shawarma"), _n("220", "12", "10", "20")),
    FoodRecord("Мёд", ("мед", "honey"), _n("304", "0.3", "0", "82")),
    FoodRecord("Сахар", ("сахар", "sugar"), _n("387", "0", "0", "100")),
    FoodRecord("Кофе чёрный", ("кофе", "black coffee", "coffee"), _n("2", "0.1", "0", "0")),
    FoodRecord("Чай", ("чай", "tea"), _n("1", "0", "0", "0.3")),
    FoodRecord("Сок", ("сок", "juice"), _n("45", "0.5", "0.1", "11")),
    FoodRecord("Кола", ("кола", "cola", "soda"), _n("42", "0", "0", "10.6")),
    FoodRecord("Вода", ("вода", "water"), _n("0", "0", "0", "0")),
)


class FoodCatalog:
    def __init__(self, records: tuple[FoodRecord, ...] = DEFAULT_RECORDS) -> None:
        self.records = records
        self._exact: dict[str, FoodRecord] = {}
        self._aliases: list[tuple[str, FoodRecord]] = []
        for record in records:
            for alias in (record.name, *record.aliases):
                normalized = normalize_name(alias)
                if not normalized:
                    continue
                self._exact.setdefault(normalized, record)
                self._aliases.append((normalized, record))

    def lookup(self, name: str) -> CatalogHit:
        normalized = normalize_name(name)
        if not normalized:
            return self._generic()
        exact = self._exact.get(normalized)
        if exact is not None:
            return CatalogHit(exact.per_100g, NutritionSource.CATALOG)

        best_score = -1
        best: FoodRecord | None = None
        for alias, record in self._aliases:
            if len(alias) >= 8 and alias in normalized:
                score = 500 + len(alias)
                if score > best_score:
                    best_score = score
                    best = record
        for token in normalized.split():
            if len(token) < 3:
                continue
            record = self._exact.get(token)
            if record is None:
                continue
            score = len(token)
            if score > best_score:
                best_score = score
                best = record
        if best is not None:
            return CatalogHit(best.per_100g, NutritionSource.CATALOG)
        return self._generic()

    def _generic(self) -> CatalogHit:
        return CatalogHit(GENERIC_PER_100G, NutritionSource.ESTIMATED)
