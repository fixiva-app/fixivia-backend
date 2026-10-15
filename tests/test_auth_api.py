"""Unit tests for OTP request/verify and registration gates."""

import itertools
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db import SessionLocal
from app.models import OtpChallengeRow, PartnerInvite, ServicePartnerProfile
from tests.conftest import make_client

_mobiles = itertools.count(9190000001)


def _mobile():
    return str(next(_mobiles))


def _code(client, capsys, mobile, purpose):
    r = client.post("/v1/otp/request", json={"mobile": mobile, "purpose": purpose})
    assert r.status_code == 200, r.text
    printed = capsys.readouterr().out
    return [p for p in printed.split() if p.startswith("code=")][-1].split("=", 1)[1]


def _verify(client, mobile, purpose, code, **extra):
    return client.post("/v1/otp/verify", json={
        "mobile": mobile, "purpose": purpose, "code": code, **extra})


def _login_seed(client, capsys, mobile):
    code = _code(client, capsys, mobile, "login")
    r = _verify(client, mobile, "login", code)
    assert r.status_code == 200, r.text
    return r.json()


def test_request_rejects_start_work_purpose():
    with make_client() as client:
        r = client.post("/v1/otp/request",
                        json={"mobile": _mobile(), "purpose": "start_work"})
        assert r.status_code == 400
        r = client.post("/v1/otp/request", json={"mobile": "123", "purpose": "login"})
        assert r.status_code == 422


def test_verify_rejects_start_work_purpose():
    with make_client() as client:
        r = client.post("/v1/otp/verify", json={
            "mobile": _mobile(), "purpose": "start_work", "code": "123456"})
        assert r.status_code == 400


def test_verify_without_request_is_not_found():
    with make_client() as client:
        r = _verify(client, _mobile(), "login", "123456")
        assert r.status_code == 400
        assert r.json() == {"detail": "otp_not_found"}


def test_verify_wrong_expired_and_reused_codes(capsys):
    with make_client() as client:
        mobile = _mobile()
        code = _code(client, capsys, mobile, "login")
        r = _verify(client, mobile, "login", "000000")
        assert r.status_code == 400
        assert r.json() == {"detail": "otp_invalid"}
        db = SessionLocal()
        try:
            row = db.scalar(select(OtpChallengeRow).where(
                OtpChallengeRow.mobile == mobile,
                OtpChallengeRow.consumed_at.is_(None)))
            row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            db.commit()
        finally:
            db.close()
        r = _verify(client, mobile, "login", code)
        assert r.json() == {"detail": "otp_expired"}
        # fresh code verifies once, then is consumed (second use: not found)
        code2 = _code(client, capsys, mobile, "register")
        r = _verify(client, mobile, "register", code2, full_name="T")
        assert r.status_code == 200, r.text
        r = _verify(client, mobile, "register", code2, full_name="T")
        assert r.json() == {"detail": "otp_not_found"}


def test_register_existing_mobile_conflicts(capsys):
    with make_client() as client:
        mobile = _mobile()
        code = _code(client, capsys, mobile, "register")
        first = _verify(client, mobile, "register", code)
        assert first.status_code == 200, first.text
        code2 = _code(client, capsys, mobile, "register")
        r = _verify(client, mobile, "register", code2)
        assert r.status_code == 409
        assert r.json() == {"detail": "mobile_taken"}


def test_register_unknown_role_rejected(capsys):
    with make_client() as client:
        mobile = _mobile()
        code = _code(client, capsys, mobile, "register")
        r = _verify(client, mobile, "register", code, role="ceo")
        assert r.status_code == 400
        assert r.json() == {"detail": "invalid_role"}


def test_register_privileged_roles_forbidden(capsys):
    with make_client() as client:
        for role in ("master_admin", "partner_admin"):
            mobile = _mobile()
            code = _code(client, capsys, mobile, "register")
            r = _verify(client, mobile, "register", code, full_name="Rogue", role=role)
            assert r.status_code == 403, r.text
            assert r.json() == {"detail": "forbidden"}


def test_register_customer_defaults(capsys):
    with make_client() as client:
        mobile = _mobile()
        code = _code(client, capsys, mobile, "register")
        r = _verify(client, mobile, "register", code)
        assert r.status_code == 200, r.text
        user = r.json()["user"]
        assert (user["role"], user["full_name"], user["locale"]) == (
            "customer", "User", "en")


def test_register_sp_requires_partner_and_creates_profile(capsys):
    with make_client() as client:
        owner = _login_seed(client, capsys, "9000000002")
        partner_id = client.get(
            "/v1/partners/me",
            headers={"Authorization": f"Bearer {owner['token']}"}).json()["id"]
        mobile = _mobile()
        code = _code(client, capsys, mobile, "register")
        r = _verify(client, mobile, "register", code, role="service_partner")
        assert r.status_code == 400
        assert r.json() == {"detail": "partner_id_required"}
        mobile2 = _mobile()
        code2 = _code(client, capsys, mobile2, "register")
        r = _verify(client, mobile2, "register", code2, role="service_partner",
                    partner_id=partner_id)
        assert r.status_code == 200, r.text
        db = SessionLocal()
        try:
            prof = db.get(ServicePartnerProfile, r.json()["user"]["id"])
            assert prof is not None and prof.partner_id == partner_id
        finally:
            db.close()


def _invite(client, master_token):
    r = client.post("/v1/partners/invites",
                    headers={"Authorization": f"Bearer {master_token}"})
    assert r.status_code == 200, r.text
    return r.json()


def test_register_owner_invite_gates(capsys):
    with make_client() as client:
        master = _login_seed(client, capsys, "9000000001")
        h_m = {"Authorization": f"Bearer {master['token']}"}
        mobile = _mobile()
        code = _code(client, capsys, mobile, "register")
        r = _verify(client, mobile, "register", code, role="partner_owner")
        assert r.json() == {"detail": "invite_required"}
        r = _verify(client, mobile, "register", code, role="partner_owner",
                    invite_token="bogus")
        assert r.json() == {"detail": "invite_invalid"}
        inv = _invite(client, master["token"])
        r = _verify(client, mobile, "register", code, role="partner_owner",
                    invite_token=inv["token"])
        assert r.json() == {"detail": "apply_first"}
        # expired invite
        inv2 = _invite(client, master["token"])
        db = SessionLocal()
        try:
            row = db.scalar(select(PartnerInvite).where(
                PartnerInvite.token_plain_dev == inv2["token"]))
            row.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
            db.commit()
        finally:
            db.close()
        mobile2 = _mobile()
        code2 = _code(client, capsys, mobile2, "register")
        r = _verify(client, mobile2, "register", code2, role="partner_owner",
                    invite_token=inv2["token"])
        assert r.json() == {"detail": "invite_invalid"}


def test_register_owner_links_partner_and_primary(capsys):
    with make_client() as client:
        master = _login_seed(client, capsys, "9000000001")
        h_m = {"Authorization": f"Bearer {master['token']}"}
        inv = _invite(client, master["token"])
        ap = client.post("/v1/partners/apply", json={
            "invite_token": inv["token"], "trade_name": f"UAuth {_mobile()}",
            "office_pincode": "673001", "personal_email": "u@x.io"})
        assert ap.status_code == 200, ap.text
        pid = ap.json()["partner_id"]
        mobile = _mobile()
        code = _code(client, capsys, mobile, "register")
        r = _verify(client, mobile, "register", code, role="partner_owner",
                    invite_token=inv["token"])
        assert r.status_code == 200, r.text
        assert r.json()["user"]["partner_id"] == pid
        me = client.get("/v1/partners/me",
                        headers={"Authorization": f"Bearer {r.json()['token']}"})
        assert me.json()["id"] == pid
        # second owner on the same invite: links partner, keeps first primary
        mobile2 = _mobile()
        code2 = _code(client, capsys, mobile2, "register")
        r2 = _verify(client, mobile2, "register", code2, role="partner_owner",
                     invite_token=inv["token"])
        assert r2.status_code == 200, r2.text
        assert r2.json()["user"]["partner_id"] == pid


def test_login_unknown_mobile_and_happy_path(capsys):
    with make_client() as client:
        mobile = _mobile()
        code = _code(client, capsys, mobile, "login")
        r = _verify(client, mobile, "login", code)
        assert r.status_code == 404
        assert r.json() == {"detail": "user_not_found"}
        body = _login_seed(client, capsys, "9000000004")
        assert body["user"]["role"] == "customer"
        assert body["token"]
