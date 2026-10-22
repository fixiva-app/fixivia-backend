"""Bucket 2: profile edit, mobile change, address delete, customer rating."""

from datetime import date

from app.db import SessionLocal
from app.models import Booking
from tests.conftest import make_client
from tests.test_bookings_api import _headers, _start_code
from tests.test_force_assign import _book, _login


def _last_code(capsys):
    printed = capsys.readouterr().out
    return [p for p in printed.split() if p.startswith("code=")][-1].split("=", 1)[1]


def _fresh_sp_here(client, capsys, partner_id, mobile):
    """Disposable SP with a fixed mobile.

    test_bookings_api._fresh_sp draws from a module-level counter, but
    tests/ has no __init__.py, so a cross-file import gets a second module
    object with a second counter starting at the same value: the two
    interleave and collide in full-suite runs. Fixed mobiles stay unique.
    """
    reg = _login(client, capsys, mobile, "register",
                 full_name="Fresh", role="service_partner",
                 partner_id=partner_id)
    return _headers(reg["token"]), reg


def test_patch_me_updates_name_and_email(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        h = _headers(cust["token"])
        r = client.patch("/v1/me", headers=h,
                         json={"full_name": "Renamed Rita",
                               "email": "rita@example.in"})
        assert r.status_code == 200, r.text
        assert (r.json()["full_name"], r.json()["email"]) == (
            "Renamed Rita", "rita@example.in")
        me = client.get("/v1/me", headers=h).json()
        assert me["full_name"] == "Renamed Rita"
        assert client.patch("/v1/me", headers=h,
                            json={"full_name": "  "}).json() == {
            "detail": "invalid_name"}
        assert client.patch("/v1/me", headers=h,
                            json={"email": "not-an-email"}).json() == {
            "detail": "invalid_email"}


def test_mobile_change_full_loop(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9198000011", "register",
                      full_name="Mover", role="customer")
        h = _headers(cust["token"])
        assert client.post("/v1/me/mobile/request", headers=h,
                           json={"mobile": "9198000011"}).json() == {
            "detail": "same_mobile"}
        assert client.post("/v1/me/mobile/request", headers=h,
                           json={"mobile": "9000000004"}).status_code == 409
        assert client.post("/v1/me/mobile/request", headers=h,
                           json={"mobile": "123"}).json() == {
            "detail": "invalid_mobile"}
        r = client.post("/v1/me/mobile/request", headers=h,
                        json={"mobile": "9198000012"})
        assert r.json() == {"sent": True}, r.text
        code = _last_code(capsys)
        bad = client.post("/v1/me/mobile/confirm", headers=h,
                          json={"mobile": "9198000012", "code": "000000"})
        assert bad.status_code == 400, bad.text
        r = client.post("/v1/me/mobile/confirm", headers=h,
                        json={"mobile": "9198000012", "code": code})
        assert r.status_code == 200, r.text
        assert r.json()["mobile"] == "9198000012"
        # The pre-change token stays valid: identity is the user id.
        assert client.get("/v1/me", headers=h).json()["mobile"] == "9198000012"
        # New number logs in; the old number is unknown.
        who = _login(client, capsys, "9198000012")
        assert who["user"]["id"] == cust["user"]["id"]
        client.post("/v1/otp/request",
                    json={"mobile": "9198000011", "purpose": "login"})
        stale = client.post("/v1/otp/verify",
                            json={"mobile": "9198000011", "purpose": "login",
                                  "code": _last_code(capsys)})
        assert stale.status_code == 404, stale.text
        # The generic verifier refuses the mobile-change purpose.
        r = client.post("/v1/otp/verify",
                        json={"mobile": "9198000012",
                              "purpose": "mobile_change", "code": "000000"})
        assert r.status_code == 400, r.text


def _completed_bid(client, capsys, h_c, owner_pid, days_ahead, sp_mobile):
    bid, _ = _book(client, h_c, days_ahead)
    h_f, _ = _fresh_sp_here(client, capsys, owner_pid, sp_mobile)
    db = SessionLocal()
    try:
        db.get(Booking, bid).service_date = date.today()
        db.commit()
    finally:
        db.close()
    code = _start_code(client, capsys, h_f, bid)
    r = client.post(f"/v1/bookings/{bid}/start", headers=h_f,
                    json={"code": code})
    assert r.json()["status"] == "in_progress", r.text
    return bid, h_f


def test_address_delete_and_default_fallback(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9198000021", "register",
                      full_name="Addr Anna", role="customer")
        h = _headers(cust["token"])
        ids = []
        for line1, default in [("Delete Me", True), ("Spare Room", False)]:
            r = client.post("/v1/addresses", headers=h,
                            json={"line1": line1, "locality": "Kaloor",
                                  "pincode": "682001", "is_default": default})
            assert r.status_code == 200, r.text
            ids.append(r.json()["id"])
        r = client.delete(f"/v1/addresses/{ids[0]}", headers=h)
        assert r.json() == {"ok": True, "id": ids[0]}, r.text
        rest = client.get("/v1/addresses", headers=h).json()
        assert [a["line1"] for a in rest] == ["Spare Room"]
        assert rest[0]["is_default"] is True
        assert client.delete(f"/v1/addresses/{ids[0]}",
                             headers=h).status_code == 404
        # Another customer's address is invisible, not forbidden-shaped.
        other = _login(client, capsys, "9198000022", "register",
                       full_name="Addr Andy", role="customer")
        h_o = _headers(other["token"])
        r = client.post("/v1/addresses", headers=h_o,
                        json={"line1": "Not Mine", "pincode": "682001"})
        assert client.delete(f"/v1/addresses/{r.json()['id']}",
                             headers=h).status_code == 404
        # An address backing a booking cannot be removed.
        bid, _ = _book(client, h, 26)
        addr_id = SessionLocal().get(Booking, bid).address_id
        r = client.delete(f"/v1/addresses/{addr_id}", headers=h)
        assert r.status_code == 409, r.text
        assert r.json() == {"detail": "address_in_use"}


def test_rate_booking_matrix(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9198000031", "register",
                      full_name="Rater", role="customer")
        owner = _login(client, capsys, "9000000002")
        h_c = _headers(cust["token"])
        bid, h_f = _completed_bid(client, capsys, h_c,
                                  owner["user"]["partner_id"], 27,
                                  "9198000041")
        r = client.post(f"/v1/bookings/{bid}/complete", headers=h_f, json={})
        assert r.json()["status"] == "completed", r.text
        r = client.post(f"/v1/bookings/{bid}/rate", headers=h_c,
                        json={"rating": 5, "comment": "Superb"})
        assert r.status_code == 200, r.text
        assert r.json()["rating"] == 5
        assert client.post(f"/v1/bookings/{bid}/rate", headers=h_c,
                           json={"rating": 4}).status_code == 409
        assert client.post("/v1/bookings/nope/rate", headers=h_c,
                           json={"rating": 5}).status_code == 404
        assert client.post(f"/v1/bookings/{bid}/rate", headers=h_c,
                           json={"rating": 6}).status_code == 422
        # Another customer's booking, and an open booking: forbidden.
        stranger = _login(client, capsys, "9198000032", "register",
                          full_name="Stranger", role="customer")
        h_s = _headers(stranger["token"])
        assert client.post(f"/v1/bookings/{bid}/rate", headers=h_s,
                           json={"rating": 5}).status_code == 403
        open_bid, _ = _book(client, h_c, 28)
        assert client.post(f"/v1/bookings/{open_bid}/rate", headers=h_c,
                           json={"rating": 5}).status_code == 403
        # A tech-collected rating at completion blocks a second rating.
        bid2, h_f2 = _completed_bid(client, capsys, h_c,
                                   owner["user"]["partner_id"], 29,
                                   "9198000042")
        done = client.post(f"/v1/bookings/{bid2}/complete", headers=h_f2,
                           json={"rating": 4})
        assert done.json()["rating"] == 4, done.text
        assert client.post(f"/v1/bookings/{bid2}/rate", headers=h_c,
                           json={"rating": 5}).status_code == 409
