"""Product image storage: R2 object store with DB-blob fallback.

R2 is active only when all four settings are configured (production).
Otherwise images stay in Product.image_bytes (local dev + tests), and
rows that already carry an image_key keep serving from R2.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import settings

_MIME_EXT = {
    "image/webp": ".webp",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
}


def r2_enabled() -> bool:
    return bool(
        settings.r2_endpoint
        and settings.r2_bucket
        and settings.r2_access_key_id
        and settings.r2_secret_access_key
    )


@lru_cache(maxsize=1)
def _client():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )


def key_for(product_id: str, mime: str) -> str:
    return f"products/{product_id}{_MIME_EXT.get(mime, '')}"


def put_product_image(product_id: str, data: bytes, mime: str) -> str:
    """Upload bytes; returns the stored object key. Raises on failure."""
    key = key_for(product_id, mime)
    _client().put_object(
        Bucket=settings.r2_bucket, Key=key, Body=data, ContentType=mime or "application/octet-stream"
    )
    return key


def get_product_image(key: str) -> bytes:
    """Download bytes by key. Raises on failure."""
    resp = _client().get_object(Bucket=settings.r2_bucket, Key=key)
    return resp["Body"].read()
