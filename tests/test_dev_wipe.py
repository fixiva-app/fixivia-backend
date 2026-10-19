"""DEV wipe endpoint: case-seeded users + bookings are removed with
their dependents; dev accounts are protected; unknown ids are skipped."""

from datetime import date, timedelta

from tests.conftest import make_client


def _register(client, mobile, **extra):
    req = client.post("/v1/otp/request", json={"mobile": mobile, "purpose": "register"})
    assert req.status_code == 200, req.text
    code = client.get("/v1/dev/otp-code", params={"mobile": mobile, "purpose": "register"})
    assert code.status_code == 200, code.text
    verify = client.post(
        "/v1/otp/verify",
        json={"mobile": mobile, "purpose": "register",
              "code": code.json()["code"], **extra},
    )
    assert verify.status_code == 200, verify.text
    return verify.json()


def test_wipe_removes_user_booking_and_dependents():
    with make_client() as client:
        seed = client.post("/v1/dev/inject-users")
        assert seed.status_code == 200, seed.text
        owner = next(a for a in seed.json()["accounts"]
                     if a["user"]["role"] == "partner_owner")
        master = next(a for a in seed.json()["accounts"]
                      if a["user"]["role"] == "master_admin")
        cust = _register(client, "9199999001", full_name="Wipe Me", role="customer")
        token = cust["token"]
        addr = client.post(
            "/v1/addresses",
            json={"label": "home", "line1": "1 Wipe St", "pincode": "682001",
                  "is_default": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert addr.status_code == 200, addr.text
        cats = client.get("/v1/categories")
        cat = next(c for c in cats.json() if c["name_en"] == "AC mechanic")
        issues = [p["id"] for p in cat["problems"] if p.get("featured_rank")][:2]
        booking = client.post(
            "/v1/bookings",
            json={"address_id": addr.json()["id"], "category_id": cat["id"],
                  "issue_template_ids": issues,
                  "service_date": (date.today() + timedelta(days=2)).isoformat(),
                  "slot": "morning"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert booking.status_code == 200, booking.text
        bid = booking.json()["id"]

        wiped = client.request(
            "DELETE", "/v1/dev/test-entities",
            json={"user_mobiles": ["9199999001"], "booking_ids": [bid]},
        )
        assert wiped.status_code == 200, wiped.text
        deleted = wiped.json()["deleted"]
        assert deleted["bookings"] == 1
        assert deleted["users"] == 1
        assert deleted["addresses"] == 1
        assert deleted["booking_offers"] >= 1

        # Gone: booking detail 404s, wiped user's token is dead.
        gone = client.get(f"/v1/bookings/{bid}",
                          headers={"Authorization": f"Bearer {master['token']}"})
        assert gone.status_code == 404
        dead = client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
        assert dead.status_code == 401
        assert dead.json()["detail"] == "user_inactive"

        # Dev accounts untouched.
        me = client.get("/v1/me",
                        headers={"Authorization": f"Bearer {owner['token']}"})
        assert me.status_code == 200, me.text


def test_wipe_protects_dev_users_and_skips_unknown():
    with make_client() as client:
        seed = client.post("/v1/dev/inject-users")
        assert seed.status_code == 200, seed.text
        blocked = client.request(
            "DELETE", "/v1/dev/test-entities",
            json={"user_mobiles": ["9000000004"], "booking_ids": []},
        )
        assert blocked.status_code == 400
        assert blocked.json()["detail"] == "dev_user_protected"

        skipped = client.request(
            "DELETE", "/v1/dev/test-entities",
            json={"user_mobiles": ["9100000000"], "booking_ids": ["no-such-id"]},
        )
        assert skipped.status_code == 200, skipped.text
        assert skipped.json()["deleted"]["users"] == 0
        assert skipped.json()["deleted"]["bookings"] == 0
