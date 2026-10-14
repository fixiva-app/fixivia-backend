from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user, require_roles
from app.models import (
    AvailabilityBlock,
    Booking,
    Document,
    PartnerPincode,
    PayoutLedger,
    ServicePartnerCategory,
    ServicePartnerPincode,
    ServicePartnerProfile,
    User,
    utcnow,
)
from app.services.notify import audit

router = APIRouter(prefix="/v1", tags=["technicians"])


@router.get("/sp/profile")
def get_profile(user: User = Depends(require_roles("service_partner")), db: Session = Depends(get_db)) -> dict:
    p = db.get(ServicePartnerProfile, user.id)
    if p is None:
        raise HTTPException(404, "no_profile")
    pins = [r.pincode for r in db.scalars(select(ServicePartnerPincode).where(ServicePartnerPincode.user_id == user.id))]
    cats = [r.category_id for r in db.scalars(select(ServicePartnerCategory).where(ServicePartnerCategory.user_id == user.id))]
    return {
        "kyc_status": p.kyc_status,
        "pincodes": pins,
        "category_ids": cats,
        "aadhaar_document_id": p.aadhaar_document_id,
        "police_document_id": p.police_document_id,
    }


class ProfileBody(BaseModel):
    pincodes: list[str]
    category_ids: list[str]
    aadhaar_path: str | None = None
    police_path: str | None = None


@router.put("/sp/profile")
def update_profile(
    body: ProfileBody,
    user: User = Depends(require_roles("service_partner")),
    db: Session = Depends(get_db),
) -> dict:
    p = db.get(ServicePartnerProfile, user.id)
    if p is None:
        raise HTTPException(404, "no_profile")
    territory = {r.pincode for r in db.scalars(select(PartnerPincode).where(PartnerPincode.partner_id == p.partner_id))}
    for pin in body.pincodes:
        if pin not in territory:
            raise HTTPException(400, f"pincode_not_in_territory:{pin}")
    for row in db.scalars(select(ServicePartnerPincode).where(ServicePartnerPincode.user_id == user.id)):
        db.delete(row)
    for row in db.scalars(select(ServicePartnerCategory).where(ServicePartnerCategory.user_id == user.id)):
        db.delete(row)
    db.flush()
    for pin in body.pincodes:
        db.add(ServicePartnerPincode(user_id=user.id, pincode=pin))
    for cid in body.category_ids:
        db.add(ServicePartnerCategory(user_id=user.id, category_id=cid))
    if body.aadhaar_path:
        doc = Document(owner_type="service_partner", owner_id=user.id, doc_type="masked_aadhaar", storage_path=body.aadhaar_path)
        db.add(doc)
        db.flush()
        p.aadhaar_document_id = doc.id
    if body.police_path:
        doc = Document(owner_type="service_partner", owner_id=user.id, doc_type="police_verification", storage_path=body.police_path)
        db.add(doc)
        db.flush()
        p.police_document_id = doc.id
    p.kyc_status = "pending_partner_verification"
    audit(db, user.id, "kyc_submit", "sp_profile", user.id)
    pins = [r.pincode for r in db.scalars(select(ServicePartnerPincode).where(ServicePartnerPincode.user_id == user.id))]
    cats = [r.category_id for r in db.scalars(select(ServicePartnerCategory).where(ServicePartnerCategory.user_id == user.id))]
    return {
        "kyc_status": p.kyc_status,
        "pincodes": pins,
        "category_ids": cats,
        "aadhaar_document_id": p.aadhaar_document_id,
        "police_document_id": p.police_document_id,
    }


@router.get("/sp/roster")
def roster(user: User = Depends(require_roles("partner_owner", "partner_admin")), db: Session = Depends(get_db)) -> list[dict]:
    users = db.scalars(select(User).where(User.partner_id == user.partner_id, User.role == "service_partner"))
    out = []
    for u in users:
        p = db.get(ServicePartnerProfile, u.id)
        out.append(
            {
                "id": u.id,
                "full_name": u.full_name,
                "mobile": u.mobile,
                "kyc_status": p.kyc_status if p else "missing",
                "status": u.status,
            }
        )
    return out


class KycBody(BaseModel):
    status: str


@router.post("/sp/{sp_id}/kyc")
def review_kyc(
    sp_id: str,
    body: KycBody,
    user: User = Depends(require_roles("partner_owner", "partner_admin")),
    db: Session = Depends(get_db),
) -> dict:
    p = db.get(ServicePartnerProfile, sp_id)
    if p is None or p.partner_id != user.partner_id:
        raise HTTPException(404, "not_found")
    if body.status not in ("approved", "rejected"):
        raise HTTPException(400, "bad_status")
    p.kyc_status = body.status
    p.reviewed_by = user.id
    p.reviewed_at = utcnow()
    audit(db, user.id, "kyc_review", "sp_profile", sp_id, status=body.status)
    return {"user_id": sp_id, "kyc_status": p.kyc_status}


class BlockBody(BaseModel):
    block_date: date
    slot: str | None = None


@router.post("/sp/availability")
def add_block(body: BlockBody, user: User = Depends(require_roles("service_partner")), db: Session = Depends(get_db)) -> dict:
    row = AvailabilityBlock(user_id=user.id, block_date=body.block_date, slot=body.slot)
    db.add(row)
    db.flush()
    return {"id": row.id}


@router.get("/sp/availability")
def list_blocks(user: User = Depends(require_roles("service_partner")), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(AvailabilityBlock).where(AvailabilityBlock.user_id == user.id))
    return [{"id": r.id, "block_date": r.block_date.isoformat(), "slot": r.slot} for r in rows]


@router.get("/sp/schedule")
def schedule(
    user: User = Depends(require_roles("service_partner")),
    db: Session = Depends(get_db),
    on: date | None = None,
) -> dict:
    day = on or (date.today() + timedelta(days=1))
    rows = list(
        db.scalars(
            select(Booking).where(
                Booking.assigned_sp_id == user.id,
                Booking.service_date == day,
                Booking.status.in_(("assigned", "en_route", "in_progress")),
            )
        )
    )
    morning = sorted([b for b in rows if b.slot == "morning"], key=lambda b: b.pincode)
    evening = sorted([b for b in rows if b.slot == "evening"], key=lambda b: b.pincode)
    return {
        "date": day.isoformat(),
        "morning": [_mini(b) for b in morning],
        "evening": [_mini(b) for b in evening],
    }


def _mini(b: Booking) -> dict:
    return {"id": b.id, "pincode": b.pincode, "status": b.status, "category_id": b.category_id}


@router.get("/sp/earnings")
def earnings(user: User = Depends(require_roles("service_partner")), db: Session = Depends(get_db)) -> dict:
    rows = list(db.scalars(select(PayoutLedger).where(PayoutLedger.service_partner_id == user.id)))
    pending = Decimal("0")
    paid = Decimal("0")
    for r in rows:
        if r.status == "paid":
            paid += r.amount
        else:
            pending += r.amount
    return {"pending": str(pending), "paid": str(paid), "jobs": len(rows)}


@router.post("/payouts/{payout_id}/paid")
def mark_payout_paid(
    payout_id: str,
    user: User = Depends(require_roles("partner_owner", "partner_admin")),
    db: Session = Depends(get_db),
) -> dict:
    row = db.get(PayoutLedger, payout_id)
    if row is None or row.partner_id != user.partner_id:
        raise HTTPException(404, "not_found")
    row.status = "paid"
    row.paid_at = utcnow()
    return {"id": row.id, "status": row.status}
