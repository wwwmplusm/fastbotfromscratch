from uuid import UUID

from app.application.fill_draft import fill_draft_from_image
from app.application.ports import UnitOfWork
from app.application.results import DraftFailed, DraftReady, NotEditable, NotFound
from app.services.nutrition_calculator import NutritionCalculator
from app.services.recognition import FoodRecognizer


class RetryRecognition:
    def __init__(
        self,
        uow: UnitOfWork,
        recognizer: FoodRecognizer,
        calculator: NutritionCalculator,
        max_bytes: int,
    ) -> None:
        self.uow = uow
        self.recognizer = recognizer
        self.calculator = calculator
        self.max_bytes = max_bytes

    async def execute(
        self,
        *,
        entry_id: UUID,
        user_id: UUID,
        image: bytes,
        mime_type: str,
        user_text: str | None,
    ) -> DraftReady | DraftFailed | NotFound | NotEditable:
        return await fill_draft_from_image(
            self.uow,
            self.recognizer,
            self.calculator,
            entry_id=entry_id,
            user_id=user_id,
            image=image,
            mime_type=mime_type,
            user_text=user_text,
            max_bytes=self.max_bytes,
        )
