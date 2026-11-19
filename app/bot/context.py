from dataclasses import dataclass

from app.config import Settings
from app.services.nutrition_calculator import NutritionCalculator
from app.services.recognition import FoodRecognizer


@dataclass
class AppContext:
    settings: Settings
    recognizer: FoodRecognizer
    calculator: NutritionCalculator
