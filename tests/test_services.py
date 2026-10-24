"""Unit tests for services, tokens, serializers, and config."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import settings
from app.domain.otp import OtpPurpose
from app.services.notify import ChannelNotConfigured
from app.services.otp_sender import (
    ConsoleOtpSender,
    OtpSender,
    WhatsAppOtpSender,
    default_otp_sender,
)
from app.services.serializers import mask_mobile, user_public
from app.services.tokens import issue_token, parse_token


def test_issue_and_parse_roundtrip():
    token = issue_token(user_id="u1", role="customer", partner_id=None)
    payload = parse_token(token)
    assert payload["sub"] == "u1"
    assert payload["role"] == "customer"
    assert payload["partner_id"] is None
    assert payload["exp"] - payload["iat"] == settings.jwt_hours * 3600


def test_parse_rejects_tampered_and_expired():
    token = issue_token(user_id="u1", role="customer", partner_id="p1")
    with pytest.raises(jwt.InvalidTokenError):
        parse_token(token + "x")
    now = datetime.now(timezone.utc)
    old = jwt.encode(
        {"sub": "u1", "role": "customer", "partner_id": None,
         "iat": int((now - timedelta(days=30)).timestamp()),
         "exp": int((now - timedelta(days=1)).timestamp())},
        settings.jwt_secret, algorithm="HS256",
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        parse_token(old)


def test_mask_mobile_shapes():
    assert mask_mobile("9000000004") == "900000****0004"
    assert mask_mobile("1234") == "****1234"
    assert mask_mobile("12") == "****"
    assert mask_mobile("") == "****"
    assert mask_mobile("+91-90000-00004") == "91900000****0004"


def test_user_public_allowlist():
    class FakeUser:
        id = "u"
        mobile = "9000000001"
        full_name = "N"
        email = "e@x.io"
        role = "customer"
        partner_id = None
        locale = "en"
        status = "active"
        password_hash = "SHOULD-NOT-LEAK"

    assert user_public(FakeUser()) == {
        "id": "u", "mobile": "9000000001", "full_name": "N", "email": "e@x.io",
        "role": "customer", "partner_id": None, "locale": "en", "status": "active",
    }


def test_config_dev_defaults():
    assert settings.flavor == "dev"
    assert settings.whatsapp_enabled is False
    assert settings.otp_ttl_minutes == 10
    assert settings.jwt_hours == 24 * 14


def test_otp_sender_base_is_abstract():
    with pytest.raises(NotImplementedError):
        OtpSender().send(OtpPurpose.LOGIN, "9000000001", "123456")


def test_console_sender_format(capsys):
    from app.services.otp_sender import last_console_code

    ConsoleOtpSender().send(OtpPurpose.LOGIN, "9000000001", "123456")
    assert capsys.readouterr().out == ""
    assert last_console_code("login", "9000000001") == "123456"
    ConsoleOtpSender().send(OtpPurpose.START_WORK, "9000000001", "999999",
                            meta="booking_id=b1")
    assert capsys.readouterr().out == ""
    assert last_console_code("start_work", "9000000001") == "999999"


def test_default_sender_console_and_whatsapp(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_enabled", False)
    assert isinstance(default_otp_sender(), ConsoleOtpSender)
    monkeypatch.setattr(settings, "whatsapp_enabled", True)
    monkeypatch.setattr(settings, "whatsapp_api_base", "https://bsp.example")
    monkeypatch.setattr(settings, "whatsapp_api_key", "k")
    monkeypatch.setattr(settings, "whatsapp_sender", "Fixiva")
    assert isinstance(default_otp_sender(), WhatsAppOtpSender)


def test_default_sender_whatsapp_without_creds_fails(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_enabled", True)
    monkeypatch.setattr(settings, "whatsapp_api_base", "")
    monkeypatch.setattr(settings, "whatsapp_api_key", "")
    monkeypatch.setattr(settings, "whatsapp_sender", "")
    with pytest.raises(ChannelNotConfigured):
        default_otp_sender()


def test_whatsapp_otp_sender_booking_meta(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_api_base", "https://bsp.example")
    monkeypatch.setattr(settings, "whatsapp_api_key", "k")
    monkeypatch.setattr(settings, "whatsapp_sender", "Fixiva")
    sender = WhatsAppOtpSender()
    calls = []
    sender._channel.send = lambda **kw: calls.append(kw)
    sender.send(OtpPurpose.START_WORK, "9000000004", "111111", meta="booking_id=b1")
    assert calls[0]["booking_id"] == "b1"
    assert calls[0]["ntype"] == "otp_start_work"
    assert calls[0]["payload"] == {"code": "111111"}
    sender.send(OtpPurpose.LOGIN, "9000000004", "222222")
    assert calls[1]["booking_id"] is None
    sender.send(OtpPurpose.LOGIN, "9000000004", "333333", meta="unrelated")
    assert calls[2]["booking_id"] is None
