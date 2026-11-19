from datetime import date

from app.application.ports import UnitOfWork
from app.application.results import DailyDiary
from app.domain.time import local_day_bounds, today_in
from app.domain.user import User


class GetDailyDiary:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def execute(self, *, user: User, on_date: date | None = None) -> DailyDiary:
        day = on_date or today_in(user.timezone)
        start, end = local_day_bounds(day, user.timezone)
        entries = await self.uow.entries.list_confirmed(user.id, start, end)
        await self.uow.commit()
        return DailyDiary(day=day, timezone=user.timezone, entries=entries)
