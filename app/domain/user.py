from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class User:
    id: UUID
    telegram_id: int
    timezone: str
    created_at: datetime
