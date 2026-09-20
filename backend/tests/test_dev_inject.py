from unittest.mock import patch

from tests.conftest import make_client


def test_inject_users_creates_one_of_each_role():
    with make_client() as client:
        first = client.post("/v1/dev/inject-users")
        assert first.status_code == 200, first.text
        accounts = first.json()["accounts"]
        roles = [a["role"] for a in accounts]
        assert roles == [
            "master_admin",
            "partner_owner",
            "service_partner",
            "customer",
            "partner_admin",
        ]
        assert {a["mobile"] for a in accounts} == {
            "9000000001",
            "9000000002",
            "9000000003",
            "9000000004",
            "9000000005",
        }
        for acc in accounts:
            assert acc["token"]
            me = client.get("/v1/me", headers={"Authorization": f"Bearer {acc['token']}"})
            assert me.status_code == 200, me.text
            assert me.json()["role"] == acc["role"]

        second = client.post("/v1/dev/inject-users")
        assert second.status_code == 200
        assert [a["mobile"] for a in second.json()["accounts"]] == [
            a["mobile"] for a in accounts
        ]


def test_inject_users_hidden_when_not_dev():
    with make_client() as client:
        with patch("app.api.dev.settings.flavor", "prod"):
            res = client.post("/v1/dev/inject-users")
        assert res.status_code == 404
