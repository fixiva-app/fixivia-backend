from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from statistics import median

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_roles
from app.models import Booking, BookingExclusion, BookingOffer, Partner, SaasInvoice, User

router = APIRouter(prefix="/v1", tags=["analytics"])


@router.get("/analytics")
def analytics(
    user: User = Depends(require_roles("master_admin", "partner_owner", "partner_admin", "service_partner")),
    db: Session = Depends(get_db),
    days: int = 30,
    pincode: str | None = None,
    category_id: str | None = None,
    slot: str | None = None,
) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = select(Booking).where(Booking.created_at >= since)
    if user.role in ("partner_owner", "partner_admin"):
        q = q.where(Booking.partner_id == user.partner_id)
    if user.role == "service_partner":
        q = q.where(Booking.assigned_sp_id == user.id)
    if pincode:
        q = q.where(Booking.pincode == pincode)
    if category_id:
        q = q.where(Booking.category_id == category_id)
    if slot:
        q = q.where(Booking.slot == slot)
    bookings = list(db.scalars(q))
    ids = [b.id for b in bookings]
    created = len(bookings)
    still_open = sum(1 for b in bookings if b.status == "open")
    accepted = sum(1 for b in bookings if b.first_accepted_at)
    completed = sum(1 for b in bookings if b.status == "completed")
    cancelled = sum(1 for b in bookings if b.status == "cancelled")
    no_show = sum(1 for b in bookings if b.status == "no_show")
    dropped = sum(1 for b in bookings if (b.reassign_count or 0) > 0)
    fills = []
    for b in bookings:
        if b.first_accepted_at and b.created_at:
            fa, cr = b.first_accepted_at, b.created_at
            if fa.tzinfo is None:
                fa = fa.replace(tzinfo=timezone.utc)
            if cr.tzinfo is None:
                cr = cr.replace(tzinfo=timezone.utc)
            fills.append((fa - cr).total_seconds() / 60)
    gmv = sum((b.collected_amount or Decimal("0")) for b in bookings if b.status == "completed")
    commission = sum((b.commission_amount or Decimal("0")) for b in bookings if b.status == "completed")
    empty_pool = sum(1 for b in bookings if b.pool_empty)
    offers = 0
    declines = 0
    if ids:
        offers = db.scalar(select(func.count()).select_from(BookingOffer).where(BookingOffer.booking_id.in_(ids))) or 0
        declines = db.scalar(
            select(func.count())
            .select_from(BookingExclusion)
            .where(BookingExclusion.booking_id.in_(ids), BookingExclusion.reason == "declined")
        ) or 0

    saas = {"invoiced": "0", "collected": "0", "overdue": "0", "note": "SaaS license fees — not job GMV"}
    if user.role == "master_admin":
        inv = list(db.scalars(select(SaasInvoice)))
        invoiced = sum((i.amount for i in inv), Decimal("0"))
        collected = sum((i.amount for i in inv if i.status == "paid"), Decimal("0"))
        overdue = sum((i.amount for i in inv if i.status == "overdue"), Decimal("0"))
        saas.update({"invoiced": str(invoiced), "collected": str(collected), "overdue": str(overdue)})

    by_partner = []
    if user.role == "master_admin":
        for pid in {b.partner_id for b in bookings}:
            subset = [b for b in bookings if b.partner_id == pid]
            p = db.get(Partner, pid)
            by_partner.append(
                {
                    "partner_id": pid,
                    "trade_name": p.trade_name if p else pid,
                    "created": len(subset),
                    "completed": sum(1 for b in subset if b.status == "completed"),
                }
            )

    return {
        "range_days": days,
        "created": created,
        "still_open": still_open,
        "accepted": accepted,
        "completed": completed,
        "cancelled": cancelled,
        "no_show": no_show,
        "dropped_after_accept": dropped,
        "accept_rate": (accepted / created) if created else 0,
        "completion_rate": (completed / accepted) if accepted else 0,
        "median_accept_minutes": median(fills) if fills else None,
        "avg_accept_minutes": (sum(fills) / len(fills)) if fills else None,
        "gmv_completed": str(gmv),
        "commission_completed": str(commission),
        "gmv_note": "Job GMV from completed visits — not mixed with SaaS license fees",
        "empty_pool": empty_pool,
        "offers": offers,
        "declines": declines,
        "saas_license_fees": saas,
        "by_partner": by_partner,
    }


@router.get("/invoices")
def invoices(user: User = Depends(require_roles("master_admin", "partner_owner")), db: Session = Depends(get_db)) -> list[dict]:
    q = select(SaasInvoice)
    if user.role != "master_admin":
        q = q.where(SaasInvoice.partner_id == user.partner_id)
    rows = db.scalars(q)
    return [
        {
            "id": r.id,
            "partner_id": r.partner_id,
            "amount": str(r.amount),
            "status": r.status,
            "period_start": r.period_start.isoformat(),
            "period_end": r.period_end.isoformat(),
        }
        for r in rows
    ]
