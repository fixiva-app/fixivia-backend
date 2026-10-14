from tests.conftest import make_client


def _login(client, capsys, mobile, purpose="login", **reg):
    client.post("/v1/otp/request", json={"mobile": mobile, "purpose": purpose})
    printed = capsys.readouterr().out
    code = [p for p in printed.split() if p.startswith("code=")][-1].split("=", 1)[1]
    body = {"mobile": mobile, "purpose": purpose, "code": code, **reg}
    r = client.post("/v1/otp/verify", json=body)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def test_sp_pages_all_load(capsys):
    with make_client() as client:
        sp = _login(client, capsys, "9000000003")
        h = {"Authorization": f"Bearer {sp}"}
        for path in (
            "/v1/offers",
            "/v1/sp/schedule",
            "/v1/sp/earnings",
            "/v1/sp/profile",
            "/v1/sp/availability",
            "/v1/analytics",
        ):
            r = client.get(path, headers=h)
            assert r.status_code == 200, (path, r.text)


def test_sp_earnings_shape(capsys):
    with make_client() as client:
        sp = _login(client, capsys, "9000000003")
        h = {"Authorization": f"Bearer {sp}"}
        r = client.get("/v1/sp/earnings", headers=h)
        assert r.status_code == 200, r.text
        body = r.json()
        assert set(body) == {"pending", "paid", "jobs"}
        assert body["jobs"] == 0
        assert body["pending"] == "0"
        assert body["paid"] == "0"
