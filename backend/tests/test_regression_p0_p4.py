"""Regression tests for the full-suite triage fixes (P0-P4)."""
from datetime import date, timedelta

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import CommitRoute, SessionLocal
from app.models import BookingExclusion, BookingOffer, Partner
from tests.conftest import make_client


def _login(client, capsys, mobile, purpose="login", **reg):
    client.post("/v1/otp/request", json={"mobile": mobile, "purpose": purpose})
    printed = capsys.readouterr().out
    code = [p for p in printed.split() if p.startswith("code=")][-1].split("=", 1)[1]
    body = {"mobile": mobile, "purpose": purpose, "code": code, **reg}
    r = client.post("/v1/otp/verify", json=body)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _tokens(client):
    res = client.post("/v1/dev/inject-users")
    assert res.status_code == 200, res.text
    return {a["role"]: a["token"] for a in res.json()["accounts"]}


def _me_id(client, token):
    me = client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    return me.json()["id"]


def _invite(client, master_h):
    inv = client.post("/v1/partners/invites", headers=master_h)
    assert inv.status_code == 200, inv.text
    return inv.json()["token"]


def _apply(client, token, trade="Reg Trade"):
    return client.post(
        "/v1/partners/apply",
        json={
            "invite_token": token,
            "trade_name": trade,
            "office_pincode": "682001",
            "personal_email": "owner@reg.io",
        },
    )


# P0: the route commits on success and rolls back on error.
def test_commit_route_commits_and_rolls_back():
    calls = []

    class FakeSession:
        def commit(self):
            calls.append("commit")

        def rollback(self):
            calls.append("rollback")

    def _dep(request: Request):
        request.state._db_session = FakeSession()
        yield

    app = FastAPI()
    app.router.route_class = CommitRoute

    @app.get("/ok", dependencies=[Depends(_dep)])
    def ok():
        return {"ok": True}

    @app.get("/boom", dependencies=[Depends(_dep)])
    def boom():
        raise HTTPException(400, "x")

    c = TestClient(app)
    assert c.get("/ok").status_code == 200
    assert calls == ["commit"]
    assert c.get("/boom").status_code == 400
    assert calls == ["commit", "rollback"]


# P0: every API router commits before responding.
def test_all_routers_use_commit_route():
    from app.api import analytics, auth, bookings, catalog, dev, health, me, partners, technicians

    for mod in (analytics, auth, bookings, catalog, dev, health, me, partners, technicians):
        assert mod.router.routes, mod.__name__
        for route in mod.router.routes:
            assert isinstance(route, CommitRoute), f"{mod.__name__} {route.path}"


# P1: invite -> apply no longer 500s on naive/aware datetimes.
def test_partner_apply_roundtrip(capsys):
    with make_client() as client:
        toks = _tokens(client)
        master_h = {"Authorization": f"Bearer {toks['master_admin']}"}
        res = _apply(client, _invite(client, master_h), "Reg P1")
        assert res.status_code == 200, res.text
        assert res.json()["partner_id"]
        dup = _apply(client, _invite(client, master_h), "Reg P1")
        assert dup.status_code == 200  # fresh invite still usable


# P2: a consumed invite mints the partner's owner login; fresh invites cannot.
def test_owner_register_links_consumed_invite(capsys):
    with make_client() as client:
        toks = _tokens(client)
        master_h = {"Authorization": f"Bearer {toks['master_admin']}"}
        token = _invite(client, master_h)
        pid = _apply(client, token, "Reg P2").json()["partner_id"]
        owner = _login(
            client, capsys, "919000001101", purpose="register",
            role="partner_owner", invite_token=token,
        )
        me = client.get("/v1/me", headers={"Authorization": f"Bearer {owner}"})
        assert me.status_code == 200
        assert me.json()["partner_id"] == pid

        fresh = _invite(client, master_h)
        client.post("/v1/otp/request", json={"mobile": "919000001102", "purpose": "register"})
        code = [p for p in capsys.readouterr().out.split() if p.startswith("code=")][-1].split("=", 1)[1]
        bad = client.post(
            "/v1/otp/verify",
            json={"mobile": "919000001102", "purpose": "register", "code": code,
                  "role": "partner_owner", "invite_token": fresh},
        )
        assert bad.status_code == 400, bad.text
        assert bad.json()["detail"] == "apply_first"


# P3: declined/dropped bookings stay out of the SP's offer surfaces.
def test_decliner_hidden_from_offers_and_list(capsys):
    with make_client() as client:
        toks = _tokens(client)
        sp_token = toks["service_partner"]
        sp_id = _me_id(client, sp_token)
        cust_token = toks["customer"]
        h_c = {"Authorization": f"Bearer {cust_token}"}
        h_s = {"Authorization": f"Bearer {sp_token}"}
        cat = client.get("/v1/categories").json()[0]
        issues = [p["id"] for p in cat["problems"][:1]]
        addr = client.post(
            "/v1/addresses", headers=h_c,
            json={"label": "home", "line1": "1 Main", "pincode": "682001"},
        ).json()["id"]
        when = (date.today() + timedelta(days=4)).isoformat()

        def _mk():
            r = client.post(
                "/v1/bookings", headers=h_c,
                json={"address_id": addr, "category_id": cat["id"],
                      "issue_template_ids": issues, "service_date": when, "slot": "morning"},
            )
            assert r.status_code == 200, r.text
            return r.json()["id"]

        declined_bid, open_bid = _mk(), _mk()
        db = SessionLocal()
        try:
            db.merge(BookingOffer(booking_id=declined_bid, service_partner_id=sp_id))
            db.merge(BookingExclusion(booking_id=declined_bid, service_partner_id=sp_id, reason="declined"))
            db.merge(BookingOffer(booking_id=open_bid, service_partner_id=sp_id))
            db.commit()
        finally:
            db.close()
        offers = client.get("/v1/offers", headers=h_s)
        assert offers.status_code == 200
        ids = [o["id"] for o in offers.json()]
        assert open_bid in ids
        assert declined_bid not in ids
        listed = client.get("/v1/bookings", headers=h_s)
        assert listed.status_code == 200
        ids = [b["id"] for b in listed.json()]
        assert open_bid in ids
        assert declined_bid not in ids


# P4: category write responses echo the stored problems.
def test_category_write_echoes_problems(capsys):
    with make_client() as client:
        toks = _tokens(client)
        h = {"Authorization": f"Bearer {toks['master_admin']}"}
        created = client.post(
            "/v1/categories", headers=h,
            json={"slug": "reg-p4-cat", "name_en": "Reg P4", "problems": [{"text_en": "P1"}]},
        )
        assert created.status_code == 200, created.text
        assert [p["text_en"] for p in created.json()["problems"]] == ["P1"]
        updated = client.put(
            f"/v1/categories/{created.json()['id']}", headers=h,
            json={"slug": "reg-p4-cat", "name_en": "Reg P4", "problems": [{"text_en": "P2"}]},
        )
        assert updated.status_code == 200, updated.text
        assert [p["text_en"] for p in updated.json()["problems"]] == ["P2"]


# P4: SP profile write responses echo the stored pins and categories.
def test_sp_profile_put_echoes_pins_and_cats(capsys):
    with make_client() as client:
        _tokens(client)
        db = SessionLocal()
        try:
            pid = db.scalar(select(Partner).where(Partner.status == "approved").limit(1)).id
        finally:
            db.close()
        cat = client.get("/v1/categories").json()[0]
        sp = _login(
            client, capsys, "919000001103", purpose="register",
            role="service_partner", partner_id=pid,
        )
        res = client.put(
            "/v1/sp/profile", headers={"Authorization": f"Bearer {sp}"},
            json={"pincodes": ["682001"], "category_ids": [cat["id"]]},
        )
        assert res.status_code == 200, res.text
        assert res.json()["pincodes"] == ["682001"]
        assert res.json()["category_ids"] == [cat["id"]]
