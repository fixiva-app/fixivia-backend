from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.domain.otp import OtpPurpose, make_challenge, verify_challenge
from app.models import OtpChallengeRow, PartnerInvite, ServicePartnerProfile, User, utcnow
from app.services.otp_sender import ConsoleOtpSender
from app.services.serializers import user_public
from app.services.tokens import ROLES, issue_token
from app.domain.otp import hash_code

router = APIRouter(prefix="/v1/otp", tags=["otp"])
_sender = ConsoleOtpSender()


class OtpRequest(BaseModel):
    mobile: str = Field(min_length=10, max_length=16)
    purpose: OtpPurpose


class OtpVerify(BaseModel):
    mobile: str
    purpose: OtpPurpose
    code: str = Field(min_length=6, max_length=6)
    full_name: str | None = None
    role: str | None = None
    locale: str = "en"
    email: str | None = None
    partner_id: str | None = None
    invite_token: str | None = None


@router.post("/request")
def request_otp(body: OtpRequest, db: Session = Depends(get_db)) -> dict:
    if body.purpose == OtpPurpose.START_WORK:
        raise HTTPException(400, "start_work otp is created on accept, not requested by the client")
    challenge, code = make_challenge(
        body.purpose,
        body.mobile,
        settings.otp_pepper,
        settings.otp_ttl_minutes,
    )
    db.add(
        OtpChallengeRow(
            purpose=body.purpose.value,
            mobile=body.mobile,
            code_hash=challenge.code_hash,
            expires_at=challenge.expires_at,
        )
    )
    _sender.send(body.purpose, body.mobile, code)
    return {"sent": True}


@router.post("/verify")
def verify_otp(body: OtpVerify, db: Session = Depends(get_db)) -> dict:
    if body.purpose == OtpPurpose.START_WORK:
        raise HTTPException(400, "use the start-work endpoint after accept")
    row = db.scalar(
        select(OtpChallengeRow)
        .where(
            OtpChallengeRow.mobile == body.mobile,
            OtpChallengeRow.purpose == body.purpose.value,
            OtpChallengeRow.consumed_at.is_(None),
        )
        .order_by(OtpChallengeRow.expires_at.desc())
    )
    if row is None:
        raise HTTPException(400, "otp_not_found")
    from app.domain.otp import OtpChallenge

    ch = OtpChallenge(
        purpose=body.purpose,
        destination=body.mobile,
        code_hash=row.code_hash,
        expires_at=row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at.tzinfo is None else row.expires_at,
        consumed_at=row.consumed_at,
    )
    try:
        verify_challenge(ch, body.code, settings.otp_pepper)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    row.consumed_at = utcnow()

    user = db.scalar(select(User).where(User.mobile == body.mobile))
    if body.purpose == OtpPurpose.REGISTER:
        if user:
            raise HTTPException(409, "mobile_taken")
        role = body.role or "customer"
        if role not in ROLES:
            raise HTTPException(400, "invalid_role")
        partner_id = body.partner_id
        if role == "partner_owner":
            if not body.invite_token:
                raise HTTPException(400, "invite_required")
            token_h = hash_code(body.invite_token, settings.otp_pepper)
            invite = db.scalar(select(PartnerInvite).where(PartnerInvite.token_hash == token_h))
            if invite is None or invite.used_by_partner_id or invite.expires_at < utcnow():
                raise HTTPException(400, "invite_invalid")
            partner_id = invite.used_by_partner_id
        user = User(
            role=role,
            partner_id=partner_id,
            full_name=body.full_name or "User",
            mobile=body.mobile,
            email=body.email or "",
            locale=body.locale,
            status="active",
        )
        db.add(user)
        db.flush()
        if role == "service_partner":
            if not partner_id:
                raise HTTPException(400, "partner_id_required")
            db.add(ServicePartnerProfile(user_id=user.id, partner_id=partner_id))
        if role == "partner_owner" and body.invite_token:
            token_h = hash_code(body.invite_token, settings.otp_pepper)
            invite = db.scalar(select(PartnerInvite).where(PartnerInvite.token_hash == token_h))
            if invite:
                from app.models import Partner

                partner = db.get(Partner, invite.used_by_partner_id) if invite.used_by_partner_id else None
                if partner:
                    partner.primary_owner_user_id = user.id
    elif not user:
        raise HTTPException(404, "user_not_found")

    token = issue_token(user_id=user.id, role=user.role, partner_id=user.partner_id)
    return {"token": token, "user": user_public(user)}
