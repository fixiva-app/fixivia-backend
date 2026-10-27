"""Shop locations API: owner CRUD, uniqueness, immutability, scoping."""

import uuid

from app.db import SessionLocal
from app.models import Partner, User
from app.services.tokens import issue_token
from tests.conftest import make_client
from tests.test_force_assign import _login

OWNER = "9000000002"
MASTER = "9000000001"
CUSTOMER = "9000000004"


def _token(client, capsys, mobile):
    return _login(client, capsys, mobile)["token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


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


def _payload(**over):
    tag = uuid.uuid4().hex[:4].upper()
    body = {"name": f"Shop {tag}", "code": tag[:3].ljust(3, "X")}
    body.update(over)
    return body


def test_owner_crud_roundtrip(capsys):
    with make_client() as client:
        tok = _token(client, capsys, OWNER)
        created = client.post("/v1/locations", json=_payload(), headers=_h(tok))
        assert created.status_code == 200, created.text
        loc_id = created.json()["id"]
        assert created.json()["is_active"] is True
        assert created.json()["asset_count"] == 0

        listed = client.get("/v1/locations", headers=_h(tok))
        assert listed.status_code == 200
        assert any((r["id"] == loc_id for r in listed.json()))

        renamed = client.put(
            f"/v1/locations/{loc_id}", json={"name": "Renamed Shop"}, headers=_h(tok)
        )
        assert renamed.status_code == 200, renamed.text
        assert renamed.json()["name"] == "Renamed Shop"

        deact = client.put(f"/v1/locations/{loc_id}", json={"is_active": False}, headers=_h(tok))
        assert deact.status_code == 200
        assert deact.json()["is_active"] is False

        deleted = client.delete(f"/v1/locations/{loc_id}", headers=_h(tok))
        assert deleted.status_code == 200, deleted.text


def test_code_and_name_uniqueness_per_partner(capsys):
    with make_client() as client:
        tok = _token(client, capsys, OWNER)
        first = client.post("/v1/locations", json=_payload(name="Unique Shop", code="UQ1"), headers=_h(tok))
        assert first.status_code == 200, first.text
        try:
            dup_code = client.post(
                "/v1/locations", json=_payload(name="Other Name", code="uq1"), headers=_h(tok)
            )
            assert dup_code.status_code == 409, dup_code.text
            assert dup_code.json()["detail"] == "location_code_taken"

            dup_name = client.post(
                "/v1/locations", json=_payload(name="unique shop", code="UQ2"), headers=_h(tok)
            )
            assert dup_name.status_code == 409, dup_name.text
            assert dup_name.json()["detail"] == "location_name_taken"

            # Same code on a different partner is fine.
            other = client.post(
                "/v1/locations",
                json=_payload(name="Unique Shop", code="UQ1"),
                headers=_h(_other_owner_token()),
            )
            assert other.status_code == 200, other.text
        finally:
            client.delete(f"/v1/locations/{first.json()['id']}", headers=_h(tok))


def test_validation_errors(capsys):
    with make_client() as client:
        tok = _token(client, capsys, OWNER)
        bad_code = client.post("/v1/locations", json={"name": "X", "code": "AB"}, headers=_h(tok))
        assert bad_code.status_code == 422
        assert bad_code.json()["detail"] == "bad_location_code"
        no_name = client.post("/v1/locations", json={"name": " ", "code": "V01"}, headers=_h(tok))
        assert no_name.status_code == 400
        assert no_name.json()["detail"] == "name_required"


def test_roles_and_scoping(capsys):
    with make_client() as client:
        owner_tok = _token(client, capsys, OWNER)
        created = client.post("/v1/locations", json=_payload(), headers=_h(owner_tok))
        loc_id = created.json()["id"]
        try:
            assert client.get("/v1/locations", headers=_h(_token(client, capsys, MASTER))).status_code == 403
            assert client.get("/v1/locations", headers=_h(_token(client, capsys, CUSTOMER))).status_code == 403
            assert (
                client.get("/v1/locations", headers=_h(_other_owner_token())).json() == []
                or all(r["id"] != loc_id for r in client.get("/v1/locations", headers=_h(_other_owner_token())).json())
            )
            assert client.delete(f"/v1/locations/{loc_id}", headers=_h(_other_owner_token())).status_code == 404
        finally:
            client.delete(f"/v1/locations/{loc_id}", headers=_h(owner_tok))


def test_delete_blocked_when_assets_use_code(capsys):
    with make_client() as client:
        tok = _token(client, capsys, OWNER)
        created = client.post("/v1/locations", json=_payload(code="USE"), headers=_h(tok))
        assert created.status_code == 200, created.text
        loc_id = created.json()["id"]
        asset = client.post(
            "/v1/assets",
            json={
                "name": f"Asset {uuid.uuid4().hex[:6]}",
                "category": "laptop",
                "location": "Use Shop",
                "location_code": "USE",
            },
            headers=_h(tok),
        )
        assert asset.status_code == 200, asset.text
        try:
            blocked = client.delete(f"/v1/locations/{loc_id}", headers=_h(tok))
            assert blocked.status_code == 409, blocked.text
            assert blocked.json()["detail"] == "location_in_use"
            listed = client.get("/v1/locations", headers=_h(tok)).json()
            assert [r for r in listed if r["id"] == loc_id][0]["asset_count"] == 1
        finally:
            client.delete(f"/v1/assets/{asset.json()['id']}", headers=_h(tok))
            client.delete(f"/v1/locations/{loc_id}", headers=_h(tok))
