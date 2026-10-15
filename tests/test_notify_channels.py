import pytest

from app.services.notify import (
    ChannelError,
    ChannelNotConfigured,
    ConsoleNotificationChannel,
    NotificationChannel,
    WhatsAppNotificationChannel,
    configure_notification_channel,
    get_notification_channel,
)
from tests.conftest import make_client
from tests.test_force_assign import _book, _login


class FakeChannel(NotificationChannel):
    name = "fake"

    def __init__(self):
        self.sent = []

    def send(self, *, user_id, mobile, ntype, booking_id, payload):
        self.sent.append(
            {"user_id": user_id, "ntype": ntype, "booking_id": booking_id, "payload": payload}
        )


class FailingChannel(NotificationChannel):
    name = "failing"

    def send(self, *, user_id, mobile, ntype, booking_id, payload):
        raise ChannelError("boom")


def test_dispatch_events_reach_configured_channel(capsys):
    fake = FakeChannel()
    configure_notification_channel(fake)
    try:
        with make_client() as client:
            cust = _login(client, capsys, "9000000004")
            h_c = {"Authorization": f"Bearer {cust['token']}"}
            bid, _ = _book(client, h_c, 8)
    finally:
        configure_notification_channel(None)
    offers = [s for s in fake.sent if s["ntype"] == "offer" and s["booking_id"] == bid]
    assert offers, "pool offer should fan out through the channel"


def test_db_notification_survives_channel_failure(capsys):
    configure_notification_channel(FailingChannel())
    try:
        with make_client() as client:
            cust = _login(client, capsys, "9000000004")
            sp = _login(client, capsys, "9000000003")
            h_c = {"Authorization": f"Bearer {cust['token']}"}
            bid, _ = _book(client, h_c, 9)
            h_s = {"Authorization": f"Bearer {sp['token']}"}
            notes = client.get("/v1/notifications", headers=h_s).json()
    finally:
        configure_notification_channel(None)
    assert any(n["booking_id"] == bid and n["type"] == "offer" for n in notes)
    assert "channel_error" in capsys.readouterr().out


def test_console_is_default_and_whatsapp_needs_creds():
    assert isinstance(get_notification_channel(), ConsoleNotificationChannel)
    with pytest.raises(ChannelNotConfigured):
        WhatsAppNotificationChannel(api_base="", api_key="", sender="")
    with pytest.raises(ChannelNotConfigured):
        WhatsAppNotificationChannel(api_base="https://bsp.example", api_key="", sender="Fixiva")


def test_whatsapp_send_failure_is_channel_error():
    ch = WhatsAppNotificationChannel(api_base="http://127.0.0.1:9", api_key="k", sender="Fixiva")
    with pytest.raises(ChannelError):
        ch.send(user_id="u", mobile="9000000003", ntype="offer", booking_id="b", payload={})
    with pytest.raises(ChannelError):
        ch.send(user_id="u", mobile="", ntype="offer", booking_id="b", payload={})


class _FakeResponse:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_whatsapp_http_status_paths(monkeypatch):
    import urllib.request

    ch = WhatsAppNotificationChannel(api_base="https://bsp.example", api_key="k",
                                     sender="Fixiva")
    seen = {}

    def _ok(req, timeout):
        seen["url"] = req.full_url
        seen["auth"] = req.headers.get("Authorization")
        return _FakeResponse(200)

    monkeypatch.setattr(urllib.request, "urlopen", _ok)
    ch.send(user_id="u", mobile="9000000003", ntype="offer", booking_id="b",
            payload={"slot_cap": 5})
    assert seen["url"] == "https://bsp.example/messages"
    assert seen["auth"] == "Bearer k"

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout: _FakeResponse(500))
    with pytest.raises(ChannelError, match="whatsapp http 500"):
        ch.send(user_id="u", mobile="9000000003", ntype="offer", booking_id="b",
                payload={})


def test_get_channel_whatsapp_branch(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "whatsapp_enabled", True)
    monkeypatch.setattr(settings, "whatsapp_api_base", "https://bsp.example")
    monkeypatch.setattr(settings, "whatsapp_api_key", "k")
    monkeypatch.setattr(settings, "whatsapp_sender", "Fixiva")
    assert isinstance(get_notification_channel(), WhatsAppNotificationChannel)
