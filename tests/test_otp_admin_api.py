# TEMP-OTP: delete this file with api/otp_admin.py once real SMS ships.
"""Unit tests for the temporary admin OTP read API."""

from datetime import timedelta

from app.db import SessionLocal
from app.models import OtpCodeRow, utcnow
from tests.conftest import admin_otp_code, make_client


def _headers(user="otpadmin", password="otpadminpass"):
    return {"X-Otp-Admin-User": user, "X-Otp-Admin-Pass": password}


def test_admin_otp_denied_without_or_with_wrong_creds():
    with make_client() as client:
        r = client.get("/v1/admin/otp-code?mobile=9000000004")
        assert r.status_code == 401
        r = client.get("/v1/admin/otp-code?mobile=9000000004",
                       headers=_headers(password="nope"))
        assert r.status_code == 401


def test_admin_otp_roundtrip_and_code_verifies():
    with make_client() as client:
        mobile = "9198000201"
        assert client.post("/v1/otp/request",
                           json={"mobile": mobile, "purpose": "register"}).status_code == 200
        code = admin_otp_code(client, mobile, "register")
        assert len(code) == 6 and code.isdigit()
        r = client.post("/v1/otp/verify",
                        json={"mobile": mobile, "purpose": "register", "code": code,
                              "full_name": "T", "role": "customer"})
        assert r.status_code == 200, r.text


def test_admin_otp_404_when_missing_consumed_or_expired():
    with make_client() as client:
        r = client.get("/v1/admin/otp-code?mobile=9198000299", headers=_headers())
        assert r.status_code == 404

        mobile = "9198000202"
        client.post("/v1/otp/request", json={"mobile": mobile, "purpose": "register"})
        code = admin_otp_code(client, mobile, "register")
        client.post("/v1/otp/verify",
                    json={"mobile": mobile, "purpose": "register", "code": code,
                          "full_name": "T", "role": "customer"})
        r = client.get(f"/v1/admin/otp-code?mobile={mobile}", headers=_headers())
        assert r.status_code == 404

        stale = "9198000203"
        client.post("/v1/otp/request", json={"mobile": stale, "purpose": "login"})
        db = SessionLocal()
        try:
            row = db.query(OtpCodeRow).filter_by(mobile=stale, consumed_at=None).one()
            row.expires_at = utcnow() - timedelta(minutes=1)
            db.commit()
        finally:
            db.close()
        r = client.get(f"/v1/admin/otp-code?mobile={stale}", headers=_headers())
        assert r.status_code == 404


def test_admin_otp_purpose_and_booking_filters():
    with make_client() as client:
        mobile = "9198000204"
        client.post("/v1/otp/request", json={"mobile": mobile, "purpose": "login"})
        r = client.get(f"/v1/admin/otp-code?mobile={mobile}&purpose=register",
                       headers=_headers())
        assert r.status_code == 404

        db = SessionLocal()
        try:
            db.add(OtpCodeRow(mobile=mobile, purpose="start_work", code="123456",
                              expires_at=utcnow() + timedelta(minutes=10),
                              booking_id="bk-1"))
            db.commit()
        finally:
            db.close()
        r = client.get(f"/v1/admin/otp-code?mobile={mobile}&purpose=start_work&booking_id=bk-1",
                       headers=_headers())
        assert r.status_code == 200 and r.json()["code"] == "123456"
        r = client.get(f"/v1/admin/otp-code?mobile={mobile}&purpose=start_work&booking_id=bk-2",
                       headers=_headers())
        assert r.status_code == 404


def test_admin_otp_read_is_audited():
    from app.models import AuditLog

    with make_client() as client:
        mobile = "9198000205"
        client.post("/v1/otp/request", json={"mobile": mobile, "purpose": "login"})
        r = client.get(f"/v1/admin/otp-code?mobile={mobile}", headers=_headers())
        assert r.status_code == 200
        db = SessionLocal()
        try:
            rows = db.query(AuditLog).filter_by(action="otp_code_read").all()
            assert any(mobile in (row.meta or "") for row in rows)
        finally:
            db.close()
