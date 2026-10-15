"""Unit tests for the dispatch job: eligibility, pooling, repool, retry."""

import itertools
import sqlite3
from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.jobs.dispatch_job as dj
from app.jobs.dispatch_job import (
    dispatch_pool,
    dispatch_repool_open,
    eligible_technicians,
    partner_admins,
    slot_job_count,
    with_busy_retry,
)
from app.models import (
    AvailabilityBlock,
    Base,
    Booking,
    BookingExclusion,
    BookingOffer,
    Notification,
    Partner,
    ServiceCategory,
    ServicePartnerCategory,
    ServicePartnerPincode,
    ServicePartnerProfile,
    User,
)

DAY = date(2027, 1, 5)
_mobiles = itertools.count(9188001000)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _mobile():
    return str(next(_mobiles))


def _partner(db, status="approved", trade_name=None):
    p = Partner(trade_name=trade_name or f"P{_mobile()}", status=status)
    db.add(p)
    db.flush()
    return p


def _user(db, role, partner_id=None, status="active", mobile=None):
    u = User(role=role, partner_id=partner_id, full_name=f"U{_mobile()}",
             mobile=mobile or _mobile(), email="", status=status)
    db.add(u)
    db.flush()
    return u


def _cat(db, slug=None):
    c = ServiceCategory(slug=slug or f"c{_mobile()}", name_en="C")
    db.add(c)
    db.flush()
    return c


def _sp(db, partner, cat_id, pin, kyc="approved", status="active", mobile=None):
    u = _user(db, "service_partner", partner.id, status, mobile)
    db.add(ServicePartnerProfile(user_id=u.id, partner_id=partner.id, kyc_status=kyc))
    db.add(ServicePartnerCategory(user_id=u.id, category_id=cat_id))
    db.add(ServicePartnerPincode(user_id=u.id, pincode=pin))
    db.flush()
    return u


def _booking(db, partner, customer, category, pin="682001", day=DAY, slot="morning",
             status="open", sp_id=None):
    b = Booking(partner_id=partner.id, customer_id=customer.id, address_id="addr-x",
                pincode=pin, category_id=category.id, service_date=day, slot=slot,
                status=status, assigned_sp_id=sp_id)
    db.add(b)
    db.flush()
    return b


def _locked():
    return OperationalError("x", None, sqlite3.OperationalError("database is locked"))


# -- with_busy_retry --------------------------------------------------------

def test_retry_success_first_try():
    assert with_busy_retry("t", lambda: "ok") == "ok"


def test_retry_recovers_from_transient_lock(capsys):
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise _locked()
        return "ok"

    retries = []
    assert with_busy_retry("t", flaky, on_retry=lambda: retries.append(1)) == "ok"
    assert len(calls) == 3 and retries == [1, 1]
    assert "busy, retry" in capsys.readouterr().out


def test_retry_propagates_non_lock_errors():
    def foreign():
        raise OperationalError("x", None, Exception("no such table: nope"))

    with pytest.raises(OperationalError):
        with_busy_retry("t", foreign, attempts=3)


def test_retry_exhaustion_reraises_raw_sqlite_error():
    def raw():
        raise sqlite3.OperationalError("database is locked")

    with pytest.raises(sqlite3.OperationalError, match="locked"):
        with_busy_retry("t", raw, attempts=2)


def test_retry_single_attempt_raises_immediately():
    with pytest.raises(OperationalError):
        with_busy_retry("t", lambda: (_ for _ in ()).throw(_locked()), attempts=1)


# -- slot_job_count ----------------------------------------------------------

def test_slot_job_count_statuses(db):
    partner = _partner(db)
    cust = _user(db, "customer")
    cat = _cat(db)
    sp = _sp(db, partner, cat.id, "682001")
    for i, status in enumerate(("assigned", "en_route", "in_progress", "completed",
                               "open", "cancelled")):
        _booking(db, partner, cust, cat, status=status,
                 sp_id=sp.id if status != "open" else None)
    _booking(db, partner, cust, cat, slot="evening", status="assigned", sp_id=sp.id)
    assert slot_job_count(db, sp.id, DAY, "morning") == 4
    assert slot_job_count(db, sp.id, DAY, "evening") == 1
    assert slot_job_count(db, "ghost", DAY, "morning") == 0


# -- partner_admins ------------------------------------------------------------

def test_partner_admins_scope(db):
    p1, p2 = _partner(db), _partner(db)
    owner = _user(db, "partner_owner", p1.id)
    admin = _user(db, "partner_admin", p1.id)
    _user(db, "partner_admin", p1.id, status="suspended")
    _user(db, "customer", p1.id)
    _user(db, "partner_owner", p2.id)
    got = {u.id for u in partner_admins(db, p1.id)}
    assert got == {owner.id, admin.id}


# -- eligible_technicians -------------------------------------------------------

def test_eligible_matrix(db):
    partner = _partner(db)
    cust = _user(db, "customer")
    cat = _cat(db)
    bid = _booking(db, partner, cust, cat).id
    booking = db.get(Booking, bid)

    ok = _sp(db, partner, cat.id, "682001", mobile=_mobile())
    _sp(db, partner, cat.id, "682001", kyc="pending")  # kyc gate
    ghost = _user(db, "service_partner", partner.id)
    db.add(ServicePartnerProfile(user_id="ghost-user", partner_id=partner.id,
                                 kyc_status="approved"))  # no such user
    _sp(db, partner, cat.id, "682001", status="suspended")  # inactive
    nocat = _sp(db, partner, cat.id, "682001")
    db.delete(db.get(ServicePartnerCategory, (nocat.id, cat.id)))
    nopin = _sp(db, partner, cat.id, "682001")
    db.delete(db.get(ServicePartnerPincode, (nopin.id, "682001")))
    excl = _sp(db, partner, cat.id, "682001")
    db.add(BookingExclusion(booking_id=bid, service_partner_id=excl.id, reason="declined"))
    fullday = _sp(db, partner, cat.id, "682001")
    db.add(AvailabilityBlock(user_id=fullday.id, block_date=DAY, slot=None))
    sameslot = _sp(db, partner, cat.id, "682001")
    db.add(AvailabilityBlock(user_id=sameslot.id, block_date=DAY, slot="morning"))
    otherslot = _sp(db, partner, cat.id, "682001")
    db.add(AvailabilityBlock(user_id=otherslot.id, block_date=DAY, slot="evening"))
    capped = _sp(db, partner, cat.id, "682001")
    for _ in range(5):
        _booking(db, partner, cust, cat, status="assigned", sp_id=capped.id)
    almost = _sp(db, partner, cat.id, "682001")
    for _ in range(4):
        _booking(db, partner, cust, cat, status="assigned", sp_id=almost.id)
    db.flush()

    got = {e["user"].id: e["jobs_in_slot"] for e in eligible_technicians(db, booking)}
    assert set(got) == {ok.id, otherslot.id, almost.id}
    assert got[almost.id] == 4
    assert got[ok.id] == 0


# -- dispatch_pool ---------------------------------------------------------------

def _staffed(db, pin="682001"):
    partner = _partner(db)
    owner = _user(db, "partner_owner", partner.id)
    admin = _user(db, "partner_admin", partner.id)
    cust = _user(db, "customer")
    cat = _cat(db)
    return partner, owner, admin, cust, cat


def _notes(db, user_id, bid):
    return [n.type for n in db.scalars(
        select(Notification).where(Notification.user_id == user_id,
                                   Notification.booking_id == bid))]


def test_pool_happy_path_and_repool(db):
    partner, owner, admin, cust, cat = _staffed(db)
    s1 = _sp(db, partner, cat.id, "682001")
    s2 = _sp(db, partner, cat.id, "682001")
    bid = _booking(db, partner, cust, cat).id

    out = dispatch_pool(db, bid)
    assert out == {"offered": [s1.id, s2.id], "empty": False}
    booking = db.get(Booking, bid)
    assert booking.dispatch_refresh_count == 1
    assert booking.pool_empty is False
    assert booking.last_dispatch_at is not None
    assert _notes(db, s1.id, bid) == ["offer"]
    assert _notes(db, owner.id, bid) == ["new_request"]
    assert _notes(db, admin.id, bid) == ["new_request"]

    out = dispatch_pool(db, bid, admin_reminder=True)
    assert out["offered"] == [s1.id, s2.id]
    assert db.get(Booking, bid).dispatch_refresh_count == 2
    assert _notes(db, owner.id, bid) == ["new_request", "open_reminder"]
    offers = list(db.scalars(select(BookingOffer).where(BookingOffer.booking_id == bid)))
    assert len(offers) == 2  # re-pool refreshes, never duplicates


def test_pool_skips_missing_and_settled(db):
    assert dispatch_pool(db, "00000000-0000-0000-0000-000000000000") == {"skipped": True}
    partner, _, _, cust, cat = _staffed(db)
    bid = _booking(db, partner, cust, cat, status="assigned").id
    assert dispatch_pool(db, bid) == {"skipped": True}


def test_pool_partner_gates(db):
    partner, _, _, cust, cat = _staffed(db, "682001")
    suspended = _partner(db, status="suspended")
    b1 = _booking(db, suspended, cust, cat).id
    out = dispatch_pool(db, b1)
    assert out == {"empty": True, "reason": "partner"}
    assert db.get(Booking, b1).pool_empty is True
    b2 = _booking(db, partner, cust, cat).id
    db.get(Booking, b2).partner_id = "ghost-partner"
    out = dispatch_pool(db, b2)
    assert out == {"empty": True, "reason": "partner"}


def test_pool_empty_pool_note(db):
    partner, owner, _, cust, cat = _staffed(db)
    lonely = _cat(db)
    bid = _booking(db, partner, cust, lonely).id  # nobody offers this category
    out = dispatch_pool(db, bid)
    assert out == {"offered": [], "empty": True}
    assert db.get(Booking, bid).pool_empty is True
    assert _notes(db, owner.id, bid) == ["empty_pool"]


def test_pool_settled_mid_pool_rolls_back(db, monkeypatch):
    partner, _, _, cust, cat = _staffed(db)
    _sp(db, partner, cat.id, "682001")
    bid = _booking(db, partner, cust, cat).id

    real_refresh = db.refresh

    def _flip(target, *args, **kwargs):
        real_refresh(target, *args, **kwargs)
        target.status = "assigned"  # raced accept landing mid-pool

    monkeypatch.setattr(db, "refresh", _flip)
    out = dispatch_pool(db, bid)
    assert out == {"skipped": True, "reason": "settled_mid_pool"}
    assert list(db.scalars(
        select(BookingOffer).where(BookingOffer.booking_id == bid))) == []


def test_pool_exception_rolls_back(db, monkeypatch):
    partner, _, _, cust, cat = _staffed(db)
    _sp(db, partner, cat.id, "682001")
    bid = _booking(db, partner, cust, cat).id

    def _boom(*args, **kwargs):
        raise RuntimeError("notify down")

    monkeypatch.setattr(dj, "notify", _boom)
    with pytest.raises(RuntimeError, match="notify down"):
        dispatch_pool(db, bid)
    assert list(db.scalars(
        select(BookingOffer).where(BookingOffer.booking_id == bid))) == []


def test_repool_open_fanout(db):
    partner, owner, _, cust, cat = _staffed(db)
    _sp(db, partner, cat.id, "682001")
    b1 = _booking(db, partner, cust, cat).id
    b2 = _booking(db, partner, cust, cat).id
    _booking(db, partner, cust, cat, status="completed")
    assert dispatch_repool_open(db) == 2
    assert _notes(db, owner.id, b1) == ["open_reminder"]
    assert _notes(db, owner.id, b2) == ["open_reminder"]
