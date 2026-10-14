from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

OPEN = "open"
ASSIGNED = "assigned"
ALREADY_TAKEN = "already_taken"
DECLINED = "declined"
DROPPED = "dropped"

# Partner fallback: strict first-accept rules until one full 3h window has
# passed with no accept (or two pools ran and the booking is still open).
FORCE_ASSIGN_AFTER_HOURS = 3
FORCE_ASSIGN_MIN_REFRESHES = 2


@dataclass(frozen=True)
class TechnicianEligibility:
    approved: bool
    same_partner: bool
    offers_category: bool
    works_pincode: bool
    excluded: bool
    jobs_in_slot: int


def is_eligible(t: TechnicianEligibility) -> bool:
    from app.domain.booking_rules import slot_has_capacity

    return (
        t.approved
        and t.same_partner
        and t.offers_category
        and t.works_pincode
        and not t.excluded
        and slot_has_capacity(t.jobs_in_slot)
    )


def accept_lock(current_status: str) -> str:
    """First accept wins. Only an open booking can move to assigned."""
    if current_status == OPEN:
        return ASSIGNED
    return ALREADY_TAKEN


def next_pool_excludes(reason: str) -> bool:
    return reason in {DECLINED, DROPPED}


def force_assign_ready(
    status: str,
    created_at: datetime | None,
    dispatch_refresh_count: int,
    now: datetime | None = None,
) -> bool:
    """Partner fallback gate: only a stale open booking may be force-assigned.

    Ready when the booking is still open and either a full 3h window has
    elapsed since creation or two dispatch pools ran with no accept.
    """
    if status != OPEN:
        return False
    if (dispatch_refresh_count or 0) >= FORCE_ASSIGN_MIN_REFRESHES:
        return True
    if created_at is None:
        return False
    moment = now or datetime.now(timezone.utc)
    start = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
    return (moment - start) >= timedelta(hours=FORCE_ASSIGN_AFTER_HOURS)
