from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable
from decimal import Decimal
from typing import TypeVar

from sqlalchemy import func, or_, select, text
from sqlalchemy.dialects import postgresql as pg_insert_module
from sqlalchemy.dialects import sqlite as sqlite_insert_module
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.domain.booking_rules import MAX_JOBS_PER_SLOT
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


def _is_pg(db: Session) -> bool:
    return db.get_bind().dialect.name == "postgresql"


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
    """Pool-eligible SPs for a booking. Shared by dispatch and force-assign.

    Set-based: one query per booking instead of ~5 per SP. A repool sweep
    over hundreds of opens used to issue 250k+ statements (>60s); the same
    results now cost two. Results and order (profile rowid) are unchanged.
    """
    excluded = {
        row.service_partner_id
        for row in db.scalars(select(BookingExclusion).where(BookingExclusion.booking_id == booking.id))
    }
    jobs_in_slot = func.count(Booking.id)
    stmt = (
        select(User, jobs_in_slot)
        .join(ServicePartnerProfile, ServicePartnerProfile.user_id == User.id)
        .join(
            ServicePartnerCategory,
            (ServicePartnerCategory.user_id == User.id)
            & (ServicePartnerCategory.category_id == booking.category_id),
        )
        .join(
            ServicePartnerPincode,
            (ServicePartnerPincode.user_id == User.id)
            & (ServicePartnerPincode.pincode == booking.pincode),
        )
        .outerjoin(
            AvailabilityBlock,
            (AvailabilityBlock.user_id == User.id)
            & (AvailabilityBlock.block_date == booking.service_date)
            & or_(AvailabilityBlock.slot.is_(None), AvailabilityBlock.slot == booking.slot),
        )
        .outerjoin(
            Booking,
            (Booking.assigned_sp_id == User.id)
            & (Booking.service_date == booking.service_date)
            & (Booking.slot == booking.slot)
            & (Booking.status.in_(ACTIVE_SLOT_STATUSES)),
        )
        .where(
            ServicePartnerProfile.partner_id == booking.partner_id,
            ServicePartnerProfile.kyc_status == "approved",
            User.status == "active",
            AvailabilityBlock.id.is_(None),
        )
        .group_by(User.id)
        .having(jobs_in_slot < MAX_JOBS_PER_SLOT)
        # Profile scan order (sqlite rowid): matches the pre-rewrite per-SP
        # loop so the offered list order is unchanged. Postgres has no
        # rowid; PK order is deterministic (no test asserts offer order).
        .order_by(
            ServicePartnerProfile.user_id
            if _is_pg(db)
            else text("service_partner_profiles.rowid")
        )
    )
    if excluded:
        stmt = stmt.where(User.id.notin_(excluded))
    out: list[dict] = []
    for user, jobs in db.execute(stmt):
        ok = is_eligible(
            TechnicianEligibility(
                approved=True,
                same_partner=True,
                offers_category=True,
                works_pincode=True,
                excluded=False,
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
    now = utcnow()
    savepoint = db.begin_nested()
    try:
        offered: list[str] = [entry["user"].id for entry in techs]
        if offered:
            # One multi-row upsert instead of one statement per tech: same
            # final rows (offered_at kept, last_notified_at refreshed).
            _insert = pg_insert_module.insert if _is_pg(db) else sqlite_insert_module.insert
            db.execute(
                _insert(BookingOffer)
                .values(
                    [
                        {
                            "booking_id": booking.id,
                            "service_partner_id": uid,
                            "last_notified_at": now,
                        }
                        for uid in offered
                    ]
                )
                .on_conflict_do_update(
                    index_elements=["booking_id", "service_partner_id"],
                    set_={"last_notified_at": now},
                )
            )
        for entry in techs:
            user = entry["user"]
            jobs = entry["jobs_in_slot"]
            notify(
                db,
                user.id,
                "offer",
                booking.id,
                slot_load=jobs,
                slot_cap=5,
            )
        db.flush()
        db.refresh(booking)
        if booking.status != "open":
            savepoint.rollback()
            return {"skipped": True, "reason": "settled_mid_pool"}
        booking.last_dispatch_at = now
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
