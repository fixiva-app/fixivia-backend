from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

KOLKATA = ZoneInfo("Asia/Kolkata")
LEAD_HOURS = 48
SLOTS = ("morning", "evening")
MAX_JOBS_PER_SLOT = 5


def now_kolkata(at: datetime | None = None) -> datetime:
    if at is None:
        return datetime.now(KOLKATA)
    if at.tzinfo is None:
        return at.replace(tzinfo=KOLKATA)
    return at.astimezone(KOLKATA)


def earliest_service_date(at: datetime | None = None) -> date:
    """Earliest bookable calendar date: now + 48h in Asia/Kolkata.

    Example: 4 Sep any time → 6 Sep onward (not 4 or 5).
    """
    moment = now_kolkata(at)
    return (moment + timedelta(hours=LEAD_HOURS)).date()


def is_service_date_allowed(service_date: date, at: datetime | None = None) -> bool:
    return service_date >= earliest_service_date(at)


def slot_window(slot: str) -> tuple[time, time]:
    if slot == "morning":
        return time(9, 0), time(13, 0)
    if slot == "evening":
        return time(13, 0), time(18, 0)
    raise ValueError(f"unknown slot: {slot}")


def slot_has_capacity(job_count: int) -> bool:
    """Eligible for pool when 0–4 jobs already in that date+slot."""
    if job_count < 0:
        raise ValueError("job_count must be >= 0")
    return job_count < MAX_JOBS_PER_SLOT
