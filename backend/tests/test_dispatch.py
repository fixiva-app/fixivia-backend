from datetime import datetime, timedelta, timezone

from app.domain.dispatch import (
    ALREADY_TAKEN,
    ASSIGNED,
    TechnicianEligibility,
    accept_lock,
    force_assign_ready,
    is_eligible,
    next_pool_excludes,
)


def _tech(**kwargs) -> TechnicianEligibility:
    base = dict(
        approved=True,
        same_partner=True,
        offers_category=True,
        works_pincode=True,
        excluded=False,
        jobs_in_slot=0,
    )
    base.update(kwargs)
    return TechnicianEligibility(**base)


def test_eligible_happy_path():
    assert is_eligible(_tech())
    assert is_eligible(_tech(jobs_in_slot=4))
    assert not is_eligible(_tech(jobs_in_slot=5))
    assert not is_eligible(_tech(approved=False))
    assert not is_eligible(_tech(same_partner=False))
    assert not is_eligible(_tech(offers_category=False))
    assert not is_eligible(_tech(excluded=True))
    assert not is_eligible(_tech(works_pincode=False))


def test_first_accept_wins():
    assert accept_lock("open") == ASSIGNED
    assert accept_lock("assigned") == ALREADY_TAKEN
    assert accept_lock("in_progress") == ALREADY_TAKEN


def test_decliners_and_droppers_excluded():
    assert next_pool_excludes("declined")
    assert next_pool_excludes("dropped")
    assert not next_pool_excludes("timeout")


def test_force_assign_gate():
    now = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
    fresh = now - timedelta(minutes=10)
    stale = now - timedelta(hours=3, minutes=1)
    boundary = now - timedelta(hours=3)
    # strict first-accept until a full 3h window passes
    assert not force_assign_ready("open", fresh, 1, now)
    assert force_assign_ready("open", stale, 1, now)
    assert force_assign_ready("open", boundary, 1, now)
    # or two pools ran with no accept
    assert force_assign_ready("open", fresh, 2, now)
    assert force_assign_ready("open", None, 2, now)
    # unknown creation time and too few pools: not ready
    assert not force_assign_ready("open", None, 1, now)
    assert not force_assign_ready("open", None, 0, now)
    # naive datetimes are treated as UTC
    assert force_assign_ready("open", stale.replace(tzinfo=None), 1, now)
    # never for non-open bookings
    assert not force_assign_ready("assigned", stale, 5, now)
    assert not force_assign_ready("completed", stale, 5, now)
