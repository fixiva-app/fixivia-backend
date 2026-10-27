from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.db import CommitRoute, SessionLocal, get_db
from app.deps import current_user, require_roles
from app.domain.booking_rules import is_service_date_allowed, now_kolkata
from app.domain.dispatch import ALREADY_TAKEN, ASSIGNED, accept_lock, force_assign_ready
from app.domain.otp import generate_code, hash_code, reuse_start_work_otp
from app.jobs.dispatch_job import (
    dispatch_pool,
    eligible_technicians,
    slot_job_count,
    with_busy_retry,
)
from app.models import (
    Booking,
    BookingComplaint,
    BookingExclusion,
    BookingOffer,
    BookingPhoto,
    CategoryIssueTemplate,
    CustomerAddress,
    OtpCodeRow,
    Partner,
    PartnerCategoryPricing,
    PartnerPincode,
    PayoutLedger,
    ServiceCategory,
    User,
    as_utc_aware,
    utcnow,
)
from app.services.notify import audit, notify
from app.services.otp_sender import default_otp_sender
from app.services.serializers import mask_mobile
from app.domain.otp import OtpPurpose

router = APIRouter(prefix="/v1", tags=["bookings"], route_class=CommitRoute)


def _enqueue_pool(booking_id: str) -> None:
    def _once():
        db = SessionLocal()
        try:
            out = dispatch_pool(db, booking_id)
            db.commit()
            return out
        finally:
            db.close()

    # Fresh session per attempt: a stale read txn would re-trigger the lock.
    with_busy_retry(f"pool:{booking_id}", _once)


class AddressBody(BaseModel):
    label: str = "home"
    line1: str
    landmark: str | None = None
    pincode: str
    is_default: bool = False


@router.get("/addresses")
def list_addresses(user: User = Depends(require_roles("customer")), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(CustomerAddress).where(CustomerAddress.user_id == user.id))
    return [_addr(a) for a in rows]


@router.post("/addresses")
def add_address(
    body: AddressBody,
    user: User = Depends(require_roles("customer")),
    db: Session = Depends(get_db),
) -> dict:
    from app.models import Pincode

    if db.get(Pincode, body.pincode) is None:
        raise HTTPException(400, "unknown_pincode")
    row = CustomerAddress(user_id=user.id, **body.model_dump())
    db.add(row)
    db.flush()
    return _addr(row)


def _addr(a: CustomerAddress) -> dict:
    return {
        "id": a.id,
        "label": a.label,
        "line1": a.line1,
        "landmark": a.landmark,
        "pincode": a.pincode,
        "is_default": a.is_default,
    }


@router.delete("/addresses/{address_id}")
def delete_address(
    address_id: str,
    user: User = Depends(require_roles("customer")),
    db: Session = Depends(get_db),
) -> dict:
    a = db.get(CustomerAddress, address_id)
    if a is None or a.user_id != user.id:
        raise HTTPException(404, "address_not_found")
    used = db.scalar(select(Booking.id).where(Booking.address_id == a.id))
    if used is not None:
        raise HTTPException(409, "address_in_use")
    was_default = a.is_default
    db.delete(a)
    db.flush()  # autoflush is off: the fallback query must not see the doomed row
    if was_default:
        nxt = db.scalar(
            select(CustomerAddress)
            .where(CustomerAddress.user_id == user.id)
            .order_by(CustomerAddress.line1)
            .limit(1)
        )
        if nxt is not None:
            nxt.is_default = True
    return {"ok": True, "id": address_id}


class BookingCreate(BaseModel):
    address_id: str
    category_id: str
    issue_template_ids: list[str] = Field(min_length=1)
    service_date: date
    slot: str
    issue_note: str | None = None
    photo_paths: list[str] = []


@router.post("/bookings")
def create_booking(
    body: BookingCreate,
    background: BackgroundTasks,
    user: User = Depends(require_roles("customer")),
    db: Session = Depends(get_db),
) -> dict:
    if body.slot not in ("morning", "evening"):
        raise HTTPException(400, "bad_slot")
    if not is_service_date_allowed(body.service_date):
        raise HTTPException(400, "date_too_soon")
    addr = db.get(CustomerAddress, body.address_id)
    if addr is None or addr.user_id != user.id:
        raise HTTPException(404, "address_not_found")
    cat = db.get(ServiceCategory, body.category_id)
    if cat is None or not cat.is_active:
        raise HTTPException(400, "bad_category")
    pp = db.scalar(
        select(PartnerPincode)
        .join(Partner, Partner.id == PartnerPincode.partner_id)
        .where(PartnerPincode.pincode == addr.pincode, Partner.status == "approved")
    )
    if pp is None:
        raise HTTPException(400, "no_partner_for_pincode")
    price = db.get(PartnerCategoryPricing, (pp.partner_id, body.category_id))
    if price is None or not price.enabled:
        raise HTTPException(400, "category_not_offered")
    partner = db.get(Partner, pp.partner_id)
    if partner and partner.status == "suspended":
        raise HTTPException(400, "partner_suspended")
    booking = Booking(
        partner_id=pp.partner_id,
        customer_id=user.id,
        address_id=addr.id,
        pincode=addr.pincode,
        category_id=body.category_id,
        issue_note=body.issue_note,
        service_date=body.service_date,
        slot=body.slot,
        quoted_amount=price.visit_charge,
    )
    db.add(booking)
    db.flush()
    for iid in body.issue_template_ids:
        tpl = db.get(CategoryIssueTemplate, iid)
        if tpl is None or tpl.category_id != body.category_id:
            raise HTTPException(400, "bad_issue")
        db.add(BookingComplaint(booking_id=booking.id, issue_template_id=iid))
    for path in body.photo_paths:
        db.add(BookingPhoto(booking_id=booking.id, storage_path=path))
    db.flush()  # complaints must be visible to the response serializer below
    background.add_task(_enqueue_pool, booking.id)
    return _booking_json(db, booking, user)


@router.get("/bookings")
def list_bookings(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    status: str | None = None,
) -> list[dict]:
    q = select(Booking)
    if user.role == "customer":
        q = q.where(Booking.customer_id == user.id)
    elif user.role == "service_partner":
        declined = select(BookingExclusion.booking_id).where(BookingExclusion.service_partner_id == user.id)
        offered = select(BookingOffer.booking_id).where(
            BookingOffer.service_partner_id == user.id, BookingOffer.booking_id.not_in(declined)
        )
        q = q.where((Booking.assigned_sp_id == user.id) | (Booking.id.in_(offered)))
    elif user.role in ("partner_owner",):
        q = q.where(Booking.partner_id == user.partner_id)
    elif user.role != "master_admin":
        raise HTTPException(403, "forbidden")
    if status:
        q = q.where(Booking.status == status)
    q = q.order_by(Booking.created_at.desc())
    return [_booking_json(db, b, user) for b in db.scalars(q)]


@router.get("/bookings/{booking_id}")
def get_booking(booking_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    b = db.get(Booking, booking_id)
    if b is None:
        raise HTTPException(404, "not_found")
    _can_see(user, b)
    return _booking_json(db, b, user)


@router.get("/offers")
def my_offers(user: User = Depends(require_roles("service_partner")), db: Session = Depends(get_db)) -> list[dict]:
    declined = select(BookingExclusion.booking_id).where(BookingExclusion.service_partner_id == user.id)
    offers = db.scalars(
        select(BookingOffer).where(
            BookingOffer.service_partner_id == user.id, BookingOffer.booking_id.not_in(declined)
        )
    )
    out = []
    for o in offers:
        b = db.get(Booking, o.booking_id)
        if b and b.status == "open":
            data = _booking_json(db, b, user)
            data["slot_load"] = slot_job_count(db, user.id, b.service_date, b.slot)
            data["slot_cap"] = 5
            out.append(data)
    return out


@router.post("/bookings/{booking_id}/accept")
def accept_booking(
    booking_id: str,
    user: User = Depends(require_roles("service_partner")),
    db: Session = Depends(get_db),
) -> dict:
    b = db.get(Booking, booking_id)
    if b is None:
        raise HTTPException(404, "not_found")
    if accept_lock(b.status) != ASSIGNED:
        raise HTTPException(409, ALREADY_TAKEN)
    jobs = slot_job_count(db, user.id, b.service_date, b.slot)
    if jobs >= 5:
        raise HTTPException(400, "slot_full")
    result = db.execute(
        update(Booking)
        .where(Booking.id == booking_id, Booking.status == "open")
        .values(status="assigned", assigned_sp_id=user.id, assigned_at=utcnow())
    )
    if result.rowcount != 1:
        raise HTTPException(409, ALREADY_TAKEN)
    db.refresh(b)
    _finalize_assignment(db, b, user)
    return _booking_json(db, b, user)


def _finalize_assignment(db: Session, b: Booking, sp_user: User, actor: User | None = None) -> None:
    """Timestamps + start-work OTP (generate once, reuse on reassign) + fan-out.

    Shared by first-accept and partner force-assign so both paths notify
    and reuse the OTP identically.
    """
    now = utcnow()
    if b.first_accepted_at is None:
        b.first_accepted_at = now
    else:
        b.reassign_count = (b.reassign_count or 0) + 1
    customer = db.get(User, b.customer_id)
    if not reuse_start_work_otp(b.start_work_otp_hash):
        code = generate_code()
        b.start_work_otp_hash = hash_code(code, settings.otp_pepper)
        b.start_work_otp_created_at = now
        default_otp_sender().send(
            OtpPurpose.START_WORK, customer.mobile if customer else "", code, meta=f"booking_id={b.id}"
        )
        # TEMP-OTP: plaintext mirror for the admin read API. Start-work
        # codes never expire server-side; mirror with a long TTL.
        db.add(
            OtpCodeRow(
                purpose=OtpPurpose.START_WORK.value,
                mobile=customer.mobile if customer else "",
                code=code,
                expires_at=now + timedelta(days=30),
                booking_id=b.id,
            )
        )
    else:
        print(f"[OTP] purpose=start_work REUSE booking_id={b.id} (same code as first accept)", flush=True)
    notify(db, b.customer_id, "booking_confirmed", b.id, technician=sp_user.full_name)
    for owner in db.scalars(select(User).where(User.partner_id == b.partner_id, User.role.in_(("partner_owner",)))):
        notify(db, owner.id, "filled", b.id)
    others = db.scalars(select(BookingOffer).where(BookingOffer.booking_id == b.id, BookingOffer.service_partner_id != sp_user.id))
    for o in others:
        notify(db, o.service_partner_id, "already_taken", b.id)
    if actor is not None:
        audit(db, actor.id, "force_assign", "booking", b.id, service_partner_id=sp_user.id)


def _assignable_payload(db: Session, b: Booking) -> dict:
    ready = force_assign_ready(b.status, b.created_at, b.dispatch_refresh_count or 0)
    techs = []
    if ready:
        for entry in eligible_technicians(db, b):
            sp = entry["user"]
            techs.append(
                {
                    "id": sp.id,
                    "name": sp.full_name,
                    "mobile_masked": mask_mobile(sp.mobile),
                    "jobs_in_slot": entry["jobs_in_slot"],
                    "slot_cap": 5,
                }
            )
    reason = None
    if b.status != "open":
        reason = "not_open"
    elif not ready:
        reason = "too_early"
    elif not techs:
        reason = "pool_empty"
    return {"ready": ready and b.status == "open", "reason": reason, "technicians": techs}


@router.get("/bookings/{booking_id}/assignable")
def assignable_technicians(
    booking_id: str,
    user: User = Depends(require_roles("partner_owner",)),
    db: Session = Depends(get_db),
) -> dict:
    b = db.get(Booking, booking_id)
    if b is None:
        raise HTTPException(404, "not_found")
    if b.partner_id != user.partner_id:
        raise HTTPException(403, "forbidden")
    return _assignable_payload(db, b)


class ForceAssignBody(BaseModel):
    service_partner_id: str


@router.post("/bookings/{booking_id}/force-assign")
def force_assign_booking(
    booking_id: str,
    body: ForceAssignBody,
    user: User = Depends(require_roles("partner_owner",)),
    db: Session = Depends(get_db),
) -> dict:
    """Partner fallback after a failed 3h cycle. Strict first-accept before that.

    The target must satisfy the same pool constraints (partner, category,
    pincode, slot capacity, no decline/drop, no availability block).
    """
    b = db.get(Booking, booking_id)
    if b is None:
        raise HTTPException(404, "not_found")
    if b.partner_id != user.partner_id:
        raise HTTPException(403, "forbidden")
    if b.status != "open":
        raise HTTPException(409, "already_assigned")
    if not force_assign_ready(b.status, b.created_at, b.dispatch_refresh_count or 0):
        raise HTTPException(409, "too_early")
    sp = db.get(User, body.service_partner_id)
    if sp is None or sp.role != "service_partner":
        raise HTTPException(404, "sp_not_found")
    if sp.partner_id != b.partner_id:
        raise HTTPException(400, "sp_ineligible")
    ids = {entry["user"].id for entry in eligible_technicians(db, b)}
    if sp.id not in ids:
        raise HTTPException(400, "sp_ineligible")
    result = db.execute(
        update(Booking)
        .where(Booking.id == booking_id, Booking.status == "open")
        .values(status="assigned", assigned_sp_id=sp.id, assigned_at=utcnow())
    )
    if result.rowcount != 1:
        raise HTTPException(409, ALREADY_TAKEN)
    db.refresh(b)
    _finalize_assignment(db, b, sp, actor=user)
    return _booking_json(db, b, user)


class DeclineBody(BaseModel):
    reason: str = "declined"


@router.post("/bookings/{booking_id}/decline")
def decline_booking(
    booking_id: str,
    background: BackgroundTasks,
    body: DeclineBody = DeclineBody(),
    user: User = Depends(require_roles("service_partner")),
    db: Session = Depends(get_db),
) -> dict:
    b = db.get(Booking, booking_id)
    if b is None:
        raise HTTPException(404, "not_found")
    db.merge(BookingExclusion(booking_id=b.id, service_partner_id=user.id, reason="declined"))
    background.add_task(_enqueue_pool, b.id)
    return {"ok": True}


@router.post("/bookings/{booking_id}/drop")
def drop_booking(
    booking_id: str,
    background: BackgroundTasks,
    user: User = Depends(require_roles("service_partner", "partner_owner")),
    db: Session = Depends(get_db),
) -> dict:
    b = db.get(Booking, booking_id)
    if b is None:
        raise HTTPException(404, "not_found")
    if user.role == "service_partner" and b.assigned_sp_id != user.id:
        raise HTTPException(403, "forbidden")
    sp_id = b.assigned_sp_id or user.id
    b.status = "open"
    b.assigned_sp_id = None
    b.assigned_at = None
    db.merge(BookingExclusion(booking_id=b.id, service_partner_id=sp_id, reason="dropped"))
    notify(db, b.customer_id, "reassigned_pending", b.id)
    background.add_task(_enqueue_pool, b.id)
    return _booking_json(db, b, user)


class StartBody(BaseModel):
    code: str


@router.post("/bookings/{booking_id}/start")
def start_work(
    booking_id: str,
    body: StartBody,
    user: User = Depends(require_roles("service_partner")),
    db: Session = Depends(get_db),
) -> dict:
    b = db.get(Booking, booking_id)
    if b is None or b.assigned_sp_id != user.id:
        raise HTTPException(404, "not_found")
    if b.status not in ("assigned", "en_route"):
        raise HTTPException(400, "bad_status")
    if not b.start_work_otp_hash or hash_code(body.code, settings.otp_pepper) != b.start_work_otp_hash:
        raise HTTPException(400, "otp_invalid")
    if b.service_date > now_kolkata().date():
        raise HTTPException(400, "too_early")
    b.status = "in_progress"
    b.start_work_verified_at = utcnow()
    return _booking_json(db, b, user)


@router.post("/bookings/{booking_id}/en-route")
def en_route(booking_id: str, user: User = Depends(require_roles("service_partner")), db: Session = Depends(get_db)) -> dict:
    b = db.get(Booking, booking_id)
    if b is None or b.assigned_sp_id != user.id:
        raise HTTPException(404, "not_found")
    b.status = "en_route"
    return _booking_json(db, b, user)


class CompleteBody(BaseModel):
    payment_mode: str = "cash"
    collected_amount: Decimal | None = None
    razorpay_payment_id: str | None = None
    rating: int | None = None
    rating_comment: str | None = None


@router.post("/bookings/{booking_id}/complete")
def complete_booking(
    booking_id: str,
    body: CompleteBody,
    user: User = Depends(require_roles("service_partner", "partner_owner")),
    db: Session = Depends(get_db),
) -> dict:
    b = db.get(Booking, booking_id)
    if b is None:
        raise HTTPException(404, "not_found")
    b.status = "completed"
    b.completed_at = utcnow()
    b.payment_mode = body.payment_mode
    b.collected_amount = body.collected_amount or b.quoted_amount
    b.razorpay_payment_id = body.razorpay_payment_id
    partner = db.get(Partner, b.partner_id)
    pct = Decimal(partner.commission_percent) if partner else Decimal("0")
    collected = Decimal(b.collected_amount or 0)
    b.commission_amount = (collected * pct / Decimal("100")).quantize(Decimal("0.01"))
    b.payout_amount = collected - b.commission_amount
    if b.assigned_sp_id:
        db.add(
            PayoutLedger(
                partner_id=b.partner_id,
                service_partner_id=b.assigned_sp_id,
                booking_id=b.id,
                amount=b.payout_amount,
                status="pending",
            )
        )
    if body.rating:
        b.rating = body.rating
        b.rating_comment = body.rating_comment
    return _booking_json(db, b, user)


class RateBody(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)


@router.post("/bookings/{booking_id}/rate")
def rate_booking(
    booking_id: str,
    body: RateBody,
    user: User = Depends(require_roles("customer")),
    db: Session = Depends(get_db),
) -> dict:
    b = db.get(Booking, booking_id)
    if b is None:
        raise HTTPException(404, "not_found")
    if b.customer_id != user.id or b.status != "completed":
        raise HTTPException(403, "forbidden")
    if b.rating is not None:
        raise HTTPException(409, "already_rated")
    b.rating = body.rating
    b.rating_comment = body.comment
    return _booking_json(db, b, user)


@router.post("/bookings/{booking_id}/cancel")
def cancel_booking(booking_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    b = db.get(Booking, booking_id)
    if b is None:
        raise HTTPException(404, "not_found")
    if user.role == "customer" and b.customer_id != user.id:
        raise HTTPException(403, "forbidden")
    b.status = "cancelled"
    b.cancelled_at = utcnow()
    # Drop the pool's offer rows: a cancelled job must vanish from SP queues
    # deterministically, whether or not its background pool committed first.
    db.execute(delete(BookingOffer).where(BookingOffer.booking_id == b.id))
    return _booking_json(db, b, user)


def _can_see(user: User, b: Booking) -> None:
    if user.role == "master_admin":
        return
    if user.role == "customer" and b.customer_id == user.id:
        return
    if user.role == "service_partner" and (b.assigned_sp_id == user.id):
        return
    if user.role in ("partner_owner",) and b.partner_id == user.partner_id:
        return
    if user.role == "service_partner":
        return  # offers checked at list
    raise HTTPException(403, "forbidden")


def _booking_json(db: Session, b: Booking, viewer: User) -> dict:
    complaints = list(db.scalars(select(BookingComplaint).where(BookingComplaint.booking_id == b.id)))
    issues = []
    for c in complaints:
        t = db.get(CategoryIssueTemplate, c.issue_template_id)
        if t:
            issues.append({"id": t.id, "text_en": t.text_en})
    tech = db.get(User, b.assigned_sp_id) if b.assigned_sp_id else None
    cat = db.get(ServiceCategory, b.category_id)
    otp_for_customer = None
    if viewer.role == "customer" and b.start_work_otp_hash and b.status in ("assigned", "en_route", "in_progress"):
        otp_for_customer = "sent_to_your_phone"
    return {
        "id": b.id,
        "status": b.status,
        "service_date": b.service_date.isoformat(),
        "slot": b.slot,
        "pincode": b.pincode,
        "category_id": b.category_id,
        "category_name": cat.name_en if cat else "",
        "quoted_amount": str(b.quoted_amount),
        "issues": issues,
        "issue_note": b.issue_note,
        "technician_name": tech.full_name if tech else None,
        "technician_mobile_masked": mask_mobile(tech.mobile) if tech else None,
        "start_work_otp_hint": otp_for_customer,
        "assigned_sp_id": b.assigned_sp_id,
        "partner_id": b.partner_id,
        "customer_id": b.customer_id,
        "pool_empty": b.pool_empty,
        "dispatch_refresh_count": b.dispatch_refresh_count or 0,
        "force_assign_ready": force_assign_ready(b.status, b.created_at, b.dispatch_refresh_count or 0),
        "created_at": as_utc_aware(b.created_at).isoformat() if b.created_at else None,
        "first_accepted_at": (
            as_utc_aware(b.first_accepted_at).isoformat() if b.first_accepted_at else None
        ),
        "payment_mode": b.payment_mode,
        "rating": b.rating,
    }
