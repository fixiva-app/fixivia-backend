from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.domain.dispatch import TechnicianEligibility, is_eligible
from app.models import (
    AvailabilityBlock,
    Booking,
    BookingExclusion,
    BookingOffer,
    Partner,
    PartnerPincode,
    ServicePartnerCategory,
    ServicePartnerPincode,
    ServicePartnerProfile,
    User,
    utcnow,
)
from app.services.notify import notify

ACTIVE_SLOT_STATUSES = ("assigned", "en_route", "in_progress", "completed")


def slot_job_count(db: Session, sp_id: str, service_date, slot: str) -> int:
    return db.scalar(
        select(func.count()).select_from(Booking).where(
            Booking.assigned_sp_id == sp_id,
            Booking.service_date == service_date,
            Booking.slot == slot,
            Booking.status.in_(ACTIVE_SLOT_STATUSES),
        )
    ) or 0


def partner_admins(db: Session, partner_id: str) -> list[User]:
    return list(
        db.scalars(
            select(User).where(
                User.partner_id == partner_id,
                User.role.in_(("partner_owner", "partner_admin")),
                User.status == "active",
            )
        )
    )


def dispatch_pool(db: Session, booking_id: str, admin_reminder: bool = False) -> dict:
    booking = db.get(Booking, booking_id)
    if booking is None or booking.status != "open":
        return {"skipped": True}
    partner = db.get(Partner, booking.partner_id)
    if partner is None or partner.status != "approved":
        booking.pool_empty = True
        return {"empty": True, "reason": "partner"}

    excluded = {
        row.service_partner_id
        for row in db.scalars(select(BookingExclusion).where(BookingExclusion.booking_id == booking.id))
    }
    profiles = list(
        db.scalars(
            select(ServicePartnerProfile).where(
                ServicePartnerProfile.partner_id == booking.partner_id,
                ServicePartnerProfile.kyc_status == "approved",
            )
        )
    )
    offered: list[str] = []
    for profile in profiles:
        user = db.get(User, profile.user_id)
        if user is None or user.status != "active":
            continue
        has_cat = db.get(ServicePartnerCategory, (user.id, booking.category_id))
        has_pin = db.get(ServicePartnerPincode, (user.id, booking.pincode))
        blocked = db.scalar(
            select(AvailabilityBlock).where(
                AvailabilityBlock.user_id == user.id,
                AvailabilityBlock.block_date == booking.service_date,
                or_(AvailabilityBlock.slot.is_(None), AvailabilityBlock.slot == booking.slot),
            )
        )
        jobs = slot_job_count(db, user.id, booking.service_date, booking.slot)
        ok = is_eligible(
            TechnicianEligibility(
                approved=True,
                same_partner=True,
                offers_category=has_cat is not None,
                works_pincode=has_pin is not None,
                excluded=profile.user_id in excluded or blocked is not None,
                jobs_in_slot=jobs,
            )
        )
        if not ok:
            continue
        existing = db.get(BookingOffer, (booking.id, user.id))
        if existing:
            existing.last_notified_at = utcnow()
        else:
            db.add(BookingOffer(booking_id=booking.id, service_partner_id=user.id))
        notify(
            db,
            user.id,
            "offer",
            booking.id,
            slot_load=jobs,
            slot_cap=5,
        )
        offered.append(user.id)

    booking.last_dispatch_at = utcnow()
    booking.dispatch_refresh_count = (booking.dispatch_refresh_count or 0) + 1
    booking.pool_empty = len(offered) == 0
    ntype = "open_reminder" if admin_reminder else ("empty_pool" if not offered else "new_request")
    for admin in partner_admins(db, booking.partner_id):
        notify(db, admin.id, ntype, booking.id, offered=len(offered))
    return {"offered": offered, "empty": len(offered) == 0}


def dispatch_repool_open(db: Session) -> int:
    ids = list(db.scalars(select(Booking.id).where(Booking.status == "open")))
    for bid in ids:
        dispatch_pool(db, bid, admin_reminder=True)
    return len(ids)
