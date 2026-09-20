from app.domain.dispatch import (
    ALREADY_TAKEN,
    ASSIGNED,
    TechnicianEligibility,
    accept_lock,
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
