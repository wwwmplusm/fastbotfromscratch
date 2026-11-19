import json
import logging
import math
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.domain.weight import parse_weight_text, validate_weight
from app.domain.errors import InvalidWeight

logger = logging.getLogger(__name__)

MAX_ITEMS = 12
MAX_NOTE_LENGTH = 300

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class RecognitionError(Exception):
    code = "unexpected"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.code)


class RecognitionNotConfigured(RecognitionError):
    code = "not_configured"


class RecognitionUnavailable(RecognitionError):
    code = "unavailable"


class RecognitionTimeout(RecognitionError):
    code = "timeout"


class RecognitionInvalid(RecognitionError):
    code = "invalid"


class RecognitionEmpty(RecognitionError):
    code = "empty"


@dataclass(frozen=True)
class RecognizedItem:
    name: str
    estimated_weight_g: Decimal
    recognition_note: str | None


class FoodRecognizer(Protocol):
    async def recognize(
        self,
        image: bytes,
        mime_type: str,
        user_text: str | None,
    ) -> list[RecognizedItem]: ...


class UnconfiguredRecognizer:
    async def recognize(
        self,
        image: bytes,
        mime_type: str,
        user_text: str | None,
    ) -> list[RecognizedItem]:
        del image, mime_type, user_text
        raise RecognitionNotConfigured()


def strip_json_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = _FENCE.sub("", stripped).strip()
    return stripped


def load_json_object(text: str) -> dict:
    raw = strip_json_fences(text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end <= start:
            raise RecognitionInvalid("response is not json") from None
        try:
            data = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            raise RecognitionInvalid("response is not json") from None
    if not isinstance(data, dict):
        raise RecognitionInvalid("payload is not an object")
    return data


def parse_recognition_payload(data: dict) -> list[RecognizedItem]:
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise RecognitionInvalid("items missing")
    if not items:
        raise RecognitionEmpty("no items")

    parsed: list[RecognizedItem] = []
    dropped = 0
    for raw in items:
        item = _try_parse_item(raw)
        if item is None:
            dropped += 1
            continue
        parsed.append(item)
        if len(parsed) >= MAX_ITEMS:
            break
    if dropped:
        logger.info("recognition dropped invalid items count=%s kept=%s", dropped, len(parsed))
    if not parsed:
        raise RecognitionInvalid("no valid items")
    return parsed


def _try_parse_item(raw: object) -> RecognizedItem | None:
    if not isinstance(raw, dict):
        return None
    name = raw.get("name")
    if not isinstance(name, str):
        return None
    cleaned = " ".join(name.split())
    if not cleaned:
        return None
    weight = _parse_model_weight(raw.get("estimated_weight_g"))
    if weight is None:
        return None
    note = raw.get("recognition_note")
    recognition_note: str | None
    if isinstance(note, str) and note.strip():
        recognition_note = " ".join(note.split())[:MAX_NOTE_LENGTH]
    else:
        recognition_note = None
    return RecognizedItem(cleaned[:200], weight, recognition_note)


def _parse_model_weight(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str):
        parsed = parse_weight_text(value)
        if parsed is None:
            return None
        number = parsed
    elif isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        number = Decimal(str(value))
    else:
        return None
    try:
        return validate_weight(number)
    except InvalidWeight:
        return None
