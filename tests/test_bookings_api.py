"""Unit tests for addresses, booking CRUD, and visibility."""

import itertools
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Booking, BookingPhoto, CategoryIssueTemplate, User
from tests.conftest import make_client
from tests.test_force_assign import _book, _login

_days = itertools.count(60)
_slugs = itertools.count(1)


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _seed_cat(client):
    cats = client.get("/v1/categories").json()
    cat = [c for c in cats if c.get("featured_rank")][0]
    issues = [p["id"] for p in cat["problems"] if p.get("featured_rank")][:2]
    return cat["id"], issues


def _addr(client, h_c, pin="682001"):
    r = client.post("/v1/addresses", headers=h_c, json={
        "label": "home", "line1": "1 St", "pincode": pin, "is_default": True})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _payload(client, h_c, addr_id, cat_id, issues, days=61, **kw):
    body = {"address_id": addr_id, "category_id": cat_id,
            "issue_template_ids": issues,
            "service_date": (date.today() + timedelta(days=days)).isoformat(),
            "slot": "morning"}
    body.update(kw)
    return client.post("/v1/bookings", headers=h_c, json=body)


def _fresh_sp(client, capsys, partner_id):
    """A disposable SP. Completes run as fresh SPs so the seed SP's ledger
    stays empty for the earnings-shape test."""
    reg = _login(client, capsys, f"9195{next(_days):06d}", "register",
                 full_name="Fresh", role="service_partner",
                 partner_id=partner_id)
    return _headers(reg["token"]), reg


def test_addresses_crud_and_gates(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        sp = _login(client, capsys, "9000000003")
        h_c, h_s = _headers(cust["token"]), _headers(sp["token"])
        assert client.get("/v1/addresses", headers=h_s).status_code == 403
        assert client.post("/v1/addresses", headers=h_s,
                           json={"line1": "x", "pincode": "682001"}).status_code == 403
        r = client.post("/v1/addresses", headers=h_c,
                        json={"line1": "x", "pincode": "000000"})
        assert r.status_code == 400
        assert r.json() == {"detail": "unknown_pincode"}
        before = len(client.get("/v1/addresses", headers=h_c).json())
        aid = _addr(client, h_c)
        rows = client.get("/v1/addresses", headers=h_c).json()
        assert len(rows) == before + 1
        assert set(rows[-1]) == {"id", "label", "line1", "landmark", "pincode",
                                 "is_default"}
        assert aid in [a["id"] for a in rows]


def test_create_validation_matrix(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        master = _login(client, capsys, "9000000001")
        h_c, h_m = _headers(cust["token"]), _headers(master["token"])
        cat_id, issues = _seed_cat(client)
        addr = _addr(client, h_c)
        base = {"address_id": addr, "category_id": cat_id,
                "issue_template_ids": issues,
                "service_date": (date.today() + timedelta(days=next(_days))).isoformat(),
                "slot": "morning"}
        r = client.post("/v1/bookings", headers=h_c,
                        json={**base, "slot": "night"})
        assert r.json() == {"detail": "bad_slot"}
        r = client.post("/v1/bookings", headers=h_c,
                        json={**base, "service_date": date.today().isoformat()})
        assert r.json() == {"detail": "date_too_soon"}
        r = client.post("/v1/bookings", headers=h_c,
                        json={**base, "address_id": "nope"})
        assert r.status_code == 404
        reg = _login(client, capsys, f"9195{next(_days):06d}", "register",
                     full_name="B", role="customer")
        foreign = _addr(client, _headers(reg["token"]))
        r = client.post("/v1/bookings", headers=h_c,
                        json={**base, "address_id": foreign})
        assert r.status_code == 404
        r = client.post("/v1/bookings", headers=h_m, json=base)
        assert r.status_code == 403  # only customers book
        r = client.post("/v1/bookings", headers=h_c,
                        json={**base, "category_id": "nope"})
        assert r.json() == {"detail": "bad_category"}
        r = client.post("/v1/bookings", headers=h_c,
                        json={**base, "issue_template_ids": []})
        assert r.status_code == 422
        loner = _addr(client, h_c, pin="673001")
        r = client.post("/v1/bookings", headers=h_c,
                        json={**base, "address_id": loner})
        assert r.json() == {"detail": "no_partner_for_pincode"}


def test_create_gates_inactive_unpriced_and_bad_issues(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        master = _login(client, capsys, "9000000001")
        owner = _login(client, capsys, "9000000002")
        h_c, h_m, h_o = (_headers(cust["token"]), _headers(master["token"]),
                         _headers(owner["token"]))
        cat_id, issues = _seed_cat(client)
        addr = _addr(client, h_c)
        slug = f"u-book-{next(_slugs)}"
        created = client.post("/v1/categories", headers=h_m, json={
            "slug": slug, "name_en": slug,
            "problems": [{"text_en": "Fix", "sort_order": 0}]}).json()
        prob = created["problems"][0]["id"]
        payload = {"address_id": addr, "category_id": created["id"],
                   "issue_template_ids": [prob],
                   "service_date": (date.today() + timedelta(days=next(_days))).isoformat(),
                   "slot": "morning"}
        r = client.post("/v1/bookings", headers=h_c, json=payload)
        assert r.json() == {"detail": "category_not_offered"}
        client.put("/v1/partner/pricing", headers=h_o,
                   json={"category_id": created["id"], "enabled": False,
                         "visit_charge": "100.00"})
        r = client.post("/v1/bookings", headers=h_c, json=payload)
        assert r.json() == {"detail": "category_not_offered"}
        client.put("/v1/partner/pricing", headers=h_o,
                   json={"category_id": created["id"], "visit_charge": "100.00"})
        r = client.post("/v1/bookings", headers=h_c,
                        json={**payload, "issue_template_ids": ["nope"]})
        assert r.json() == {"detail": "bad_issue"}
        r = client.post("/v1/bookings", headers=h_c,
                        json={**payload, "issue_template_ids": issues})
        assert r.json() == {"detail": "bad_issue"}  # seed issue, wrong category
        ok = client.post("/v1/bookings", headers=h_c,
                         json={**payload, "issue_note": "pls hurry",
                               "photo_paths": ["s3://a", "s3://b"]})
        assert ok.status_code == 200, ok.text
        assert ok.json()["issue_note"] == "pls hurry"
        assert ok.json()["issues"] == [{"id": prob, "text_en": "Fix"}]
        db = SessionLocal()
        try:
            photos = list(db.scalars(select(BookingPhoto).where(
                BookingPhoto.booking_id == ok.json()["id"])))
            assert len(photos) == 2
        finally:
            db.close()
        client.put(f"/v1/categories/{created['id']}", headers=h_m, json={
            "slug": slug, "name_en": slug, "is_active": False,
            "problems": [{"text_en": "Fix", "sort_order": 0}]})
        r = client.post("/v1/bookings", headers=h_c, json=payload)
        assert r.json() == {"detail": "bad_category"}


def test_list_scoping_and_status_filter(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        sp = _login(client, capsys, "9000000003")
        owner = _login(client, capsys, "9000000002")
        master = _login(client, capsys, "9000000001")
        h_c, h_s, h_o, h_m = (_headers(cust["token"]), _headers(sp["token"]),
                              _headers(owner["token"]), _headers(master["token"]))
        bid, _ = _book(client, h_c, next(_days))
        mine = client.get("/v1/bookings", headers=h_c).json()
        assert bid in [b["id"] for b in mine]
        assert all(b["customer_id"] == cust["user"]["id"] for b in mine)
        assert bid in [b["id"] for b in
                       client.get("/v1/bookings?status=open", headers=h_c).json()]
        assert bid not in [b["id"] for b in
                           client.get("/v1/bookings?status=completed", headers=h_c).json()]
        offered = client.get("/v1/bookings", headers=h_s).json()
        assert bid in [b["id"] for b in offered]
        own = client.get("/v1/bookings", headers=h_o).json()
        assert bid in [b["id"] for b in own]
        assert all(b["partner_id"] == owner["user"]["partner_id"] for b in own)
        assert bid in [b["id"] for b in client.get("/v1/bookings", headers=h_m).json()]


def test_list_unknown_role_forbidden():
    from app.services.tokens import issue_token

    db = SessionLocal()
    try:
        ghost = User(role="ghost", full_name="G", mobile=f"9196{next(_days):06d}",
                     email="", status="active")
        db.add(ghost)
        db.commit()
        gid = ghost.id
    finally:
        db.close()
    with make_client() as client:
        tok = issue_token(user_id=gid, role="ghost", partner_id=None)
        r = client.get("/v1/bookings", headers=_headers(tok))
        assert r.status_code == 403
        assert r.json() == {"detail": "forbidden"}


def test_detail_visibility_matrix(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        sp = _login(client, capsys, "9000000003")
        owner = _login(client, capsys, "9000000002")
        master = _login(client, capsys, "9000000001")
        h_c, h_s, h_o, h_m = (_headers(cust["token"]), _headers(sp["token"]),
                              _headers(owner["token"]), _headers(master["token"]))
        bid, _ = _book(client, h_c, next(_days))
        assert client.get("/v1/bookings/nope", headers=h_c).status_code == 404
        assert client.get(f"/v1/bookings/{bid}", headers=h_c).status_code == 200
        assert client.get(f"/v1/bookings/{bid}", headers=h_s).status_code == 200
        assert client.get(f"/v1/bookings/{bid}", headers=h_o).status_code == 200
        assert client.get(f"/v1/bookings/{bid}", headers=h_m).status_code == 200
        reg = _login(client, capsys, f"9195{next(_days):06d}", "register",
                     full_name="S", role="customer")
        r = client.get(f"/v1/bookings/{bid}", headers=_headers(reg["token"]))
        assert r.status_code == 403


def test_detail_skips_deleted_templates_and_otp_hint(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        sp = _login(client, capsys, "9000000003")
        master = _login(client, capsys, "9000000001")
        owner = _login(client, capsys, "9000000002")
        h_c, h_s = _headers(cust["token"]), _headers(sp["token"])
        h_m, h_o = _headers(master["token"]), _headers(owner["token"])
        bid, _ = _book(client, h_c, next(_days))
        assert client.get(f"/v1/bookings/{bid}", headers=h_c).json()[
            "start_work_otp_hint"] is None
        assert client.post(f"/v1/bookings/{bid}/accept", headers=h_s).status_code == 200
        assert client.get(f"/v1/bookings/{bid}",
                          headers=h_c).json()["start_work_otp_hint"] == "sent_to_your_phone"
        assert client.get(f"/v1/bookings/{bid}",
                          headers=h_s).json()["start_work_otp_hint"] is None
        # own throwaway category: deleting its template harms no other test
        slug = f"u-tpl-{next(_slugs)}"
        created = client.post("/v1/categories", headers=h_m, json={
            "slug": slug, "name_en": slug,
            "problems": [{"text_en": "Fix", "sort_order": 0}]}).json()
        client.put("/v1/partner/pricing", headers=h_o,
                   json={"category_id": created["id"], "visit_charge": "100.00"})
        addr = _addr(client, h_c)
        lone = _payload(client, h_c, addr, created["id"],
                        [created["problems"][0]["id"]], days=next(_days)).json()["id"]
        db = SessionLocal()
        try:
            tpl = db.get(CategoryIssueTemplate, created["problems"][0]["id"])
            db.delete(tpl)
            db.commit()
        finally:
            db.close()
        assert client.get(f"/v1/bookings/{lone}", headers=h_c).json()["issues"] == []


def test_accept_unknown_and_slot_full(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        owner = _login(client, capsys, "9000000002")
        sp = _login(client, capsys, "9000000003")
        h_c, h_o, h_s = (_headers(cust["token"]), _headers(owner["token"]),
                         _headers(sp["token"]))
        assert client.post("/v1/bookings/nope/accept", headers=h_s).status_code == 404
        assert client.post("/v1/bookings/nope/accept", headers=h_o).status_code == 403
        reg = _login(client, capsys, f"9195{next(_days):06d}", "register",
                     full_name="Cap", role="service_partner",
                     partner_id=owner["user"]["partner_id"])
        h_n = _headers(reg["token"])
        off = next(_days)
        day = date.today() + timedelta(days=off)
        db = SessionLocal()
        try:
            me = client.get("/v1/partners/me", headers=h_o).json()
            cust_row = db.scalar(select(User).where(User.mobile == "9000000004"))
            for _ in range(5):
                db.add(Booking(partner_id=me["id"], customer_id=cust_row.id,
                               address_id="a", pincode="682001", category_id="c",
                               service_date=day, slot="morning",
                               status="assigned", assigned_sp_id=reg["user"]["id"]))
            db.commit()
        finally:
            db.close()
        cat_id, issues = _seed_cat(client)
        addr = _addr(client, h_c)
        created = _payload(client, h_c, addr, cat_id, issues, days=off).json()
        r = client.post(f"/v1/bookings/{created['id']}/accept", headers=h_n)
        assert r.status_code == 400
        assert r.json() == {"detail": "slot_full"}


def test_assignable_reasons_and_tenant(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        sp = _login(client, capsys, "9000000003")
        owner = _login(client, capsys, "9000000002")
        h_c, h_s, h_o = (_headers(cust["token"]), _headers(sp["token"]),
                         _headers(owner["token"]))
        bid, _ = _book(client, h_c, next(_days))
        assert client.get("/v1/bookings/nope/assignable", headers=h_o).status_code == 404
        assert client.post(f"/v1/bookings/{bid}/accept", headers=h_s).status_code == 200
        state = client.get(f"/v1/bookings/{bid}/assignable", headers=h_o).json()
        assert state["ready"] is False and state["reason"] == "not_open"
        db = SessionLocal()
        try:
            cust_row = db.scalar(select(User).where(User.mobile == "9000000004"))
            foreign = Booking(partner_id="ghost-partner", customer_id=cust_row.id,
                              address_id="a", pincode="682001", category_id="c",
                              service_date=date.today(), slot="morning", status="open")
            db.add(foreign)
            db.commit()
            fid = foreign.id
        finally:
            db.close()
        r = client.get(f"/v1/bookings/{fid}/assignable", headers=h_o)
        assert r.status_code == 403
        r = client.post(f"/v1/bookings/{fid}/force-assign", headers=h_o,
                        json={"service_partner_id": sp["user"]["id"]})
        assert r.status_code == 403


def test_force_assign_target_gates(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        owner = _login(client, capsys, "9000000002")
        h_c, h_o = _headers(cust["token"]), _headers(owner["token"])
        bid, _ = _book(client, h_c, next(_days))
        db = SessionLocal()
        try:
            db.get(Booking, bid).dispatch_refresh_count = 2
            db.commit()
        finally:
            db.close()
        r = client.post("/v1/bookings/nope/force-assign", headers=h_o,
                        json={"service_partner_id": "x"})
        assert r.status_code == 404
        r = client.post(f"/v1/bookings/{bid}/force-assign", headers=h_o,
                        json={"service_partner_id": "nope"})
        assert r.status_code == 404
        assert r.json() == {"detail": "sp_not_found"}
        r = client.post(f"/v1/bookings/{bid}/force-assign", headers=h_o,
                        json={"service_partner_id": cust["user"]["id"]})
        assert r.json() == {"detail": "sp_not_found"}  # not an SP at all
        db = SessionLocal()
        try:
            outsider = User(role="service_partner", partner_id="ghost-partner",
                            full_name="O", mobile=f"9196{next(_days):06d}",
                            email="", status="active")
            db.add(outsider)
            db.commit()
            oid = outsider.id
        finally:
            db.close()
        r = client.post(f"/v1/bookings/{bid}/force-assign", headers=h_o,
                        json={"service_partner_id": oid})
        assert r.status_code == 400
        assert r.json() == {"detail": "sp_ineligible"}


def test_decline_drop_gates(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        sp = _login(client, capsys, "9000000003")
        h_c, h_s = _headers(cust["token"]), _headers(sp["token"])
        assert client.post("/v1/bookings/nope/decline", headers=h_s).status_code == 404
        assert client.post("/v1/bookings/nope/drop", headers=h_s).status_code == 404
        bid, _ = _book(client, h_c, next(_days))
        assert client.post(f"/v1/bookings/{bid}/accept", headers=h_s).status_code == 200
        reg = _login(client, capsys, f"9195{next(_days):06d}", "register",
                     full_name="Z", role="service_partner",
                     partner_id=sp["user"]["partner_id"])
        r = client.post(f"/v1/bookings/{bid}/drop", headers=_headers(reg["token"]))
        assert r.status_code == 403
        assert r.json() == {"detail": "forbidden"}


def _start_code(client, capsys, h_s, bid):
    capsys.readouterr()
    assert client.post(f"/v1/bookings/{bid}/accept", headers=h_s).status_code == 200
    printed = capsys.readouterr().out
    line = [ln for ln in printed.splitlines()
            if "purpose=start_work" in ln and bid in ln][0]
    return line.split("code=")[1].split()[0]


def test_start_and_en_route_matrix(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        sp = _login(client, capsys, "9000000003")
        owner = _login(client, capsys, "9000000002")
        h_c, h_s = _headers(cust["token"]), _headers(sp["token"])
        h_f, fresh = _fresh_sp(client, capsys, owner["user"]["partner_id"])
        bid, _ = _book(client, h_c, next(_days))
        db = SessionLocal()
        try:
            # Start requires the service date to have arrived; the matrix
            # below exercises status/OTP gates, not the date gate.
            db.get(Booking, bid).service_date = date.today()
            db.commit()
        finally:
            db.close()
        assert client.post("/v1/bookings/nope/start", headers=h_f,
                           json={"code": "1"}).status_code == 404
        assert client.post("/v1/bookings/nope/en-route", headers=h_f).status_code == 404
        r = client.post(f"/v1/bookings/{bid}/start", headers=h_f,
                        json={"code": "123456"})
        assert r.status_code == 404  # not assigned to anyone yet
        code = _start_code(client, capsys, h_f, bid)
        r = client.post(f"/v1/bookings/{bid}/start", headers=h_f,
                        json={"code": "000000"})
        assert r.json() == {"detail": "otp_invalid"}
        r = client.post(f"/v1/bookings/{bid}/en-route", headers=h_f)
        assert r.json()["status"] == "en_route"
        r = client.post(f"/v1/bookings/{bid}/start", headers=h_f, json={"code": code})
        assert r.json()["status"] == "in_progress"
        client.post(f"/v1/bookings/{bid}/complete", headers=h_f, json={})
        r = client.post(f"/v1/bookings/{bid}/start", headers=h_f,
                        json={"code": code})
        assert r.status_code == 400
        assert r.json() == {"detail": "bad_status"}  # completed, not startable
        reg = _login(client, capsys, f"9195{next(_days):06d}", "register",
                     full_name="Z", role="service_partner",
                     partner_id=sp["user"]["partner_id"])
        r = client.post(f"/v1/bookings/{bid}/start",
                        headers=_headers(reg["token"]), json={"code": code})
        assert r.status_code == 404  # stranger technician
        bid2, _ = _book(client, h_c, next(_days))
        db = SessionLocal()
        try:
            b = db.get(Booking, bid2)
            b.status = "assigned"
            b.assigned_sp_id = fresh["user"]["id"]  # no OTP hash minted
            db.commit()
        finally:
            db.close()
        r = client.post(f"/v1/bookings/{bid2}/start", headers=h_f,
                        json={"code": "123456"})
        assert r.json() == {"detail": "otp_invalid"}


def test_start_too_early_until_due(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        owner = _login(client, capsys, "9000000002")
        h_c = _headers(cust["token"])
        h_f, _ = _fresh_sp(client, capsys, owner["user"]["partner_id"])
        bid, _ = _book(client, h_c, next(_days))
        code = _start_code(client, capsys, h_f, bid)
        r = client.post(f"/v1/bookings/{bid}/start", headers=h_f,
                        json={"code": code})
        assert r.json() == {"detail": "too_early"}
        r = client.post("/v1/dev/bookings/make-due",
                        json={"booking_ids": [bid]})
        assert r.status_code == 200, r.text
        assert r.json() == {"moved": [bid]}
        r = client.post(f"/v1/bookings/{bid}/start", headers=h_f,
                        json={"code": code})
        assert r.json()["status"] == "in_progress"


def test_complete_matrix(capsys):
    from app.models import PayoutLedger

    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        sp = _login(client, capsys, "9000000003")
        owner = _login(client, capsys, "9000000002")
        master = _login(client, capsys, "9000000001")
        h_c, h_s, h_o = (_headers(cust["token"]), _headers(sp["token"]),
                         _headers(owner["token"]))
        h_m = _headers(master["token"])
        assert client.post("/v1/bookings/nope/complete", headers=h_s,
                           json={}).status_code == 404
        bid, _ = _book(client, h_c, next(_days))
        assert client.post(f"/v1/bookings/{bid}/complete", headers=h_c,
                           json={}).status_code == 403
        assert client.post(f"/v1/bookings/{bid}/complete", headers=h_m,
                           json={}).status_code == 403
        h_f, _ = _fresh_sp(client, capsys, owner["user"]["partner_id"])
        assert client.post(f"/v1/bookings/{bid}/accept", headers=h_f).status_code == 200
        quoted = Decimal(client.get(f"/v1/bookings/{bid}",
                                    headers=h_c).json()["quoted_amount"])
        done = client.post(f"/v1/bookings/{bid}/complete", headers=h_f, json={}).json()
        assert done["status"] == "completed"
        assert done["payment_mode"] == "cash"
        assert done["rating"] is None
        db = SessionLocal()
        try:
            b = db.get(Booking, bid)
            assert b.collected_amount == quoted
            pct = Decimal("0.10")  # seed commission
            assert b.commission_amount == (quoted * pct).quantize(Decimal("0.01"))
            assert b.payout_amount == quoted - b.commission_amount
            rows = list(db.scalars(select(PayoutLedger).where(
                PayoutLedger.booking_id == bid)))
            assert len(rows) == 1 and rows[0].status == "pending"
            assert rows[0].amount == b.payout_amount
        finally:
            db.close()
        bid2, _ = _book(client, h_c, next(_days))
        assert client.post(f"/v1/bookings/{bid2}/accept", headers=h_f).status_code == 200
        done = client.post(f"/v1/bookings/{bid2}/complete", headers=h_o, json={
            "payment_mode": "upi", "collected_amount": "600.00",
            "razorpay_payment_id": "pay_x", "rating": 4,
            "rating_comment": "good"}).json()
        assert done["rating"] == 4
        db = SessionLocal()
        try:
            b = db.get(Booking, bid2)
            assert b.collected_amount == Decimal("600.00")
            assert b.razorpay_payment_id == "pay_x"
            assert b.rating_comment == "good"
        finally:
            db.close()


def test_complete_edge_paths(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        owner = _login(client, capsys, "9000000002")
        h_c, h_o = _headers(cust["token"]), _headers(owner["token"])
        from app.models import PayoutLedger

        # open booking completes too (no status guard — documents behavior)
        bid, _ = _book(client, h_c, next(_days))
        done = client.post(f"/v1/bookings/{bid}/complete", headers=h_o, json={}).json()
        assert done["status"] == "completed"
        db = SessionLocal()
        try:
            assert list(db.scalars(select(PayoutLedger).where(
                PayoutLedger.booking_id == bid))) == []
            cust_row = db.scalar(select(User).where(User.mobile == "9000000004"))
            ghost = Booking(partner_id="ghost-partner", customer_id=cust_row.id,
                            address_id="a", pincode="682001", category_id="c",
                            service_date=date.today(), slot="morning",
                            status="assigned",
                            quoted_amount=Decimal("100.00"))
            db.add(ghost)
            db.commit()
            gid = ghost.id
        finally:
            db.close()
        done = client.post(f"/v1/bookings/{gid}/complete", headers=h_o, json={}).json()
        assert done["status"] == "completed"  # zero commission, no crash


def test_accept_loses_race_deterministically(capsys):
    from fastapi import HTTPException

    from app.api.bookings import accept_booking

    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        sp = _login(client, capsys, "9000000003")
        owner = _login(client, capsys, "9000000002")
        h_c = _headers(cust["token"])
        h_f, fresh = _fresh_sp(client, capsys, owner["user"]["partner_id"])
        bid, _ = _book(client, h_c, next(_days))
        stale_db = SessionLocal()
        try:
            cached = stale_db.get(Booking, bid)
            assert cached.status == "open"
            racer = stale_db.get(User, fresh["user"]["id"])
            assert client.post(f"/v1/bookings/{bid}/accept",
                               headers=_headers(sp["token"])).status_code == 200
            # Pin the stale in-memory state: the status check reads this while
            # the guarded UPDATE below reads committed DB state (assigned).
            cached.status = "open"
            with pytest.raises(HTTPException) as ei:
                accept_booking(bid, racer, stale_db)
            assert (ei.value.status_code, ei.value.detail) == (409, "already_taken")
        finally:
            stale_db.close()


def test_force_assign_loses_race_deterministically(capsys):
    from fastapi import HTTPException

    from app.api.bookings import ForceAssignBody, force_assign_booking
    from tests.test_force_assign import _onboard_sp

    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        sp = _login(client, capsys, "9000000003")
        owner = _login(client, capsys, "9000000002")
        h_c, h_s, h_o = (_headers(cust["token"]), _headers(sp["token"]),
                         _headers(owner["token"]))
        owner_pid = client.get("/v1/partners/me", headers=h_o).json()["id"]
        seed_cat, _ = _seed_cat(client)
        sp_id = _onboard_sp(client, capsys, h_o, "9194770001", owner_pid, seed_cat)
        try:
            bid, _ = _book(client, h_c, next(_days))
            db = SessionLocal()
            try:
                db.get(Booking, bid).dispatch_refresh_count = 2
                db.commit()
            finally:
                db.close()
            stale_db = SessionLocal()
            try:
                cached = stale_db.get(Booking, bid)
                assert cached.status == "open"
                staff = stale_db.get(User, owner["user"]["id"])
                assert client.post(f"/v1/bookings/{bid}/accept",
                                   headers=h_s).status_code == 200
                # Pin the stale in-memory state: the guards read this while the
                # guarded UPDATE below reads committed DB state (assigned).
                cached.status = "open"
                with pytest.raises(HTTPException) as ei:
                    force_assign_booking(bid, ForceAssignBody(service_partner_id=sp_id),
                                         staff, stale_db)
                assert (ei.value.status_code, ei.value.detail) == (409, "already_taken")
            finally:
                stale_db.close()
        finally:
            # Restore the baseline world: later tests assume only the seed SP
            # is pool-eligible, so retire this one from eligibility.
            from app.models import ServicePartnerProfile

            db = SessionLocal()
            try:
                prof = db.get(ServicePartnerProfile, sp_id)
                if prof is not None:
                    prof.kyc_status = "pending_partner_verification"
                    db.commit()
            finally:
                db.close()


def test_cancel_matrix(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        sp = _login(client, capsys, "9000000003")
        owner = _login(client, capsys, "9000000002")
        master = _login(client, capsys, "9000000001")
        h_c, h_s, h_o, h_m = (_headers(cust["token"]), _headers(sp["token"]),
                              _headers(owner["token"]), _headers(master["token"]))
        assert client.post("/v1/bookings/nope/cancel", headers=h_c).status_code == 404
        bid, _ = _book(client, h_c, next(_days))
        reg = _login(client, capsys, f"9195{next(_days):06d}", "register",
                     full_name="S", role="customer")
        r = client.post(f"/v1/bookings/{bid}/cancel",
                        headers=_headers(reg["token"]))
        assert r.status_code == 403
        assert client.post(f"/v1/bookings/{bid}/cancel",
                           headers=h_c).json()["status"] == "cancelled"
        for h in (h_s, h_o, h_m):
            other, _ = _book(client, h_c, next(_days))
            assert client.post(f"/v1/bookings/{other}/cancel",
                               headers=h).json()["status"] == "cancelled"
