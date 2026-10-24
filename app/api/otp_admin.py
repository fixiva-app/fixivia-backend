# TEMP-OTP: temporary admin OTP read API. Internal workaround until real
# SMS/WhatsApp delivery ships — then DELETE this file, the OtpCodeRow
# model, the config creds, and the TEMP-OTP blocks in auth.py / me.py.
"""GET /v1/admin/otp-code — read the active OTP for a mobile.

Header auth (X-Otp-Admin-User / X-Otp-Admin-Pass, env-configurable).
Returns the latest unexpired, unconsumed code. Every read is audited.
"""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import CommitRoute, get_db
from app.domain.otp import OtpPurpose
from app.models import OtpCodeRow, as_utc_aware, utcnow
from app.services.notify import audit

router = APIRouter(prefix="/v1/admin", tags=["otp-admin"], route_class=CommitRoute)


def _require_otp_admin(
    user: str | None = Header(default=None, alias="X-Otp-Admin-User"),
    password: str | None = Header(default=None, alias="X-Otp-Admin-Pass"),
) -> None:
    ok = (
        user is not None
        and password is not None
        and hmac.compare_digest(user, settings.otp_admin_user)
        and hmac.compare_digest(password, settings.otp_admin_pass)
    )
    if not ok:
        raise HTTPException(status_code=401, detail="otp_admin_denied")


@router.get("/otp-code")
def read_active_otp(
    mobile: str,
    purpose: OtpPurpose = OtpPurpose.LOGIN,
    db: Session = Depends(get_db),
    _: None = Depends(_require_otp_admin),
) -> dict:
    row = db.scalar(
        select(OtpCodeRow)
        .where(
            OtpCodeRow.mobile == mobile.strip(),
            OtpCodeRow.purpose == purpose.value,
            OtpCodeRow.consumed_at.is_(None),
        )
        .order_by(OtpCodeRow.expires_at.desc())
    )
    if row is None or as_utc_aware(row.expires_at) < utcnow():
        raise HTTPException(status_code=404, detail="otp_not_found")
    audit(db, "otp_admin", "otp_code_read", "otp_code", row.id, mobile=mobile.strip())
    return {
        "mobile": mobile.strip(),
        "purpose": purpose.value,
        "code": row.code,
        "expires_at": as_utc_aware(row.expires_at).isoformat(),
    }
