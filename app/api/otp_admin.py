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
    mobile: str | None = None,
    purpose: OtpPurpose | None = None,
    booking_id: str | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(_require_otp_admin),
) -> dict:
    if not (mobile or "").strip() and not booking_id:
        raise HTTPException(status_code=400, detail="mobile_or_booking_required")
    query = select(OtpCodeRow).where(OtpCodeRow.consumed_at.is_(None))
    if (mobile or "").strip():
        query = query.where(OtpCodeRow.mobile == mobile.strip())
    if purpose is not None:
        query = query.where(OtpCodeRow.purpose == purpose.value)
    if booking_id is not None:
        query = query.where(OtpCodeRow.booking_id == booking_id)
    row = db.scalar(query.order_by(OtpCodeRow.expires_at.desc()))
    if row is None or as_utc_aware(row.expires_at) < utcnow():
        raise HTTPException(status_code=404, detail="otp_not_found")
    audit(db, "otp_admin", "otp_code_read", "otp_code", row.id, mobile=row.mobile)
    return {
        "mobile": row.mobile,
        "purpose": row.purpose,
        "code": row.code,
        "expires_at": as_utc_aware(row.expires_at).isoformat(),
        "booking_id": row.booking_id,
    }
