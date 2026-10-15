from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable
from decimal import Decimal
from typing import TypeVar

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import OperationalError
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

T = TypeVar("T")


def with_busy_retry(label: str, fn: Callable[[], T], *, attempts: int = 5,
                    on_retry: Callable[[], None] | None = None) -> T:
    """Retry fn when SQLite reports a lock. WAL busy-timeouts don't cover
    snapshot-busy (read-then-write across racing sessions), which fails fast;
    a fresh attempt milliseconds later succeeds."""
    for attempt in range(attempts):
        try:
            return fn()
        except (OperationalError, sqlite3.OperationalError) as exc:
            if "locked" not in str(exc).lower() or attempt == attempts - 1:
                raise
            if on_retry is not None:
                on_retry()
            print(f"[POOL] {label} busy, retry {attempt + 1}", flush=True)
            time.sleep(0.05 * (2 ** attempt))
    raise AssertionError("unreachable")


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


def eligible_technicians(db: Session, booking: Booking) -> list[dict]:
    """Pool-eligible SPs for a booking. Shared by dispatch and force-assign."""
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
    out: list[dict] = []
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
        out.append({"user": user, "jobs_in_slot": jobs})
    return out


def dispatch_pool(db: Session, booking_id: str, admin_reminder: bool = False) -> dict:
    booking = db.get(Booking, booking_id)
    if booking is None or booking.status != "open":
        return {"skipped": True}
    partner = db.get(Partner, booking.partner_id)
    if partner is None or partner.status != "approved":
        booking.pool_empty = True
        return {"empty": True, "reason": "partner"}

    techs = eligible_technicians(db, booking)
    savepoint = db.begin_nested()
    try:
        offered: list[str] = []
        for entry in techs:
            user = entry["user"]
            jobs = entry["jobs_in_slot"]
            db.execute(
                sqlite_insert(BookingOffer)
                .values(booking_id=booking.id, service_partner_id=user.id)
                .on_conflict_do_nothing()
            )
            db.execute(
                update(BookingOffer)
                .where(
                    BookingOffer.booking_id == booking.id,
                    BookingOffer.service_partner_id == user.id,
                )
                .values(last_notified_at=utcnow())
            )
            notify(
                db,
                user.id,
                "offer",
                booking.id,
                slot_load=jobs,
                slot_cap=5,
            )
            offered.append(user.id)
        db.flush()
        db.refresh(booking)
        if booking.status != "open":
            savepoint.rollback()
            return {"skipped": True, "reason": "settled_mid_pool"}
        booking.last_dispatch_at = utcnow()
        booking.dispatch_refresh_count = (booking.dispatch_refresh_count or 0) + 1
        booking.pool_empty = len(offered) == 0
        ntype = "open_reminder" if admin_reminder else ("empty_pool" if not offered else "new_request")
        for admin in partner_admins(db, booking.partner_id):
            notify(db, admin.id, ntype, booking.id, offered=len(offered))
        db.flush()
        savepoint.commit()
    except Exception:
        savepoint.rollback()
        raise
    return {"offered": offered, "empty": len(offered) == 0}


def dispatch_repool_open(db: Session) -> int:
    ids = list(db.scalars(select(Booking.id).where(Booking.status == "open")))
    for bid in ids:
        dispatch_pool(db, bid, admin_reminder=True)
    return len(ids)
