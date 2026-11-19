import re
from decimal import Decimal

from app.domain.errors import InvalidWeight
from app.domain.nutrition import quantize_amount

MIN_WEIGHT_G = Decimal("1")
MAX_WEIGHT_G = Decimal("5000")

_WEIGHT_TEXT = re.compile(
    r"^\s*(\d+(?:[.,]\d+)?)\s*(?:г|гр|грамм(?:а|ов)?|g|grams?)?\s*$",
    re.IGNORECASE,
)


def parse_weight_text(text: str) -> Decimal | None:
    match = _WEIGHT_TEXT.match(text.strip())
    if match is None:
        return None
    return Decimal(match.group(1).replace(",", "."))


def validate_weight(value: Decimal) -> Decimal:
    if not value.is_finite() or value < MIN_WEIGHT_G or value > MAX_WEIGHT_G:
        raise InvalidWeight(value)
    return quantize_amount(value)
