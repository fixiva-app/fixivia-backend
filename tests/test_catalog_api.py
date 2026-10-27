"""Unit tests for catalog, categories, and partner pricing."""

import itertools

from tests.conftest import make_client
from tests.test_force_assign import _login

_slugs = itertools.count(1)


def _slug(prefix="u-cat"):
    return f"{prefix}-{next(_slugs)}"


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _cat_body(slug=None, **kw):
    body = {"slug": slug or _slug(), "name_en": "Name",
            "problems": [{"text_en": "Fix", "sort_order": 0}]}
    body.update(kw)
    return body


def test_list_filters_active_and_shape(capsys):
    with make_client() as client:
        master = _login(client, capsys, "9000000001")
        h_m = _headers(master["token"])
        slug = _slug()
        created = client.post("/v1/categories", headers=h_m, json=_cat_body(slug))
        assert created.status_code == 200, created.text
        assert created.json()["problems"][0]["text_en"] == "Fix"
        hidden = client.post("/v1/categories", headers=h_m,
                             json=_cat_body(is_active=False))
        assert hidden.status_code == 200
        names = [c["slug"] for c in client.get("/v1/categories").json()]
        assert slug in names and hidden.json()["slug"] not in names
        all_names = [c["slug"] for c in client.get("/v1/categories?active=false").json()]
        assert hidden.json()["slug"] in all_names
        bare = client.post("/v1/categories", headers=h_m,
                           json={"slug": _slug(), "name_en": "Bare"})
        assert bare.status_code == 200
        assert bare.json()["problems"] == []


def test_create_validates_featured_rank(capsys):
    with make_client() as client:
        master = _login(client, capsys, "9000000001")
        h_m = _headers(master["token"])
        for bad in (0, 6):
            r = client.post("/v1/categories", headers=h_m,
                            json=_cat_body(featured_rank=bad))
            assert r.status_code == 400
            assert r.json() == {"detail": "featured_rank_1_5"}
        r = client.post("/v1/categories", headers=h_m,
                        json=_cat_body(featured_rank=1))
        assert r.status_code == 409
        assert r.json() == {"detail": "featured_rank_taken"}


def test_create_claims_freed_rank(capsys):
    with make_client() as client:
        master = _login(client, capsys, "9000000001")
        h_m = _headers(master["token"])
        cats = client.get("/v1/categories").json()
        donor = [c for c in cats if c.get("featured_rank") == 5][0]
        r = client.put(f"/v1/categories/{donor['id']}", headers=h_m, json={
            "slug": donor["slug"], "name_en": donor["name_en"],
            "featured_rank": None, "problems": donor["problems"]})
        assert r.status_code == 200, r.text
        assert r.json()["featured_rank"] is None
        claimed = client.post("/v1/categories", headers=h_m,
                              json=_cat_body(featured_rank=5))
        assert claimed.status_code == 200, claimed.text
        assert claimed.json()["featured_rank"] == 5


def test_create_rejects_dup_and_ranged_problem_ranks(capsys):
    with make_client() as client:
        master = _login(client, capsys, "9000000001")
        h_m = _headers(master["token"])
        dup = [{"text_en": "A", "featured_rank": 2}, {"text_en": "B", "featured_rank": 2}]
        r = client.post("/v1/categories", headers=h_m, json=_cat_body(problems=dup))
        assert r.status_code == 409
        assert r.json() == {"detail": "problem_featured_dup"}
        bad = [{"text_en": "A", "featured_rank": 9}]
        r = client.post("/v1/categories", headers=h_m, json=_cat_body(problems=bad))
        assert r.status_code == 400
        assert r.json() == {"detail": "featured_rank_1_5"}


def test_update_roundtrip_and_errors(capsys):
    with make_client() as client:
        master = _login(client, capsys, "9000000001")
        h_m = _headers(master["token"])
        created = client.post("/v1/categories", headers=h_m, json=_cat_body()).json()
        cid = created["id"]
        old_prob = created["problems"][0]["id"]
        r = client.put(f"/v1/categories/{cid}", headers=h_m,
                       json=_cat_body(created["slug"], name_en="New",
                                      problems=[{"text_en": "Other", "sort_order": 0}]))
        assert r.status_code == 200, r.text
        assert r.json()["name_en"] == "New"
        assert r.json()["problems"][0]["id"] != old_prob
        r = client.put("/v1/categories/00000000-0000-0000-0000-000000000000",
                       headers=h_m, json=_cat_body())
        assert r.status_code == 404
        r = client.put(f"/v1/categories/{cid}", headers=h_m,
                       json=_cat_body(created["slug"], featured_rank=2))
        assert r.status_code == 409  # rank 2 belongs to a seed category


def test_category_write_rbac(capsys):
    with make_client() as client:
        for mobile in ("9000000004", "9000000003", "9000000002"):
            who = _login(client, capsys, mobile)
            h = _headers(who["token"])
            assert client.post("/v1/categories", headers=h,
                               json=_cat_body()).status_code == 403, mobile
            assert client.put("/v1/categories/x", headers=h,
                              json=_cat_body()).status_code == 403, mobile


def test_pricing_list_scopes_and_upsert(capsys):
    with make_client() as client:
        owner = _login(client, capsys, "9000000002")
        cust = _login(client, capsys, "9000000004")
        h_o, h_c = _headers(owner["token"]), _headers(cust["token"])
        rows = client.get("/v1/partner/pricing", headers=h_o).json()
        assert rows and set(rows[0]) == {"category_id", "enabled", "visit_charge"}
        r = client.get("/v1/partner/pricing", headers=h_c)
        assert r.status_code == 400
        assert r.json() == {"detail": "no_partner"}
        cat_id = rows[0]["category_id"]
        r = client.put("/v1/partner/pricing", headers=h_o,
                       json={"category_id": cat_id, "visit_charge": "777.00"})
        assert r.status_code == 200
        assert r.json()["visit_charge"] == "777.00"
        r = client.put("/v1/partner/pricing", headers=h_o,
                       json={"category_id": cat_id, "enabled": False,
                             "visit_charge": "777.00"})
        assert r.json()["enabled"] is False
        r = client.put("/v1/partner/pricing", headers=h_c,
                       json={"category_id": cat_id, "visit_charge": "1.00"})
        assert r.status_code == 403
