"""Unit tests for partner onboarding, review, territory, and admin requests."""

import itertools
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db import SessionLocal
from app.models import PartnerInvite, User
from tests.conftest import make_client
from tests.test_force_assign import _login

_names = itertools.count(1)
_mobiles = itertools.count(9191000001)


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _invite(client, master_token):
    r = client.post("/v1/partners/invites", headers=_headers(master_token))
    assert r.status_code == 200, r.text
    return r.json()


def _apply(client, token, pin="673001"):
    n = next(_names)
    return client.post("/v1/partners/apply", json={
        "invite_token": token, "trade_name": f"Unit P{n}",
        "office_pincode": pin, "personal_email": f"u{n}@x.io"})


def test_invite_master_only_and_shape(capsys):
    with make_client() as client:
        for mobile in ("9000000004", "9000000002"):
            who = _login(client, capsys, mobile)
            r = client.post("/v1/partners/invites", headers=_headers(who["token"]))
            assert r.status_code == 403, mobile
        master = _login(client, capsys, "9000000001")
        inv = _invite(client, master["token"])
        assert set(inv) == {"id", "token", "expires_at"}
        assert len(inv["token"]) == 12


def test_apply_gates(capsys):
    with make_client() as client:
        master = _login(client, capsys, "9000000001")
        r = client.post("/v1/partners/apply", json={
            "invite_token": "bogus", "trade_name": "X",
            "office_pincode": "673001", "personal_email": "x@x.io"})
        assert r.json() == {"detail": "invite_invalid"}
        inv = _invite(client, master["token"])
        db = SessionLocal()
        try:
            row = db.scalar(select(PartnerInvite).where(
                PartnerInvite.token_plain_dev == inv["token"]))
            row.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
            db.commit()
        finally:
            db.close()
        assert _apply(client, inv["token"]).json() == {"detail": "invite_invalid"}
        inv2 = _invite(client, master["token"])
        r = client.post("/v1/partners/apply", json={
            "invite_token": inv2["token"], "trade_name": "X",
            "office_pincode": "000000", "personal_email": "x@x.io"})
        assert r.json() == {"detail": "unknown_pincode"}
        ok = _apply(client, inv2["token"])
        assert ok.status_code == 200, ok.text
        assert ok.json()["status"] == "submitted"
        again = _apply(client, inv2["token"])
        assert again.status_code == 409
        assert again.json() == {"detail": "invite_used"}


def test_public_and_master_lists(capsys):
    with make_client() as client:
        pubs = client.get("/v1/partners/public").json()
        assert pubs and set(pubs[0]) == {"id", "trade_name"}
        cust = _login(client, capsys, "9000000004")
        r = client.get("/v1/partners", headers=_headers(cust["token"]))
        assert r.status_code == 403
        master = _login(client, capsys, "9000000001")
        rows = client.get("/v1/partners", headers=_headers(master["token"])).json()
        assert len(rows) >= len(pubs)
        assert rows[0]["pincodes"] == []  # list view omits territory


def test_partners_me_gates(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        r = client.get("/v1/partners/me", headers=_headers(cust["token"]))
        assert r.status_code == 400
        assert r.json() == {"detail": "no_partner"}
        owner = _login(client, capsys, "9000000002")
        me = client.get("/v1/partners/me", headers=_headers(owner["token"])).json()
        assert set(me["pincodes"]) >= {"682001", "682011"}
        # user pointing at a deleted partner
        db = SessionLocal()
        try:
            u = db.scalar(select(User).where(User.mobile == "9000000002"))
            real = u.partner_id
            u.partner_id = "00000000-0000-0000-0000-000000000000"
            db.commit()
        finally:
            db.close()
        try:
            r = client.get("/v1/partners/me", headers=_headers(owner["token"]))
            assert r.status_code == 404
        finally:
            db = SessionLocal()
            try:
                u = db.scalar(select(User).where(User.mobile == "9000000002"))
                u.partner_id = real
                db.commit()
            finally:
                db.close()


def test_review_flow_and_gates(capsys):
    with make_client() as client:
        master = _login(client, capsys, "9000000001")
        owner = _login(client, capsys, "9000000002")
        h_m, h_o = _headers(master["token"]), _headers(owner["token"])
        r = client.post("/v1/partners/00000000-0000-0000-0000-000000000000/review",
                        headers=h_m, json={"status": "approved"})
        assert r.status_code == 404
        r = client.post("/v1/partners/00000000-0000-0000-0000-000000000000/review",
                        headers=h_o, json={"status": "approved"})
        assert r.status_code == 403
        inv = _invite(client, master["token"])
        pid = _apply(client, inv["token"]).json()["partner_id"]
        r = client.post(f"/v1/partners/{pid}/review", headers=h_m,
                        json={"status": "maybe"})
        assert r.status_code == 400
        assert r.json() == {"detail": "bad_status"}
        r = client.post(f"/v1/partners/{pid}/review", headers=h_m,
                        json={"status": "under_review"})
        assert r.json()["status"] == "under_review"
        try:
            r = client.post(f"/v1/partners/{pid}/review", headers=h_m, json={
                "status": "approved", "pincodes": ["695001"],
                "license_fee_amount": "20000", "commission_percent": "12.5"})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["pincodes"] == ["695001"]
            assert body["license_fee_amount"] == "20000"
            assert body["commission_percent"] == "12.5"
        finally:
            client.post(f"/v1/partners/{pid}/review", headers=h_m,
                        json={"status": "approved", "pincodes": []})
        r = client.post(f"/v1/partners/{pid}/review", headers=h_m,
                        json={"status": "suspended"})
        assert r.json()["status"] == "suspended"
        r = client.post(f"/v1/partners/{pid}/review", headers=h_m,
                        json={"status": "rejected"})
        assert r.json()["status"] == "rejected"


def test_assign_pincodes_validates(capsys):
    with make_client() as client:
        master = _login(client, capsys, "9000000001")
        h_m = _headers(master["token"])
        inv = _invite(client, master["token"])
        pid = _apply(client, inv["token"]).json()["partner_id"]
        r = client.post(f"/v1/partners/{pid}/review", headers=h_m,
                        json={"status": "approved", "pincodes": ["000000"]})
        assert r.status_code == 400
        assert r.json()["detail"].startswith("unknown_pincode")
        r = client.post(f"/v1/partners/{pid}/review", headers=h_m,
                        json={"status": "approved", "pincodes": ["682001"]})
        assert r.status_code == 409
        assert r.json()["detail"].startswith("pincode_taken")


def test_admin_request_lifecycle(capsys):
    with make_client() as client:
        master = _login(client, capsys, "9000000001")
        owner = _login(client, capsys, "9000000002")
        cust = _login(client, capsys, "9000000004")
        h_m, h_o, h_c = (_headers(master["token"]), _headers(owner["token"]),
                         _headers(cust["token"]))
        mobile = str(next(_mobiles))
        r = client.post("/v1/partner-admin-requests", headers=h_c,
                        json={"full_name": "X", "mobile": mobile})
        assert r.status_code == 403
        created = client.post("/v1/partner-admin-requests", headers=h_o,
                              json={"full_name": "Unit Admin", "mobile": mobile,
                                    "email": "ua@x.io"}).json()
        assert created["status"] == "submitted"
        own = client.get("/v1/partner-admin-requests", headers=h_o).json()
        assert created["id"] in [x["id"] for x in own]
        assert all(x["partner_id"] == owner["user"]["partner_id"] for x in own)
        all_rows = client.get("/v1/partner-admin-requests", headers=h_m).json()
        assert created["id"] in [x["id"] for x in all_rows]
        assert client.get("/v1/partner-admin-requests",
                          headers=h_c).status_code == 403
        r = client.post(f"/v1/partner-admin-requests/{created['id']}/review",
                        headers=h_o, json={"status": "approved"})
        assert r.status_code == 403
        r = client.post("/v1/partner-admin-requests/00000000-0000-0000-0000-000000000000/review",
                        headers=h_m, json={"status": "approved"})
        assert r.status_code == 404
        r = client.post(f"/v1/partner-admin-requests/{created['id']}/review",
                        headers=h_m, json={"status": "maybe"})
        assert r.status_code == 400
        rej = client.post(f"/v1/partner-admin-requests/{created['id']}/review",
                          headers=h_m, json={"status": "rejected"}).json()
        assert rej["status"] == "rejected" and rej["created_user_id"] is None
        mobile2 = str(next(_mobiles))
        created2 = client.post("/v1/partner-admin-requests", headers=h_o,
                               json={"full_name": "Unit Admin2",
                                     "mobile": mobile2}).json()
        ok = client.post(f"/v1/partner-admin-requests/{created2['id']}/review",
                         headers=h_m, json={"status": "approved"}).json()
        assert ok["status"] == "approved" and ok["created_user_id"]
        db = SessionLocal()
        try:
            admin = db.get(User, ok["created_user_id"])
            assert admin.role == "partner_admin"
            assert admin.partner_id == owner["user"]["partner_id"]
        finally:
            db.close()
        dupe = client.post("/v1/partner-admin-requests", headers=h_o,
                           json={"full_name": "Dupe", "mobile": "9000000004"}).json()
        r = client.post(f"/v1/partner-admin-requests/{dupe['id']}/review",
                        headers=h_m, json={"status": "approved"})
        assert r.status_code == 409
        assert r.json() == {"detail": "mobile_taken"}


def test_pincodes_sorted(capsys):
    with make_client() as client:
        pins = client.get("/v1/pincodes").json()
        codes = [p["pincode"] for p in pins]
        assert codes == sorted(codes)
        assert {"682001", "682011", "695001"} <= set(codes)
        assert set(pins[0]) == {"pincode", "district", "locality", "state"}
