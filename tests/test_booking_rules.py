from datetime import date, datetime

import pytest

from app.domain.booking_rules import (
    MAX_JOBS_PER_SLOT,
    earliest_service_date,
    is_service_date_allowed,
    now_kolkata,
    slot_has_capacity,
    slot_window,
)


def test_earliest_date_skips_today_and_tomorrow():
    # 4 Sep 2026 10:00 IST → 48h later is 6 Sep
    at = datetime(2026, 9, 4, 10, 0, tzinfo=__import__("zoneinfo").ZoneInfo("Asia/Kolkata"))
    assert earliest_service_date(at) == date(2026, 9, 6)
    assert is_service_date_allowed(date(2026, 9, 6), at)
    assert not is_service_date_allowed(date(2026, 9, 4), at)
    assert not is_service_date_allowed(date(2026, 9, 5), at)


def test_late_evening_still_adds_full_48_hours():
    at = datetime(2026, 9, 4, 23, 0, tzinfo=__import__("zoneinfo").ZoneInfo("Asia/Kolkata"))
    assert earliest_service_date(at) == date(2026, 9, 6)


def test_slot_windows():
    assert slot_window("morning")[0].hour == 9
    assert slot_window("evening")[1].hour == 18
    with pytest.raises(ValueError):
        slot_window("night")


def test_slot_capacity_five():
    for n in range(5):
        assert slot_has_capacity(n)
    assert not slot_has_capacity(MAX_JOBS_PER_SLOT)
    assert not slot_has_capacity(6)
    with pytest.raises(ValueError, match="job_count"):
        slot_has_capacity(-1)


def test_now_kolkata_branches():
    from zoneinfo import ZoneInfo

    assert now_kolkata().tzinfo is not None
    naive = datetime(2026, 9, 4, 10, 0)
    assert now_kolkata(naive).tzinfo == ZoneInfo("Asia/Kolkata")
    utc = datetime(2026, 9, 4, 10, 0, tzinfo=__import__("datetime").timezone.utc)
    assert now_kolkata(utc).hour == 15  # +5:30
    assert earliest_service_date(naive) == date(2026, 9, 6)
