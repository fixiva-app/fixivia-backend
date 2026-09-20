from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.dev_users import inject_payload

router = APIRouter(prefix="/v1/dev", tags=["dev"])


def _require_dev() -> None:
    if settings.flavor != "dev":
        raise HTTPException(status_code=404, detail="not_found")


@router.post("/inject-users")
def inject_users(db: Session = Depends(get_db)) -> dict:
    """Create one of each role if missing. Dev flavor only."""
    _require_dev()
    return {"accounts": inject_payload(db)}
