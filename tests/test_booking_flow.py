from datetime import date, timedelta

from tests.conftest import make_client


def _login(client, capsys, mobile, purpose="login", **reg):
    client.post("/v1/otp/request", json={"mobile": mobile, "purpose": purpose})
    printed = capsys.readouterr().out
    code = [p for p in printed.split() if p.startswith("code=")][-1].split("=", 1)[1]
    body = {"mobile": mobile, "purpose": purpose, "code": code, **reg}
    r = client.post("/v1/otp/verify", json=body)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def test_booking_first_accept_and_slot_rules(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        sp = _login(client, capsys, "9000000003")
        h_c = {"Authorization": f"Bearer {cust}"}
        h_s = {"Authorization": f"Bearer {sp}"}

        cats = client.get("/v1/categories").json()
        featured = [c for c in cats if c.get("featured_rank")]
        cat = featured[0]
        issues = [p["id"] for p in cat["problems"] if p.get("featured_rank")][:2]

        addr = client.post(
            "/v1/addresses",
            headers=h_c,
            json={"label": "home", "line1": "12 Palm Street", "pincode": "682001", "is_default": True},
        )
        assert addr.status_code == 200, addr.text
        too_soon = client.post(
            "/v1/bookings",
            headers=h_c,
            json={
                "address_id": addr.json()["id"],
                "category_id": cat["id"],
                "issue_template_ids": issues,
                "service_date": date.today().isoformat(),
                "slot": "morning",
            },
        )
        assert too_soon.status_code == 400

        when = (date.today() + timedelta(days=3)).isoformat()
        created = client.post(
            "/v1/bookings",
            headers=h_c,
            json={
                "address_id": addr.json()["id"],
                "category_id": cat["id"],
                "issue_template_ids": issues,
                "service_date": when,
                "slot": "morning",
            },
        )
        assert created.status_code == 200, created.text
        bid = created.json()["id"]

        offers = client.get("/v1/offers", headers=h_s)
        assert offers.status_code == 200
        assert any(o["id"] == bid for o in offers.json())

        acc = client.post(f"/v1/bookings/{bid}/accept", headers=h_s)
        assert acc.status_code == 200, acc.text
        assert acc.json()["status"] == "assigned"

        acc2 = client.post(f"/v1/bookings/{bid}/accept", headers=h_s)
        assert acc2.status_code == 409

        analytics = client.get("/v1/analytics", headers=h_s)
        assert analytics.status_code == 200
        assert "gmv_note" in analytics.json()
