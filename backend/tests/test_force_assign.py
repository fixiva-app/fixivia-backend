from datetime import date, timedelta

from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditLog
from tests.conftest import make_client


def _login(client, capsys, mobile, purpose="login", **reg):
    client.post("/v1/otp/request", json={"mobile": mobile, "purpose": purpose})
    printed = capsys.readouterr().out
    code = [p for p in printed.split() if p.startswith("code=")][-1].split("=", 1)[1]
    body = {"mobile": mobile, "purpose": purpose, "code": code, **reg}
    r = client.post("/v1/otp/verify", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _book(client, h_c, days_ahead):
    cats = client.get("/v1/categories").json()
    cat = [c for c in cats if c.get("featured_rank")][0]
    issues = [p["id"] for p in cat["problems"] if p.get("featured_rank")][:2]
    addr = client.post(
        "/v1/addresses",
        headers=h_c,
        json={"label": "home", "line1": "12 Palm Street", "pincode": "682001", "is_default": True},
    )
    assert addr.status_code == 200, addr.text
    created = client.post(
        "/v1/bookings",
        headers=h_c,
        json={
            "address_id": addr.json()["id"],
            "category_id": cat["id"],
            "issue_template_ids": issues,
            "service_date": (date.today() + timedelta(days=days_ahead)).isoformat(),
            "slot": "morning",
        },
    )
    assert created.status_code == 200, created.text
    return created.json()["id"], cat["id"]


def _onboard_sp(client, capsys, h_owner, mobile, partner_id, category_id):
    reg = _login(
        client,
        capsys,
        mobile,
        "register",
        full_name="Second Tech",
        role="service_partner",
        partner_id=partner_id,
    )
    h_sp = {"Authorization": f"Bearer {reg['token']}"}
    prof = client.put(
        "/v1/sp/profile",
        headers=h_sp,
        json={"pincodes": ["682001"], "category_ids": [category_id]},
    )
    assert prof.status_code == 200, prof.text
    kyc = client.post(f"/v1/sp/{reg['user']['id']}/kyc", headers=h_owner, json={"status": "approved"})
    assert kyc.status_code == 200, kyc.text
    return reg["user"]["id"]


def _types(client, headers, booking_id):
    notes = client.get("/v1/notifications", headers=headers).json()
    return [n["type"] for n in notes if n["booking_id"] == booking_id]


def test_force_assign_after_failed_cycle(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        owner = _login(client, capsys, "9000000002")
        master = _login(client, capsys, "9000000001")
        h_c = {"Authorization": f"Bearer {cust['token']}"}
        h_o = {"Authorization": f"Bearer {owner['token']}"}
        h_m = {"Authorization": f"Bearer {master['token']}"}

        bid, _ = _book(client, h_c, 4)

        early = client.post(f"/v1/bookings/{bid}/force-assign", headers=h_o, json={"service_partner_id": "x"})
        assert early.status_code == 409
        assert early.json() == {"detail": "too_early"}

        pre = client.get(f"/v1/bookings/{bid}/assignable", headers=h_o)
        assert pre.status_code == 200
        assert pre.json()["ready"] is False
        assert pre.json()["reason"] == "too_early"

        repooled = client.post("/v1/jobs/dispatch-repool", headers=h_m)
        assert repooled.status_code == 200

        ready = client.get(f"/v1/bookings/{bid}/assignable", headers=h_o)
        assert ready.status_code == 200, ready.text
        assert ready.json()["ready"] is True
        assert ready.json()["technicians"], "seed SP should be assignable"
        sp_id = ready.json()["technicians"][0]["id"]

        capsys.readouterr()
        done = client.post(f"/v1/bookings/{bid}/force-assign", headers=h_o, json={"service_partner_id": sp_id})
        assert done.status_code == 200, done.text
        body = done.json()
        assert body["status"] == "assigned"
        assert body["assigned_sp_id"] == sp_id
        assert body["first_accepted_at"] is not None
        printed = capsys.readouterr().out
        assert "purpose=start_work" in printed
        assert "REUSE" not in printed

        assert "booking_confirmed" in _types(client, h_c, bid)
        assert "filled" in _types(client, h_o, bid)

        db = SessionLocal()
        try:
            rows = db.scalars(select(AuditLog).where(AuditLog.action == "force_assign", AuditLog.entity_id == bid)).all()
            assert len(rows) == 1
            assert rows[0].actor_user_id == owner["user"]["id"]
        finally:
            db.close()

        again = client.post(f"/v1/bookings/{bid}/force-assign", headers=h_o, json={"service_partner_id": sp_id})
        assert again.status_code == 409


def test_force_assign_rbac(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        sp = _login(client, capsys, "9000000003")
        master = _login(client, capsys, "9000000001")
        admin = _login(client, capsys, "9000000005")
        h_c = {"Authorization": f"Bearer {cust['token']}"}
        bid, _ = _book(client, h_c, 5)
        for token in (cust["token"], sp["token"], master["token"]):
            h = {"Authorization": f"Bearer {token}"}
            assert client.get(f"/v1/bookings/{bid}/assignable", headers=h).status_code == 403
            r = client.post(f"/v1/bookings/{bid}/force-assign", headers=h, json={"service_partner_id": "x"})
            assert r.status_code == 403
        # partner admin shares the fallback with the owner
        h_a = {"Authorization": f"Bearer {admin['token']}"}
        assert client.get(f"/v1/bookings/{bid}/assignable", headers=h_a).status_code == 200


def test_force_assign_decliner_stays_blocked(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        sp = _login(client, capsys, "9000000003")
        owner = _login(client, capsys, "9000000002")
        h_c = {"Authorization": f"Bearer {cust['token']}"}
        h_s = {"Authorization": f"Bearer {sp['token']}"}
        h_o = {"Authorization": f"Bearer {owner['token']}"}

        bid, _ = _book(client, h_c, 6)
        dec = client.post(f"/v1/bookings/{bid}/decline", headers=h_s)
        assert dec.status_code == 200

        state = client.get(f"/v1/bookings/{bid}/assignable", headers=h_o).json()
        assert state["ready"] is True
        assert state["reason"] == "pool_empty"
        assert state["technicians"] == []

        blocked = client.post(
            f"/v1/bookings/{bid}/force-assign", headers=h_o, json={"service_partner_id": sp["user"]["id"]}
        )
        assert blocked.status_code == 400


def test_force_assign_reuses_start_work_otp(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        sp = _login(client, capsys, "9000000003")
        owner = _login(client, capsys, "9000000002")
        master = _login(client, capsys, "9000000001")
        h_c = {"Authorization": f"Bearer {cust['token']}"}
        h_s = {"Authorization": f"Bearer {sp['token']}"}
        h_o = {"Authorization": f"Bearer {owner['token']}"}
        h_m = {"Authorization": f"Bearer {master['token']}"}

        bid, cat_id = _book(client, h_c, 7)
        partner_id = client.get("/v1/partners/me", headers=h_o).json()["id"]
        sp_b = _onboard_sp(client, capsys, h_o, "9112000001", partner_id, cat_id)

        acc = client.post(f"/v1/bookings/{bid}/accept", headers=h_s)
        assert acc.status_code == 200
        dropped = client.post(f"/v1/bookings/{bid}/drop", headers=h_o)
        assert dropped.status_code == 200
        assert dropped.json()["status"] == "open"
        # scheduler sweep: still open after another pool, so the fallback opens
        client.post("/v1/jobs/dispatch-repool", headers=h_m)

        capsys.readouterr()
        done = client.post(f"/v1/bookings/{bid}/force-assign", headers=h_o, json={"service_partner_id": sp_b})
        assert done.status_code == 200, done.text
        assert done.json()["assigned_sp_id"] == sp_b
        printed = capsys.readouterr().out
        assert "REUSE" in printed
        assert "booking_confirmed" in _types(client, h_c, bid)
