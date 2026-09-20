from tests.conftest import make_client


def test_health():
    with make_client() as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["ok"] is True


def _otp(client, mobile, purpose, **extra):
    req = client.post("/v1/otp/request", json={"mobile": mobile, "purpose": purpose})
    assert req.status_code == 200
    # code is on stdout; request a second time would create another. Parse from... we need to get code from DB or capture.
    return req


def test_register_login_otp_roundtrip(capsys):
    with make_client() as client:
        mobile = "9111111111"
        req = client.post("/v1/otp/request", json={"mobile": mobile, "purpose": "register"})
        assert req.status_code == 200
        printed = capsys.readouterr().out
        assert "[OTP] purpose=register" in printed
        code = [p for p in printed.split() if p.startswith("code=")][-1].split("=", 1)[1]
        ok = client.post(
            "/v1/otp/verify",
            json={
                "mobile": mobile,
                "purpose": "register",
                "code": code,
                "full_name": "Asha",
                "role": "customer",
            },
        )
        assert ok.status_code == 200, ok.text
        assert ok.json()["user"]["role"] == "customer"
        assert ok.json()["token"]
