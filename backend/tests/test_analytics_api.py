"""Unit tests for analytics rollups, filters, scoping, and invoices."""

import itertools
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.db import SessionLocal
from app.models import (
    Booking,
    BookingExclusion,
    BookingOffer,
    Partner,
    SaasInvoice,
    User,
)
from tests.conftest import make_client
from tests.test_force_assign import _login

SLOT = "evening"

_pins = itertools.count(999000)
_cats = itertools.count(1)
_sp2_mobiles = itertools.count(9193990001)


def _dataset():
    """Insert a distinctive slice with unique pin/cat; returns ids + filter."""
    pin, cat = str(next(_pins)), f"cat-analytics-{next(_cats)}"
    db = SessionLocal()
    try:
        partner = db.scalar(select(Partner).limit(1))
        cust = db.scalar(select(User).where(User.mobile == "9000000004"))
        sp = db.scalar(select(User).where(User.mobile == "9000000003"))
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=40)
        mk = lambda **kw: Booking(partner_id=partner.id, customer_id=cust.id,
                                  address_id="a", pincode=pin, category_id=cat,
                                  service_date=date.today(), slot=SLOT, **kw)
        rows = [
            mk(status="open"),
            mk(status="assigned", assigned_sp_id=sp.id,
               first_accepted_at=now - timedelta(minutes=30)),
            mk(status="completed", assigned_sp_id=sp.id,
               first_accepted_at=now - timedelta(hours=2),
               collected_amount=Decimal("500.00"),
               commission_amount=Decimal("50.00")),
            mk(status="completed", assigned_sp_id=sp.id,
               first_accepted_at=now - timedelta(hours=3),
               collected_amount=Decimal("300.00"),
               commission_amount=Decimal("30.00"),
               reassign_count=1, pool_empty=True),
            mk(status="cancelled"),
            mk(status="no_show"),
        ]
        stale = mk(status="completed", collected_amount=Decimal("9999.00"),
                   commission_amount=Decimal("999.00"))
        db.add_all(rows + [stale])
        db.flush()
        stale.created_at = old  # outside the default 30d window
        ghost = mk(status="open")
        ghost.partner_id = "ghost-partner"
        db.add(ghost)
        sp2 = User(role="service_partner", partner_id=partner.id,
                   full_name="SP2", mobile=str(next(_sp2_mobiles)),
                   email="", status="active")
        db.add(sp2)
        db.flush()
        db.add(BookingOffer(booking_id=rows[0].id, service_partner_id=sp.id))
        db.add(BookingExclusion(booking_id=rows[0].id, service_partner_id=sp.id,
                                reason="declined"))
        db.add(BookingExclusion(booking_id=rows[0].id, service_partner_id=sp2.id,
                                reason="dropped"))
        other = Partner(trade_name="Analytics Other", status="approved")
        db.add(other)
        db.flush()
        db.add(SaasInvoice(partner_id=partner.id, period_start=date.today(),
                            period_end=date.today(), amount=Decimal("100.00"),
                            status="paid"))
        db.add(SaasInvoice(partner_id=other.id, period_start=date.today(),
                            period_end=date.today(), amount=Decimal("200.00"),
                            status="overdue"))
        db.commit()
        return {"bids": [r.id for r in rows], "ghost": ghost.id,
                "other_pid": other.id, "partner_id": partner.id,
                "q": f"?pincode={pin}&category_id={cat}&slot={SLOT}",
                "pin": pin}
    finally:
        db.close()


def _snap(client, token, query=""):
    r = client.get(f"/v1/analytics{query}",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    return r.json()


def test_funnel_math_and_rates(capsys):
    with make_client() as client:
        master = _login(client, capsys, "9000000001")
        ds = _dataset()
        s = _snap(client, master["token"], ds["q"])
        assert s["created"] == 7  # stale one excluded by window
        assert s["still_open"] == 2  # open + ghost-partner open
        assert s["accepted"] == 3
        assert s["completed"] == 2
        assert s["cancelled"] == 1
        assert s["no_show"] == 1
        assert s["dropped_after_accept"] == 1
        assert s["accept_rate"] == 3 / 7
        assert s["completion_rate"] == 2 / 3
        assert s["median_accept_minutes"] is not None
        assert s["avg_accept_minutes"] is not None
        assert s["gmv_completed"] == "800.00"
        assert s["commission_completed"] == "80.00"
        assert s["empty_pool"] == 1
        assert s["offers"] == 1
        assert s["declines"] == 1


def test_empty_slice_zero_rates(capsys):
    with make_client() as client:
        master = _login(client, capsys, "9000000001")
        s = _snap(client, master["token"], "?pincode=000000")
        assert s["created"] == 0
        assert s["accept_rate"] == 0
        assert s["completion_rate"] == 0
        assert s["median_accept_minutes"] is None
        assert s["gmv_completed"] == "0"


def test_filters_narrow(capsys):
    with make_client() as client:
        master = _login(client, capsys, "9000000001")
        ds = _dataset()
        full = _snap(client, master["token"], f"?pincode={ds['pin']}")
        assert full["created"] >= 7
        narrow = _snap(client, master["token"], ds["q"])
        assert narrow["created"] == 7
        assert _snap(client, master["token"],
                     f"?pincode={ds['pin']}&slot=morning")["created"] == 0


def test_role_scoping_and_customer_forbidden(capsys):
    with make_client() as client:
        master = _login(client, capsys, "9000000001")
        owner = _login(client, capsys, "9000000002")
        sp = _login(client, capsys, "9000000003")
        cust = _login(client, capsys, "9000000004")
        ds = _dataset()
        assert _snap(client, owner["token"], ds["q"])["created"] == 6  # ghost excluded
        got = _snap(client, sp["token"], ds["q"])
        assert got["created"] == 3  # only assigned-to-me
        assert got["completed"] == 2
        r = client.get("/v1/analytics",
                       headers={"Authorization": f"Bearer {cust['token']}"})
        assert r.status_code == 403


def test_saas_master_only_and_by_partner(capsys):
    with make_client() as client:
        master = _login(client, capsys, "9000000001")
        owner = _login(client, capsys, "9000000002")
        ds = _dataset()
        s = _snap(client, master["token"], ds["q"])
        saas = s["saas_license_fees"]
        assert Decimal(saas["collected"]) >= Decimal("100.00")
        assert Decimal(saas["overdue"]) >= Decimal("200.00")
        assert Decimal(saas["invoiced"]) >= Decimal("300.00")
        byp = {r["partner_id"]: r for r in s["by_partner"]}
        assert byp["ghost-partner"]["trade_name"] == "ghost-partner"
        assert byp["ghost-partner"]["created"] == 1
        assert byp[ds["partner_id"]]["created"] == 6
        o = _snap(client, owner["token"], ds["q"])
        assert o["saas_license_fees"]["invoiced"] == "0"
        assert o["by_partner"] == []


def test_invoices_scoping_and_shape(capsys):
    with make_client() as client:
        master = _login(client, capsys, "9000000001")
        owner = _login(client, capsys, "9000000002")
        cust = _login(client, capsys, "9000000004")
        _dataset()
        all_rows = client.get("/v1/invoices",
                              headers={"Authorization": f"Bearer {master['token']}"}).json()
        own = client.get("/v1/invoices",
                         headers={"Authorization": f"Bearer {owner['token']}"}).json()
        assert len(all_rows) > len(own) >= 1
        assert all(r["partner_id"] == owner["user"]["partner_id"] for r in own)
        assert set(all_rows[0]) == {"id", "partner_id", "amount", "status",
                                    "period_start", "period_end"}
        r = client.get("/v1/invoices",
                       headers={"Authorization": f"Bearer {cust['token']}"})
        assert r.status_code == 403
