"""One-time move: product DB blobs -> R2 objects.

Usage (needs R2 + DATABASE_URL in env):
    cd backend
    DATABASE_URL='postgresql+psycopg://...' \
    R2_ENDPOINT=https://<account>.r2.cloudflarestorage.com R2_BUCKET=fixiva \
    R2_ACCESS_KEY_ID=... R2_SECRET_ACCESS_KEY=... \
    .venv/bin/python scripts/migrate_images_to_r2.py [--commit]

Dry-run by default. With --commit, uploads each row's bytes, sets
image_key, and clears image_bytes. Idempotent: rows already keyed are
skipped, so re-running is safe.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal, init_db  # noqa: E402
from app.models import Product  # noqa: E402
from app.services import image_store  # noqa: E402


def main() -> int:
    commit = "--commit" in sys.argv[1:]
    if not image_store.r2_enabled():
        print("R2 not configured (need R2_ENDPOINT/R2_BUCKET/R2_ACCESS_KEY_ID/R2_SECRET_ACCESS_KEY)")
        return 2
    init_db()
    db = SessionLocal()
    try:
        rows = list(
            db.scalars(
                select(Product).where(
                    Product.image_bytes.is_not(None),
                    Product.image_key.is_(None),
                )
            )
        )
        print(f"{len(rows)} rows with blobs and no key")
        moved, failed = 0, 0
        for p in rows:
            if not commit:
                continue
            try:
                key = image_store.put_product_image(p.id, p.image_bytes, p.image_mime or "")
                p.image_key = key
                p.image_bytes = None
                db.flush()
                moved += 1
            except Exception as exc:
                print(f"  FAIL {p.sku}: {exc!r}")
                db.rollback()
                failed += 1
        if commit:
            db.commit()
            print(f"moved: {moved}, failed: {failed}")
        else:
            print("dry run — pass --commit to move")
        return 0 if failed == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
