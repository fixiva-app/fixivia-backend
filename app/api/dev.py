from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.db import CommitRoute, get_db
from app.dev_users import inject_payload
from app.domain.otp import OtpPurpose
from app.services.otp_sender import last_console_code

router = APIRouter(prefix="/v1/dev", tags=["dev"], route_class=CommitRoute)


def _require_dev() -> None:
    if settings.flavor != "dev":
        raise HTTPException(status_code=404, detail="not_found")


@router.post("/inject-users")
def inject_users(db: Session = Depends(get_db)) -> dict:
    """Create one of each role if missing. Dev flavor only."""
    _require_dev()
    return {"accounts": inject_payload(db)}


@router.get("/otp-code")
def read_otp_code(mobile: str, purpose: OtpPurpose = OtpPurpose.LOGIN) -> dict:
    """Return the last dev-sent OTP code. Dev flavor only (UI tests)."""
    _require_dev()
    code = last_console_code(purpose.value, mobile)
    if code is None:
        raise HTTPException(status_code=404, detail="otp_not_found")
    return {"mobile": mobile, "purpose": purpose.value, "code": code}
