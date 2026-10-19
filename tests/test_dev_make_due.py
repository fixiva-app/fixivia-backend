"""Dev-only make-due hook for same-day start/complete journeys."""

import itertools
from unittest.mock import patch

from tests.conftest import make_client
from tests.test_force_assign import _book, _login

_days = itertools.count(500)


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_make_due_by_ids_and_mobile(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        h_c = _headers(cust["token"])
        bid, _ = _book(client, h_c, next(_days))
        bid2, _ = _book(client, h_c, next(_days))
        r = client.post("/v1/dev/bookings/make-due",
                        json={"booking_ids": [bid, "nope"]})
        assert r.status_code == 200, r.text
        assert r.json() == {"moved": [bid]}
        r = client.post("/v1/dev/bookings/make-due",
                        json={"customer_mobile": "9000000004"})
        assert r.status_code == 200, r.text
        assert bid2 in r.json()["moved"]
        # Empty selector moves nothing.
        r = client.post("/v1/dev/bookings/make-due", json={})
        assert r.json() == {"moved": []}


def test_make_due_skips_final_bookings(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        owner = _login(client, capsys, "9000000002")
        h_c = _headers(cust["token"])
        h_s = _headers(owner["token"])
        bid, _ = _book(client, h_c, next(_days))
        done = client.post(f"/v1/bookings/{bid}/complete", headers=h_s,
                           json={}).json()
        assert done["status"] == "completed"
        r = client.post("/v1/dev/bookings/make-due",
                        json={"booking_ids": [bid]})
        assert r.json() == {"moved": []}


def test_make_due_hidden_when_not_dev():
    with make_client() as client:
        with patch("app.api.dev.settings.flavor", "prod"):
            res = client.post("/v1/dev/bookings/make-due",
                              json={"booking_ids": ["x"]})
        assert res.status_code == 404
