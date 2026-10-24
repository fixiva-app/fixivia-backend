from __future__ import annotations

from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import CommitRoute, get_db
from app.deps import current_user
from app.domain.otp import (
    OtpChallenge,
    OtpPurpose,
    make_challenge,
    verify_challenge,
)
from app.jobs.dispatch_job import dispatch_repool_open, with_busy_retry
from app.models import Notification, OtpChallengeRow, OtpCodeRow, User, utcnow
from app.services.otp_sender import default_otp_sender
from app.services.serializers import user_public

router = APIRouter(prefix="/v1", tags=["me"], route_class=CommitRoute)


@router.get("/me")
def me(user: User = Depends(current_user)) -> dict:
    return user_public(user)


class MePatch(BaseModel):
    full_name: str | None = None
    email: str | None = None


@router.patch("/me")
def patch_me(
    body: MePatch,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    if body.full_name is not None:
        name = body.full_name.strip()
        if not name or len(body.full_name) > 200:
            raise HTTPException(400, "invalid_name")
        user.full_name = name
    if body.email is not None:
        email = body.email.strip()
        if (email and "@" not in email) or len(email) > 200:
            raise HTTPException(400, "invalid_email")
        user.email = email
    return user_public(user)


def _normalize_mobile(raw: str) -> str:
    digits = "".join(ch for ch in (raw or "") if ch.isdigit())
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) != 10 or digits[0] not in "6789":
        raise HTTPException(400, "invalid_mobile")
    return digits


class MobileRequest(BaseModel):
    mobile: str


@router.post("/me/mobile/request")
def request_mobile_change(
    body: MobileRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    mobile = _normalize_mobile(body.mobile)
    if mobile == user.mobile:
        raise HTTPException(400, "same_mobile")
    if db.scalar(select(User.id).where(User.mobile == mobile)) is not None:
        raise HTTPException(409, "mobile_taken")
    challenge, code = make_challenge(
        OtpPurpose.MOBILE_CHANGE,
        mobile,
        settings.otp_pepper,
        settings.otp_ttl_minutes,
    )
    db.add(
        OtpChallengeRow(
            purpose=OtpPurpose.MOBILE_CHANGE.value,
            mobile=mobile,
            code_hash=challenge.code_hash,
            expires_at=challenge.expires_at,
        )
    )
    # TEMP-OTP: plaintext mirror for the admin read API.
    db.add(
        OtpCodeRow(
            purpose=OtpPurpose.MOBILE_CHANGE.value,
            mobile=mobile,
            code=code,
            expires_at=challenge.expires_at,
        )
    )
    default_otp_sender().send(OtpPurpose.MOBILE_CHANGE, mobile, code)
    return {"sent": True}


class MobileConfirm(BaseModel):
    mobile: str
    code: str = Field(min_length=6, max_length=6)


@router.post("/me/mobile/confirm")
def confirm_mobile_change(
    body: MobileConfirm,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    mobile = _normalize_mobile(body.mobile)
    row = db.scalar(
        select(OtpChallengeRow)
        .where(
            OtpChallengeRow.mobile == mobile,
            OtpChallengeRow.purpose == OtpPurpose.MOBILE_CHANGE.value,
            OtpChallengeRow.consumed_at.is_(None),
        )
        .order_by(OtpChallengeRow.expires_at.desc())
    )
    if row is None:
        raise HTTPException(400, "otp_not_found")
    ch = OtpChallenge(
        purpose=OtpPurpose.MOBILE_CHANGE,
        destination=mobile,
        code_hash=row.code_hash,
        expires_at=row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at.tzinfo is None else row.expires_at,
        consumed_at=row.consumed_at,
    )
    try:
        verify_challenge(ch, body.code, settings.otp_pepper)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    other = db.scalar(select(User.id).where(User.mobile == mobile))
    if other is not None and other != user.id:
        raise HTTPException(409, "mobile_taken")
    row.consumed_at = utcnow()
    # TEMP-OTP: retire the plaintext mirror on successful verify.
    mirror = db.scalar(
        select(OtpCodeRow)
        .where(
            OtpCodeRow.mobile == mobile,
            OtpCodeRow.purpose == OtpPurpose.MOBILE_CHANGE.value,
            OtpCodeRow.consumed_at.is_(None),
        )
        .order_by(OtpCodeRow.expires_at.desc())
    )
    if mirror is not None:
        mirror.consumed_at = utcnow()
    user.mobile = mobile
    return user_public(user)


@router.get("/notifications")
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(
        select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(100)
    )
    return [
        {
            "id": n.id,
            "type": n.type,
            "booking_id": n.booking_id,
            "payload": n.payload,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in rows
    ]


@router.post("/jobs/dispatch-repool")
def cron_repool(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    if user.role != "master_admin":
        from fastapi import HTTPException

        raise HTTPException(403, "forbidden")
    n = with_busy_retry("repool", lambda: dispatch_repool_open(db),
                          on_retry=db.rollback)
    return {"open_bookings": n}
