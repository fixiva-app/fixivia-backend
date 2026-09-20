from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import current_user, require_roles
from app.domain.otp import generate_code, hash_code
from app.models import (
    Partner,
    PartnerAdminRequest,
    PartnerInvite,
    PartnerPincode,
    Pincode,
    User,
    utcnow,
)
from app.services.notify import audit
from app.services.serializers import user_public

router = APIRouter(prefix="/v1", tags=["partners"])


class InviteOut(BaseModel):
    id: str
    token: str
    expires_at: str


@router.post("/partners/invites")
def create_invite(
    user: User = Depends(require_roles("master_admin")),
    db: Session = Depends(get_db),
) -> dict:
    token = generate_code() + generate_code()
    row = PartnerInvite(
        token_hash=hash_code(token, settings.otp_pepper),
        token_plain_dev=token,
        expires_at=utcnow() + timedelta(days=14),
        created_by=user.id,
    )
    db.add(row)
    db.flush()
    print(f"[EMAIL] partner invite token={token} from master={user.mobile}", flush=True)
    audit(db, user.id, "invite_create", "partner_invite", row.id)
    return {"id": row.id, "token": token, "expires_at": row.expires_at.isoformat()}


class ApplyBody(BaseModel):
    invite_token: str
    trade_name: str
    org_type: str = "company"
    legal_name: str | None = None
    gstin: str | None = None
    cin: str | None = None
    office_address: str = ""
    office_pincode: str
    personal_email: str
    company_email: str | None = None
    billing_cycle: str = "monthly"


@router.post("/partners/apply")
def apply_partner(body: ApplyBody, db: Session = Depends(get_db)) -> dict:
    token_h = hash_code(body.invite_token, settings.otp_pepper)
    invite = db.scalar(select(PartnerInvite).where(PartnerInvite.token_hash == token_h))
    if invite is None or invite.expires_at < utcnow():
        raise HTTPException(400, "invite_invalid")
    if invite.used_by_partner_id:
        raise HTTPException(409, "invite_used")
    pin = db.get(Pincode, body.office_pincode)
    if pin is None:
        raise HTTPException(400, "unknown_pincode")
    partner = Partner(
        org_type=body.org_type,
        trade_name=body.trade_name,
        legal_name=body.legal_name,
        gstin=body.gstin,
        cin=body.cin,
        status="submitted",
        office_address=body.office_address,
        office_pincode=body.office_pincode,
        personal_email=body.personal_email,
        company_email=body.company_email,
        billing_cycle=body.billing_cycle,
    )
    db.add(partner)
    db.flush()
    invite.used_by_partner_id = partner.id
    audit(db, None, "partner_apply", "partner", partner.id)
    return {"partner_id": partner.id, "status": partner.status}


@router.get("/partners/public")
def public_partners(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Partner).where(Partner.status == "approved"))
    return [{"id": p.id, "trade_name": p.trade_name} for p in rows]


@router.get("/partners")
def list_partners(
    user: User = Depends(require_roles("master_admin")),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.scalars(select(Partner).order_by(Partner.created_at.desc()))
    return [_partner_json(p) for p in rows]


@router.get("/partners/me")
def my_partner(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not user.partner_id:
        raise HTTPException(400, "no_partner")
    p = db.get(Partner, user.partner_id)
    if p is None:
        raise HTTPException(404, "not_found")
    return _partner_json(p, db)


class ReviewBody(BaseModel):
    status: str
    pincodes: list[str] = []
    license_fee_amount: Decimal | None = None
    commission_percent: Decimal | None = None


@router.post("/partners/{partner_id}/review")
def review_partner(
    partner_id: str,
    body: ReviewBody,
    user: User = Depends(require_roles("master_admin")),
    db: Session = Depends(get_db),
) -> dict:
    partner = db.get(Partner, partner_id)
    if partner is None:
        raise HTTPException(404, "not_found")
    if body.status not in ("approved", "rejected", "suspended", "under_review"):
        raise HTTPException(400, "bad_status")
    if body.status == "approved":
        _assign_pincodes(db, partner, body.pincodes)
        if body.license_fee_amount is not None:
            partner.license_fee_amount = body.license_fee_amount
        if body.commission_percent is not None:
            partner.commission_percent = body.commission_percent
        print(
            f"[EMAIL] credentials partner={partner.trade_name} to={partner.personal_email},{partner.company_email} "
            f"owner must login with mobile OTP",
            flush=True,
        )
    partner.status = body.status
    audit(db, user.id, "partner_review", "partner", partner.id, status=body.status)
    return _partner_json(partner, db)


def _assign_pincodes(db: Session, partner: Partner, pincodes: list[str]) -> None:
    for code in pincodes:
        if db.get(Pincode, code) is None:
            raise HTTPException(400, f"unknown_pincode:{code}")
        taken = db.scalar(
            select(PartnerPincode.partner_id)
            .join(Partner, Partner.id == PartnerPincode.partner_id)
            .where(PartnerPincode.pincode == code, Partner.status == "approved", Partner.id != partner.id)
        )
        if taken:
            raise HTTPException(409, f"pincode_taken:{code}")
    existing = list(db.scalars(select(PartnerPincode).where(PartnerPincode.partner_id == partner.id)))
    for row in existing:
        db.delete(row)
    db.flush()
    for code in pincodes:
        db.add(PartnerPincode(partner_id=partner.id, pincode=code))


class AdminReqBody(BaseModel):
    full_name: str
    mobile: str
    email: str = ""


@router.post("/partner-admin-requests")
def request_admin(
    body: AdminReqBody,
    user: User = Depends(require_roles("partner_owner")),
    db: Session = Depends(get_db),
) -> dict:
    row = PartnerAdminRequest(
        partner_id=user.partner_id,
        full_name=body.full_name,
        mobile=body.mobile,
        email=body.email,
        requested_by=user.id,
    )
    db.add(row)
    db.flush()
    return {"id": row.id, "status": row.status}


@router.get("/partner-admin-requests")
def list_admin_requests(
    user: User = Depends(require_roles("master_admin", "partner_owner")),
    db: Session = Depends(get_db),
) -> list[dict]:
    q = select(PartnerAdminRequest)
    if user.role != "master_admin":
        q = q.where(PartnerAdminRequest.partner_id == user.partner_id)
    rows = db.scalars(q.order_by(PartnerAdminRequest.created_at.desc()))
    return [
        {
            "id": r.id,
            "partner_id": r.partner_id,
            "full_name": r.full_name,
            "mobile": r.mobile,
            "email": r.email,
            "status": r.status,
            "created_user_id": r.created_user_id,
        }
        for r in rows
    ]


@router.post("/partner-admin-requests/{req_id}/review")
def review_admin_request(
    req_id: str,
    body: ReviewBody,
    user: User = Depends(require_roles("master_admin")),
    db: Session = Depends(get_db),
) -> dict:
    row = db.get(PartnerAdminRequest, req_id)
    if row is None:
        raise HTTPException(404, "not_found")
    if body.status not in ("approved", "rejected"):
        raise HTTPException(400, "bad_status")
    row.status = body.status
    row.reviewed_by = user.id
    if body.status == "approved":
        existing = db.scalar(select(User).where(User.mobile == row.mobile))
        if existing:
            raise HTTPException(409, "mobile_taken")
        admin = User(
            role="partner_admin",
            partner_id=row.partner_id,
            full_name=row.full_name,
            mobile=row.mobile,
            email=row.email,
            status="active",
        )
        db.add(admin)
        db.flush()
        row.created_user_id = admin.id
        print(f"[EMAIL] partner admin credentials mobile={row.mobile} email={row.email} login via OTP", flush=True)
    return {"id": row.id, "status": row.status, "created_user_id": row.created_user_id}


@router.get("/pincodes")
def list_pincodes(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Pincode).order_by(Pincode.pincode))
    return [{"pincode": p.pincode, "district": p.district, "locality": p.locality, "state": p.state} for p in rows]


def _partner_json(p: Partner, db: Session | None = None) -> dict:
    pins = []
    if db is not None:
        pins = [r.pincode for r in db.scalars(select(PartnerPincode).where(PartnerPincode.partner_id == p.id))]
    return {
        "id": p.id,
        "trade_name": p.trade_name,
        "legal_name": p.legal_name,
        "status": p.status,
        "org_type": p.org_type,
        "gstin": p.gstin,
        "office_pincode": p.office_pincode,
        "license_fee_amount": str(p.license_fee_amount),
        "commission_percent": str(p.commission_percent),
        "pincodes": pins,
        "personal_email": p.personal_email,
        "company_email": p.company_email,
    }
