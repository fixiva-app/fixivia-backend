from unittest.mock import patch

from tests.conftest import make_client


def test_otp_code_roundtrip_after_request():
    with make_client() as client:
        seed = client.post("/v1/dev/inject-users")
        assert seed.status_code == 200, seed.text
        req = client.post(
            "/v1/otp/request",
            json={"mobile": "9000000004", "purpose": "login"},
        )
        assert req.status_code == 200, req.text
        got = client.get(
            "/v1/dev/otp-code",
            params={"mobile": "9000000004", "purpose": "login"},
        )
        assert got.status_code == 200, got.text
        body = got.json()
        assert body["mobile"] == "9000000004"
        assert body["purpose"] == "login"
        assert len(body["code"]) == 6
        # Other purposes stay empty: the hook is scoped per purpose.
        other = client.get(
            "/v1/dev/otp-code",
            params={"mobile": "9000000004", "purpose": "register"},
        )
        assert other.status_code == 404
        # The disclosed code verifies: proves the hook returns the live code.
        verify = client.post(
            "/v1/otp/verify",
            json={"mobile": "9000000004", "purpose": "login", "code": body["code"]},
        )
        assert verify.status_code == 200, verify.text


def test_otp_code_unknown_is_404():
    with make_client() as client:
        res = client.get("/v1/dev/otp-code", params={"mobile": "9111111111"})
        assert res.status_code == 404
        assert "otp_not_found" in res.text


def test_otp_code_hidden_when_not_dev():
    with make_client() as client:
        with patch("app.api.dev.settings.flavor", "prod"):
            res = client.get("/v1/dev/otp-code", params={"mobile": "9000000004"})
        assert res.status_code == 404
