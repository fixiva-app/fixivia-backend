"""Owner payouts: partner-scoped ledger list + mark-paid."""

from datetime import date

from app.db import SessionLocal
from app.models import Booking
from tests.conftest import make_client
from tests.test_bookings_api import _headers, _start_code
from tests.test_bucket2_api import _fresh_sp_here
from tests.test_force_assign import _book, _login


def _completed_as(client, capsys, h_c, owner_pid, days_ahead, sp_mobile):
    bid, _ = _book(client, h_c, days_ahead)
    h_f, _ = _fresh_sp_here(client, capsys, owner_pid, sp_mobile)
    db = SessionLocal()
    try:
        db.get(Booking, bid).service_date = date.today()
        db.commit()
    finally:
        db.close()
    code = _start_code(client, capsys, h_f, bid)
    started = client.post(f"/v1/bookings/{bid}/start", headers=h_f,
                          json={"code": code})
    assert started.json()["status"] == "in_progress", started.text
    done = client.post(f"/v1/bookings/{bid}/complete", headers=h_f, json={})
    assert done.json()["status"] == "completed", done.text
    return bid


def test_payouts_list_and_mark_paid(capsys):
    with make_client() as client:
        cust = _login(client, capsys, "9198000051", "register",
                      full_name="Pay Paula", role="customer")
        owner = _login(client, capsys, "9000000002")
        h_c = _headers(cust["token"])
        h_o = _headers(owner["token"])
        bid = _completed_as(client, capsys, h_c, owner["user"]["partner_id"],
                            31, "9198000052")
        rows = client.get("/v1/payouts", headers=h_o).json()
        mine = [r for r in rows if r["booking_id"] == bid]
        assert len(mine) == 1, rows
        row = mine[0]
        assert set(row) == {"id", "booking_id", "service_partner_id",
                            "sp_name", "amount", "status", "paid_at"}
        assert (row["status"], row["paid_at"]) == ("pending", None)
        r = client.post(f"/v1/payouts/{row['id']}/paid", headers=h_o)
        assert r.json() == {"id": row["id"], "status": "paid"}, r.text
        again = [r for r in client.get("/v1/payouts", headers=h_o).json()
                 if r["id"] == row["id"]][0]
        assert again["status"] == "paid" and again["paid_at"], again
        assert client.post("/v1/payouts/nope/paid",
                           headers=h_o).status_code == 404
        # Customer and tech are not allowed near the ledger.
        sp = _login(client, capsys, "9000000003")
        assert client.get("/v1/payouts", headers=h_c).status_code == 403
        assert client.get(
            "/v1/payouts",
            headers=_headers(sp["token"])).status_code == 403
