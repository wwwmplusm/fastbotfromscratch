from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def resolve_zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("UTC")


def local_day_bounds(day: date, timezone_name: str) -> tuple[datetime, datetime]:
    tz = resolve_zone(timezone_name)
    start = datetime.combine(day, time.min, tzinfo=tz)
    end = start + timedelta(days=1)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def today_in(timezone_name: str, now: datetime | None = None) -> date:
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(resolve_zone(timezone_name)).date()
