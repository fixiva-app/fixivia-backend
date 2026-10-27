"""Assets API: partner-owner/admin CRUD, code generation, validation, scoping."""

import uuid

from app.db import SessionLocal
from app.models import Partner, User
from app.services.tokens import issue_token
from tests.conftest import make_client
from tests.test_force_assign import _login

OWNER = "9000000002"
ADMIN = "9000000005"
MASTER = "9000000001"
SP = "9000000003"
CUSTOMER = "9000000004"


def _token(client, capsys, mobile):
    return _login(client, capsys, mobile)["token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _payload(loc="TST", **over):
    tag = uuid.uuid4().hex[:8]
    body = {
        "name": f"Asset {tag}",
        "category": "laptop",
        "location": "Test Office",
        "location_code": loc,
    }
    body.update(over)
    return body


def _other_owner_token():
    db = SessionLocal()
    try:
        partner = Partner(trade_name=f"Other Org {uuid.uuid4().hex[:6]}")
        db.add(partner)
        db.flush()
        mobile = "9" + uuid.uuid4().hex[:9]
        user = User(
            role="partner_owner",
            partner_id=partner.id,
            full_name="Other Owner",
            mobile=mobile,
        )
        db.add(user)
        db.commit()
        return issue_token(user_id=user.id, role="partner_owner", partner_id=partner.id)
    finally:
        db.close()


def test_create_assigns_sequential_codes_per_location(capsys):
    with make_client() as client:
        h = _h(_token(client, capsys, OWNER))
        first = client.post("/v1/assets", json=_payload("A01"), headers=h)
        assert first.status_code == 200, first.text
        assert first.json()["asset_code"] == "AST-A01-0001"
        second = client.post("/v1/assets", json=_payload("A01"), headers=h)
        assert second.json()["asset_code"] == "AST-A01-0002"
        other = client.post("/v1/assets", json=_payload("B02"), headers=h)
        assert other.json()["asset_code"] == "AST-B02-0001"


def test_location_code_uppercased(capsys):
    with make_client() as client:
        h = _h(_token(client, capsys, OWNER))
        r = client.post("/v1/assets", json=_payload("c03"), headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["location_code"] == "C03"
        assert r.json()["asset_code"].startswith("AST-C03-")


def test_admin_full_crud(capsys):
    with make_client() as client:
        h = _h(_token(client, capsys, ADMIN))
        created = client.post("/v1/assets", json=_payload("D04"), headers=h)
        assert created.status_code == 200, created.text
        aid = created.json()["id"]
        assert client.get("/v1/assets", headers=h).status_code == 200
        assert client.get(f"/v1/assets/{aid}", headers=h).status_code == 200
        up = client.put(f"/v1/assets/{aid}", json={"assigned_to": "Anil"}, headers=h)
        assert up.status_code == 200 and up.json()["assigned_to"] == "Anil"
        assert client.delete(f"/v1/assets/{aid}", headers=h).status_code == 200
        assert client.get(f"/v1/assets/{aid}", headers=h).status_code == 404


def test_master_customer_sp_forbidden(capsys):
    with make_client() as client:
        for mobile in (MASTER, CUSTOMER, SP):
            h = _h(_token(client, capsys, mobile))
            r = client.post("/v1/assets", json=_payload("E05"), headers=h)
            assert r.status_code == 403, (mobile, r.text)
            assert r.json()["detail"] == "forbidden"
            assert client.get("/v1/assets", headers=h).status_code == 403
        assert client.post("/v1/assets", json=_payload("E05")).status_code == 401
        assert client.get("/v1/assets").status_code == 401


def test_cross_partner_invisible(capsys):
    with make_client() as client:
        h = _h(_token(client, capsys, OWNER))
        aid = client.post("/v1/assets", json=_payload("F06"), headers=h).json()["id"]
        other = _h(_other_owner_token())
        assert client.get(f"/v1/assets/{aid}", headers=other).status_code == 404
        assert client.put(f"/v1/assets/{aid}", json={"name": "X"}, headers=other).status_code == 404
        assert client.delete(f"/v1/assets/{aid}", headers=other).status_code == 404
        ids = [a["id"] for a in client.get("/v1/assets", headers=other).json()]
        assert aid not in ids


def test_required_and_length_validation(capsys):
    with make_client() as client:
        h = _h(_token(client, capsys, OWNER))
        r = client.post("/v1/assets", json=_payload("G07", name="   "), headers=h)
        assert r.status_code == 400 and r.json()["detail"] == "name_required"
        body = _payload("G07")
        del body["name"]
        assert client.post("/v1/assets", json=body, headers=h).status_code == 422
        r = client.post("/v1/assets", json=_payload("G07", name="x" * 121), headers=h)
        assert r.status_code == 422 and r.json()["detail"] == "name_too_long"
        r = client.post("/v1/assets", json=_payload("G07", location=""), headers=h)
        assert r.status_code == 400 and r.json()["detail"] == "location_required"


def test_category_and_location_code_validation(capsys):
    with make_client() as client:
        h = _h(_token(client, capsys, OWNER))
        r = client.post("/v1/assets", json=_payload("H08", category="spaceship"), headers=h)
        assert r.status_code == 422 and r.json()["detail"] == "bad_category"
        for bad in ("AB", "ABCD", "A!C", ""):
            r = client.post("/v1/assets", json=_payload(bad or "H08", location_code=bad), headers=h)
            assert r.status_code == 422 and r.json()["detail"] == "bad_location_code", bad


def test_sim_conditional(capsys):
    with make_client() as client:
        h = _h(_token(client, capsys, OWNER))
        tag = uuid.uuid4().hex[:8]
        base = {"name": f"Phone {tag}", "category": "mobile_phone",
                "location": "Test Office", "location_code": "I09"}
        r = client.post("/v1/assets", json={**base, "has_sim": True}, headers=h)
        assert r.status_code == 400 and r.json()["detail"] == "sim_number_required"
        r = client.post("/v1/assets", json={**base, "has_sim": True, "sim_number": "12345"}, headers=h)
        assert r.status_code == 422 and r.json()["detail"] == "bad_sim_number"
        ok = client.post("/v1/assets", json={**base, "has_sim": True, "sim_number": "9846011223"}, headers=h)
        assert ok.status_code == 200, ok.text
        assert ok.json()["sim_number"] == "9846011223"
        ignored = client.post("/v1/assets", json=_payload("I09", sim_number="9846011223"), headers=h)
        assert ignored.status_code == 200 and ignored.json()["sim_number"] == ""


def test_serial_unique_when_present(capsys):
    with make_client() as client:
        h = _h(_token(client, capsys, OWNER))
        serial = f"SN-{uuid.uuid4().hex[:8]}"
        first = client.post("/v1/assets", json=_payload("J10", serial=serial), headers=h)
        assert first.status_code == 200, first.text
        clash = client.post("/v1/assets", json=_payload("J10", serial=serial), headers=h)
        assert clash.status_code == 409 and clash.json()["detail"] == "serial_taken"
        blank1 = client.post("/v1/assets", json=_payload("J10", serial=""), headers=h)
        blank2 = client.post("/v1/assets", json=_payload("J10"), headers=h)
        assert blank1.status_code == 200 and blank2.status_code == 200
        assert blank1.json()["serial"] is None


def test_update_rules(capsys):
    with make_client() as client:
        h = _h(_token(client, capsys, OWNER))
        serial = f"SN-{uuid.uuid4().hex[:8]}"
        aid = client.post("/v1/assets", json=_payload("K11", serial=serial), headers=h).json()["id"]
        other = client.post("/v1/assets", json=_payload("K11"), headers=h).json()["id"]
        r = client.put(f"/v1/assets/{other}", json={"serial": serial}, headers=h)
        assert r.status_code == 409 and r.json()["detail"] == "serial_taken"
        r = client.put(f"/v1/assets/{aid}", json={"location_code": "Z99"}, headers=h)
        assert r.status_code == 422 and r.json()["detail"] == "location_code_immutable"
        same_case = client.put(f"/v1/assets/{aid}", json={"location_code": "k11"}, headers=h)
        assert same_case.status_code == 200, same_case.text
        r = client.put(f"/v1/assets/{aid}", json={"name": ""}, headers=h)
        assert r.status_code == 400 and r.json()["detail"] == "name_required"


def test_update_sim_flows(capsys):
    with make_client() as client:
        h = _h(_token(client, capsys, OWNER))
        aid = client.post("/v1/assets", json=_payload("L12"), headers=h).json()["id"]
        r = client.put(f"/v1/assets/{aid}", json={"has_sim": True}, headers=h)
        assert r.status_code == 400 and r.json()["detail"] == "sim_number_required"
        r = client.put(f"/v1/assets/{aid}", json={"sim_number": "9846011223"}, headers=h)
        assert r.status_code == 422 and r.json()["detail"] == "sim_not_enabled"
        on = client.put(f"/v1/assets/{aid}", json={"has_sim": True, "sim_number": "9846011223"}, headers=h)
        assert on.status_code == 200 and on.json()["sim_number"] == "9846011223"
        off = client.put(f"/v1/assets/{aid}", json={"has_sim": False}, headers=h)
        assert off.status_code == 200 and off.json()["has_sim"] is False
        assert off.json()["sim_number"] == ""


def test_list_filters(capsys):
    with make_client() as client:
        h = _h(_token(client, capsys, OWNER))
        tag = uuid.uuid4().hex[:8]
        client.post("/v1/assets", json=_payload("M13", name=f"FilterMe {tag}", category="printer"), headers=h)
        client.post("/v1/assets", json=_payload("M13", name=f"Other {tag}", category="ups"), headers=h)
        by_cat = client.get("/v1/assets?category=printer", headers=h).json()
        assert any(f"FilterMe {tag}" == a["name"] for a in by_cat)
        assert all(a["category"] == "printer" for a in by_cat)
        by_q = client.get(f"/v1/assets?q=FilterMe {tag}", headers=h).json()
        assert [a["name"] for a in by_q] == [f"FilterMe {tag}"]
        by_loc = client.get("/v1/assets?location_code=m13", headers=h).json()
        assert {a["name"] for a in by_loc} >= {f"FilterMe {tag}", f"Other {tag}"}
