"""Unit tests for technician profile, KYC, roster, schedule, earnings, payouts."""

import itertools
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.db import SessionLocal
from app.models import (
    AvailabilityBlock,
    Booking,
    Partner,
    PayoutLedger,
    ServicePartnerProfile,
    User,
)
from tests.conftest import make_client
from tests.test_force_assign import _login

_mobiles = itertools.count(9192000001)


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _seed_ids(client, owner_token):
    me = client.get("/v1/partners/me", headers=_headers(owner_token)).json()
    cats = client.get("/v1/categories").json()
    cat = [c for c in cats if c.get("featured_rank")][0]
    return me["id"], cat["id"]


def test_profile_get_and_missing(capsys):
    with make_client() as client:
        sp = _login(client, capsys, "9000000003")
        h_s = _headers(sp["token"])
        body = client.get("/v1/sp/profile", headers=h_s).json()
        assert set(body) == {"kyc_status", "pincodes", "category_ids",
                             "aadhaar_document_id", "police_document_id"}
        cust = _login(client, capsys, "9000000004")
        assert client.get("/v1/sp/profile",
                          headers=_headers(cust["token"])).status_code == 403
        db = SessionLocal()
        try:
            ghost = User(role="service_partner", full_name="G",
                         mobile=str(next(_mobiles)), email="", status="active")
            db.add(ghost)
            db.commit()
            gid = ghost.id
        finally:
            db.close()
        from app.services.tokens import issue_token
        h_g = _headers(issue_token(user_id=gid, role="service_partner",
                                   partner_id=None))
        r = client.get("/v1/sp/profile", headers=h_g)
        assert r.status_code == 404
        assert r.json() == {"detail": "no_profile"}
        r = client.put("/v1/sp/profile", headers=h_g,
                       json={"pincodes": [], "category_ids": []})
        assert r.json() == {"detail": "no_profile"}


def test_profile_put_validates_replaces_and_links_docs(capsys):
    with make_client() as client:
        sp = _login(client, capsys, "9000000003")
        owner = _login(client, capsys, "9000000002")
        h_s, h_o = _headers(sp["token"]), _headers(owner["token"])
        _, cat_id = _seed_ids(client, owner["token"])
        r = client.put("/v1/sp/profile", headers=h_s,
                       json={"pincodes": ["695001"], "category_ids": [cat_id]})
        assert r.status_code == 400
        assert r.json()["detail"].startswith("pincode_not_in_territory")
        first = client.put("/v1/sp/profile", headers=h_s, json={
            "pincodes": ["682001", "682011"], "category_ids": [cat_id],
            "aadhaar_path": "s3://aadhaar", "police_path": "s3://police"}).json()
        assert first["kyc_status"] == "pending_partner_verification"
        assert first["aadhaar_document_id"] and first["police_document_id"]
        second = client.put("/v1/sp/profile", headers=h_s, json={
            "pincodes": ["682001"], "category_ids": [cat_id]}).json()
        assert second["pincodes"] == ["682001"]  # replaced, not merged


def test_roster_lists_tenant_with_states(capsys):
    with make_client() as client:
        owner = _login(client, capsys, "9000000002")
        cust = _login(client, capsys, "9000000004")
        h_o = _headers(owner["token"])
        assert client.get("/v1/sp/roster", headers=_headers(cust["token"])).status_code == 403
        rows = client.get("/v1/sp/roster", headers=h_o).json()
        by_mobile = {r["mobile"]: r for r in rows}
        assert by_mobile["9000000003"]["kyc_status"] in (
            "approved", "pending_partner_verification")
        assert set(rows[0]) == {"id", "full_name", "mobile", "kyc_status", "status"}
        db = SessionLocal()
        try:
            pid = by_mobile["9000000003"]["id"]
            me = client.get("/v1/partners/me", headers=h_o).json()
            orphan = User(role="service_partner", partner_id=me["id"],
                          full_name="Orphan", mobile=str(next(_mobiles)),
                          email="", status="active")
            db.add(orphan)
            db.commit()
            orphan_mobile = orphan.mobile
        finally:
            db.close()
        rows = client.get("/v1/sp/roster", headers=h_o).json()
        assert [r for r in rows if r["mobile"] == orphan_mobile][0]["kyc_status"] == "missing"


def test_kyc_review_gates(capsys):
    with make_client() as client:
        owner = _login(client, capsys, "9000000002")
        sp = _login(client, capsys, "9000000003")
        h_o = _headers(owner["token"])
        r = client.post("/v1/sp/00000000-0000-0000-0000-000000000000/kyc",
                        headers=h_o, json={"status": "approved"})
        assert r.status_code == 404
        r = client.post(f"/v1/sp/{sp['user']['id']}/kyc", headers=h_o,
                        json={"status": "maybe"})
        assert r.status_code == 400
        assert r.json() == {"detail": "bad_status"}
        r = client.post(f"/v1/sp/{sp['user']['id']}/kyc",
                        headers=_headers(sp["token"]), json={"status": "approved"})
        assert r.status_code == 403
        db = SessionLocal()
        try:
            p2 = Partner(trade_name="KYC Other", status="approved")
            db.add(p2)
            db.flush()
            outsider = User(role="service_partner", partner_id=p2.id,
                            full_name="Out", mobile=str(next(_mobiles)),
                            email="", status="active")
            db.add(outsider)
            db.flush()
            db.add(ServicePartnerProfile(user_id=outsider.id, partner_id=p2.id,
                                         kyc_status="pending_partner_verification"))
            db.commit()
            oid = outsider.id
        finally:
            db.close()
        r = client.post(f"/v1/sp/{oid}/kyc", headers=h_o, json={"status": "approved"})
        assert r.status_code == 404
        for status in ("rejected", "approved"):
            r = client.post(f"/v1/sp/{sp['user']['id']}/kyc", headers=h_o,
                            json={"status": status})
            assert r.json() == {"user_id": sp["user"]["id"], "kyc_status": status}


def test_availability_roundtrip(capsys):
    with make_client() as client:
        sp = _login(client, capsys, "9000000003")
        cust = _login(client, capsys, "9000000004")
        h_s = _headers(sp["token"])
        assert client.post("/v1/sp/availability", headers=_headers(cust["token"]),
                           json={"block_date": "2027-02-01"}).status_code == 403
        day = (date.today() + timedelta(days=40)).isoformat()
        r = client.post("/v1/sp/availability", headers=h_s,
                        json={"block_date": day, "slot": "morning"})
        assert r.status_code == 200 and r.json()["id"]
        r = client.post("/v1/sp/availability", headers=h_s,
                        json={"block_date": day})
        assert r.status_code == 200
        rows = client.get("/v1/sp/availability", headers=h_s).json()
        mine = [x for x in rows if x["block_date"] == day]
        assert {x["slot"] for x in mine} == {"morning", None}


def test_schedule_buckets_and_default_day(capsys):
    with make_client() as client:
        sp = _login(client, capsys, "9000000003")
        h_s = _headers(sp["token"])
        day = date.today() + timedelta(days=41)
        db = SessionLocal()
        try:
            cust = db.scalar(select(User).where(User.mobile == "9000000004"))
            mk = lambda slot, status, pin: Booking(
                partner_id=sp["user"]["partner_id"], customer_id=cust.id,
                address_id="a", pincode=pin, category_id="c",
                service_date=day, slot=slot, status=status,
                assigned_sp_id=sp["user"]["id"])
            db.add(mk("morning", "assigned", "682011"))
            db.add(mk("morning", "en_route", "682001"))
            db.add(mk("evening", "in_progress", "682001"))
            db.add(mk("morning", "completed", "682001"))
            db.add(mk("morning", "cancelled", "682001"))
            db.commit()
        finally:
            db.close()
        body = client.get(f"/v1/sp/schedule?on={day.isoformat()}", headers=h_s).json()
        assert body["date"] == day.isoformat()
        assert [b["pincode"] for b in body["morning"]] == ["682001", "682011"]
        assert [b["status"] for b in body["morning"]] == ["en_route", "assigned"]
        assert len(body["evening"]) == 1
        assert set(body["morning"][0]) == {"id", "pincode", "status", "category_id"}
        default = client.get("/v1/sp/schedule", headers=h_s).json()
        assert default["date"] == (date.today() + timedelta(days=1)).isoformat()


def test_earnings_sums_and_mark_paid(capsys):
    with make_client() as client:
        sp = _login(client, capsys, "9000000003")
        owner = _login(client, capsys, "9000000002")
        h_s, h_o = _headers(sp["token"]), _headers(owner["token"])
        assert client.get("/v1/sp/earnings", headers=h_o).status_code == 403
        before = client.get("/v1/sp/earnings", headers=h_s).json()
        db = SessionLocal()
        try:
            pid = sp["user"]["partner_id"]
            rows = [
                PayoutLedger(partner_id=pid, service_partner_id=sp["user"]["id"],
                             booking_id=f"b{i}", amount=Decimal(v), status=st)
                for i, (v, st) in enumerate(
                    (("100.00", "pending"), ("50.00", "pending"), ("25.00", "paid")))
            ]
            db.add_all(rows)
            db.commit()
            ids = [r.id for r in rows]
        finally:
            db.close()
        earn = client.get("/v1/sp/earnings", headers=h_s).json()
        assert Decimal(earn["pending"]) - Decimal(before["pending"]) == Decimal("150.00")
        assert Decimal(earn["paid"]) - Decimal(before["paid"]) == Decimal("25.00")
        assert earn["jobs"] - before["jobs"] == 3
        r = client.post(f"/v1/payouts/{ids[0]}/paid", headers=h_s)
        assert r.status_code == 403
        r = client.post("/v1/payouts/00000000-0000-0000-0000-000000000000/paid",
                        headers=h_o)
        assert r.status_code == 404
        r = client.post(f"/v1/payouts/{ids[0]}/paid", headers=h_o)
        assert r.json() == {"id": ids[0], "status": "paid"}
        earn = client.get("/v1/sp/earnings", headers=h_s).json()
        assert Decimal(earn["pending"]) - Decimal(before["pending"]) == Decimal("50.00")
        assert Decimal(earn["paid"]) - Decimal(before["paid"]) == Decimal("125.00")
