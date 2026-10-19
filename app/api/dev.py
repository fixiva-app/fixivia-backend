from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import CommitRoute, get_db
from app.dev_users import inject_payload
from app.domain.otp import OtpPurpose
from app.models import (
    AvailabilityBlock,
    Booking,
    BookingComplaint,
    BookingExclusion,
    BookingOffer,
    BookingPhoto,
    CustomerAddress,
    Notification,
    OtpChallengeRow,
    PayoutLedger,
    ServicePartnerCategory,
    ServicePartnerPincode,
    ServicePartnerProfile,
    User,
)
from app.seed import DEV_ACCOUNTS
from app.services.otp_sender import last_console_code

router = APIRouter(prefix="/v1/dev", tags=["dev"], route_class=CommitRoute)


def _require_dev() -> None:
    if settings.flavor != "dev":
        raise HTTPException(status_code=404, detail="not_found")


@router.post("/inject-users")
def inject_users(db: Session = Depends(get_db)) -> dict:
    """Create one of each role if missing. Dev flavor only."""
    _require_dev()
    return {"accounts": inject_payload(db)}


@router.get("/otp-code")
def read_otp_code(mobile: str, purpose: OtpPurpose = OtpPurpose.LOGIN) -> dict:
    """Return the last dev-sent OTP code. Dev flavor only (UI tests)."""
    _require_dev()
    code = last_console_code(purpose.value, mobile)
    if code is None:
        raise HTTPException(status_code=404, detail="otp_not_found")
    return {"mobile": mobile, "purpose": purpose.value, "code": code}


class WipeBody(BaseModel):
    user_mobiles: list[str] = Field(default_factory=list)
    booking_ids: list[str] = Field(default_factory=list)


_DEV_MOBILES = frozenset(a["mobile"] for a in DEV_ACCOUNTS)


@router.delete("/test-entities")
def wipe_test_entities(body: WipeBody, db: Session = Depends(get_db)) -> dict:
    """Delete case-seeded users + bookings and their dependents.

    Dev flavor only (UI test teardown). Idempotent: unknown ids are
    skipped. The shared dev accounts can never be wiped.
    """
    _require_dev()
    if _DEV_MOBILES.intersection(body.user_mobiles):
        raise HTTPException(status_code=400, detail="dev_user_protected")
    counts: dict[str, int] = {}
    bids = list(dict.fromkeys(body.booking_ids))
    uids = []
    if body.user_mobiles:
        uids = db.scalars(
            select(User.id).where(User.mobile.in_(body.user_mobiles))
        ).all()

    def _wipe(model, *conds, name: str) -> None:
        if not conds:
            counts[name] = 0
            return
        res = db.execute(delete(model).where(*conds))
        counts[name] = res.rowcount or 0

    if bids:
        _wipe(PayoutLedger, PayoutLedger.booking_id.in_(bids), name="payout_ledger")
        _wipe(Notification, Notification.booking_id.in_(bids), name="notifications_by_booking")
        for model, name in (
            (BookingComplaint, "booking_complaints"),
            (BookingPhoto, "booking_photos"),
            (BookingOffer, "booking_offers"),
            (BookingExclusion, "booking_exclusions"),
        ):
            _wipe(model, model.booking_id.in_(bids), name=name)
        _wipe(Booking, Booking.id.in_(bids), name="bookings")
    else:
        counts.update(
            payout_ledger=0,
            notifications_by_booking=0,
            booking_complaints=0,
            booking_photos=0,
            booking_offers=0,
            booking_exclusions=0,
            bookings=0,
        )
    if uids:
        _wipe(PayoutLedger, PayoutLedger.service_partner_id.in_(uids),
              name="payout_ledger_by_sp")
        _wipe(Notification, Notification.user_id.in_(uids), name="notifications_by_user")
        _wipe(BookingOffer, BookingOffer.service_partner_id.in_(uids),
              name="booking_offers_by_sp")
        _wipe(BookingExclusion, BookingExclusion.service_partner_id.in_(uids),
              name="booking_exclusions_by_sp")
        _wipe(CustomerAddress, CustomerAddress.user_id.in_(uids), name="addresses")
        _wipe(AvailabilityBlock, AvailabilityBlock.user_id.in_(uids),
              name="availability_blocks")
        _wipe(ServicePartnerProfile, ServicePartnerProfile.user_id.in_(uids),
              name="sp_profiles")
        _wipe(ServicePartnerPincode, ServicePartnerPincode.user_id.in_(uids),
              name="sp_pincodes")
        _wipe(ServicePartnerCategory, ServicePartnerCategory.user_id.in_(uids),
              name="sp_categories")
        _wipe(User, User.id.in_(uids), name="users")
    else:
        counts.update(
            payout_ledger_by_sp=0,
            notifications_by_user=0,
            booking_offers_by_sp=0,
            booking_exclusions_by_sp=0,
            addresses=0,
            availability_blocks=0,
            sp_profiles=0,
            sp_pincodes=0,
            sp_categories=0,
            users=0,
        )
    if body.user_mobiles:
        _wipe(OtpChallengeRow, OtpChallengeRow.mobile.in_(body.user_mobiles),
              name="otp_challenges")
    else:
        counts["otp_challenges"] = 0
    return {"deleted": counts}
