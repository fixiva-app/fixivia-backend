from __future__ import annotations

from dataclasses import dataclass

OPEN = "open"
ASSIGNED = "assigned"
ALREADY_TAKEN = "already_taken"
DECLINED = "declined"
DROPPED = "dropped"


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
