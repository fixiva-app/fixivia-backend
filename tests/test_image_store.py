"""Unit tests for product image storage (R2 with DB-blob fallback)."""

from io import BytesIO

from app.config import settings
from app.services import image_store


def test_r2_disabled_by_default():
    assert settings.r2_endpoint == ""
    assert image_store.r2_enabled() is False


def test_r2_enabled_only_when_fully_configured(monkeypatch):
    monkeypatch.setattr(settings, "r2_endpoint", "https://x.r2.test")
    monkeypatch.setattr(settings, "r2_bucket", "bkt")
    assert image_store.r2_enabled() is False
    monkeypatch.setattr(settings, "r2_access_key_id", "id")
    monkeypatch.setattr(settings, "r2_secret_access_key", "secret")
    assert image_store.r2_enabled() is True


def test_key_for_ext():
    assert image_store.key_for("pid", "image/webp") == "products/pid.webp"
    assert image_store.key_for("pid", "image/png") == "products/pid.png"
    assert image_store.key_for("pid", "image/jpeg") == "products/pid.jpg"
    assert image_store.key_for("pid", "application/octet-stream") == "products/pid"


class _FakeS3:
    def __init__(self):
        self.puts = []
        self.objects = {}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.puts.append({"bucket": Bucket, "key": Key, "body": Body,
                          "mime": ContentType})
        self.objects[Key] = Body

    def get_object(self, Bucket, Key):
        return {"Body": BytesIO(self.objects[Key])}


def test_put_and_get_roundtrip_via_fake_client(monkeypatch):
    fake = _FakeS3()
    monkeypatch.setattr(image_store, "_client", lambda: fake)
    key = image_store.put_product_image("p1", b"bytes", "image/png")
    assert key == "products/p1.png"
    assert fake.puts[0]["mime"] == "image/png"
    assert image_store.get_product_image(key) == b"bytes"
