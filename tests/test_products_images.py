"""Products image endpoints: DB-blob fallback and R2 paths."""

import uuid
from io import BytesIO

from app.config import settings
from app.db import SessionLocal
from app.models import Product
from app.services import image_store
from tests.conftest import make_client
from tests.test_force_assign import _login

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _master(client, capsys):
    return _login(client, capsys, "9000000001")["token"]


def _payload():
    tag = uuid.uuid4().hex[:8]
    return {
        "name": f"Img Pump {tag}",
        "brand": "UTEST",
        "sku": f"UT-SKU-{tag}",
        "category": "Pumps",
    }


def test_create_and_serve_image_from_db_blobs(capsys):
    with make_client() as client:
        token = _master(client, capsys)
        r = client.post("/v1/products", data=_payload(),
                        files={"image": ("a.png", PNG, "image/png")},
                        headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["has_image"] is True
        img = client.get(f"/v1/products/{body['id']}/image")
        assert img.status_code == 200
        assert img.content == PNG
        assert img.headers["content-type"] == "image/png"


class _FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[Key] = Body

    def get_object(self, Bucket, Key):
        return {"Body": BytesIO(self.objects[Key])}


def _enable_r2(monkeypatch, fake):
    monkeypatch.setattr(settings, "r2_endpoint", "https://x.r2.test")
    monkeypatch.setattr(settings, "r2_bucket", "bkt")
    monkeypatch.setattr(settings, "r2_access_key_id", "id")
    monkeypatch.setattr(settings, "r2_secret_access_key", "secret")
    monkeypatch.setattr(image_store, "_client", lambda: fake)


def test_create_serves_from_r2_and_clears_blobs(capsys, monkeypatch):
    fake = _FakeS3()
    _enable_r2(monkeypatch, fake)
    with make_client() as client:
        token = _master(client, capsys)
        r = client.post("/v1/products", data=_payload(),
                        files={"image": ("a.png", PNG, "image/png")},
                        headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        img = client.get(f"/v1/products/{pid}/image")
        assert img.status_code == 200 and img.content == PNG
        db = SessionLocal()
        try:
            row = db.get(Product, pid)
            assert row.image_key == f"products/{pid}.png"
            assert row.image_bytes is None
        finally:
            db.close()


def test_update_replaces_image_in_r2(capsys, monkeypatch):
    fake = _FakeS3()
    _enable_r2(monkeypatch, fake)
    with make_client() as client:
        token = _master(client, capsys)
        r = client.post("/v1/products", data=_payload(),
                        headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        assert r.json()["has_image"] is False
        r = client.put(f"/v1/products/{pid}", data={"name": "Img Pump v2"},
                       files={"image": ("b.png", PNG, "image/png")},
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
        assert r.json()["has_image"] is True
        img = client.get(f"/v1/products/{pid}/image")
        assert img.status_code == 200 and img.content == PNG


def test_image_store_failure_is_502(capsys, monkeypatch):
    class _Broken(_FakeS3):
        def get_object(self, Bucket, Key):
            raise RuntimeError("r2 down")

    _enable_r2(monkeypatch, _Broken())
    with make_client() as client:
        token = _master(client, capsys)
        r = client.post("/v1/products", data=_payload(),
                        files={"image": ("a.png", PNG, "image/png")},
                        headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
        img = client.get(f"/v1/products/{r.json()['id']}/image")
        assert img.status_code == 502
