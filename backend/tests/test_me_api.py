"""Unit tests for /v1/me, /v1/notifications, and the repool job endpoint."""

from tests.conftest import make_client
from tests.test_force_assign import _book, _login


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_me_shape(capsys):
    with make_client() as client:
        me = _login(client, capsys, "9000000004")
        r = client.get("/v1/me", headers=_headers(me["token"]))
        assert r.status_code == 200
        body = r.json()
        assert set(body) == {"id", "mobile", "full_name", "email", "role",
                             "partner_id", "locale", "status"}
        assert (body["mobile"], body["role"]) == ("9000000004", "customer")


def test_repool_requires_master(capsys):
    with make_client() as client:
        for mobile in ("9000000004", "9000000003", "9000000002", "9000000005"):
            who = _login(client, capsys, mobile)
            r = client.post("/v1/jobs/dispatch-repool",
                            headers=_headers(who["token"]))
            assert r.status_code == 403, mobile
            assert r.json() == {"detail": "forbidden"}


def test_repool_counts_open_bookings(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        master = _login(client, capsys, "9000000001")
        h_c = _headers(cust["token"])
        h_m = _headers(master["token"])
        before = client.post("/v1/jobs/dispatch-repool", headers=h_m).json()["open_bookings"]
        _book(client, h_c, 21)
        _book(client, h_c, 22)
        after = client.post("/v1/jobs/dispatch-repool", headers=h_m).json()["open_bookings"]
        assert after - before == 2


def test_notifications_newest_first_with_shape(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9000000004")
        owner = _login(client, capsys, "9000000002")
        h_c = _headers(cust["token"])
        h_o = _headers(owner["token"])
        bid, _ = _book(client, h_c, 23)
        notes = client.get("/v1/notifications", headers=h_o).json()
        assert len(notes) <= 100
        stamps = [n["created_at"] for n in notes]
        assert stamps == sorted(stamps, reverse=True)
        mine = [n for n in notes if n["booking_id"] == bid]
        assert mine and set(mine[0]) == {"id", "type", "booking_id", "payload", "created_at"}
        assert mine[0]["type"] == "new_request"
