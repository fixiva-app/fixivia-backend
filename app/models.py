from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Pincode(Base):
    __tablename__ = "pincodes"
    pincode: Mapped[str] = mapped_column(String(6), primary_key=True)
    state: Mapped[str] = mapped_column(String(80), default="Kerala")
    district: Mapped[str] = mapped_column(String(80))
    locality: Mapped[str | None] = mapped_column(String(120), nullable=True)


class Partner(Base):
    __tablename__ = "partners"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    org_type: Mapped[str] = mapped_column(String(20), default="company")
    trade_name: Mapped[str] = mapped_column(String(200))
    legal_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gstin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cin: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    billing_cycle: Mapped[str] = mapped_column(String(20), default="monthly")
    license_fee_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    commission_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    office_address: Mapped[str] = mapped_column(Text, default="")
    office_pincode: Mapped[str] = mapped_column(String(6), default="")
    personal_email: Mapped[str] = mapped_column(String(200), default="")
    company_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    primary_owner_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PartnerInvite(Base):
    __tablename__ = "partner_invites"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    token_plain_dev: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    used_by_partner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PartnerPincode(Base):
    __tablename__ = "partner_pincodes"
    partner_id: Mapped[str] = mapped_column(String(36), ForeignKey("partners.id"), primary_key=True)
    pincode: Mapped[str] = mapped_column(String(6), ForeignKey("pincodes.pincode"), primary_key=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firebase_uid: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    role: Mapped[str] = mapped_column(String(30))
    partner_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("partners.id"), nullable=True)
    full_name: Mapped[str] = mapped_column(String(200))
    mobile: Mapped[str] = mapped_column(String(16), unique=True)
    email: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(20), default="active")
    locale: Mapped[str] = mapped_column(String(8), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class OtpChallengeRow(Base):
    __tablename__ = "otp_challenges"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    purpose: Mapped[str] = mapped_column(String(20))
    mobile: Mapped[str] = mapped_column(String(16), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PartnerAdminRequest(Base):
    __tablename__ = "partner_admin_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    partner_id: Mapped[str] = mapped_column(String(36), ForeignKey("partners.id"))
    full_name: Mapped[str] = mapped_column(String(200))
    mobile: Mapped[str] = mapped_column(String(16))
    email: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(20), default="submitted")
    requested_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ServiceCategory(Base):
    __tablename__ = "service_categories"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name_en: Mapped[str] = mapped_column(String(200))
    name_ml: Mapped[str] = mapped_column(String(200), default="")
    description_en: Mapped[str] = mapped_column(Text, default="")
    description_ml: Mapped[str] = mapped_column(Text, default="")
    skill_set_en: Mapped[str] = mapped_column(Text, default="")
    skill_set_ml: Mapped[str] = mapped_column(Text, default="")
    icon: Mapped[str] = mapped_column(String(80), default="build")
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    featured_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)


class CategoryIssueTemplate(Base):
    __tablename__ = "category_issue_templates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("service_categories.id"))
    text_en: Mapped[str] = mapped_column(String(200))
    text_ml: Mapped[str] = mapped_column(String(200), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    featured_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)


class PartnerCategoryPricing(Base):
    __tablename__ = "partner_category_pricing"
    partner_id: Mapped[str] = mapped_column(String(36), ForeignKey("partners.id"), primary_key=True)
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("service_categories.id"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    visit_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("499"))


class SaasInvoice(Base):
    __tablename__ = "saas_invoices"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    partner_id: Mapped[str] = mapped_column(String(36), ForeignKey("partners.id"))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_type: Mapped[str] = mapped_column(String(30))
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    doc_type: Mapped[str] = mapped_column(String(40))
    storage_path: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    verified_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ServicePartnerProfile(Base):
    __tablename__ = "service_partner_profiles"
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    partner_id: Mapped[str] = mapped_column(String(36), ForeignKey("partners.id"))
    kyc_status: Mapped[str] = mapped_column(String(40), default="profile_incomplete")
    aadhaar_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    police_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ServicePartnerPincode(Base):
    __tablename__ = "service_partner_pincodes"
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    pincode: Mapped[str] = mapped_column(String(6), ForeignKey("pincodes.pincode"), primary_key=True)


class ServicePartnerCategory(Base):
    __tablename__ = "service_partner_categories"
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("service_categories.id"), primary_key=True)


class CustomerAddress(Base):
    __tablename__ = "customer_addresses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    label: Mapped[str] = mapped_column(String(20), default="home")
    line1: Mapped[str] = mapped_column(String(300))
    landmark: Mapped[str | None] = mapped_column(String(200), nullable=True)
    pincode: Mapped[str] = mapped_column(String(6), ForeignKey("pincodes.pincode"))
    lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    lng: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)


class AvailabilityBlock(Base):
    __tablename__ = "availability_blocks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    block_date: Mapped[date] = mapped_column(Date)
    slot: Mapped[str | None] = mapped_column(String(20), nullable=True)


class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    partner_id: Mapped[str] = mapped_column(String(36), ForeignKey("partners.id"))
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    address_id: Mapped[str] = mapped_column(String(36), ForeignKey("customer_addresses.id"))
    pincode: Mapped[str] = mapped_column(String(6))
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("service_categories.id"))
    issue_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_date: Mapped[date] = mapped_column(Date)
    slot: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="open")
    assigned_sp_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    first_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reassign_count: Mapped[int] = mapped_column(Integer, default=0)
    dispatch_refresh_count: Mapped[int] = mapped_column(Integer, default=0)
    last_dispatch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_work_otp_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    start_work_otp_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_work_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quoted_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    collected_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    payout_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    commission_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    payment_mode: Mapped[str] = mapped_column(String(20), default="unpaid")
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    pool_empty: Mapped[bool] = mapped_column(Boolean, default=False)


class BookingComplaint(Base):
    __tablename__ = "booking_complaints"
    booking_id: Mapped[str] = mapped_column(String(36), ForeignKey("bookings.id"), primary_key=True)
    issue_template_id: Mapped[str] = mapped_column(String(36), ForeignKey("category_issue_templates.id"), primary_key=True)


class BookingPhoto(Base):
    __tablename__ = "booking_photos"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    booking_id: Mapped[str] = mapped_column(String(36), ForeignKey("bookings.id"))
    storage_path: Mapped[str] = mapped_column(String(500))


class BookingOffer(Base):
    __tablename__ = "booking_offers"
    booking_id: Mapped[str] = mapped_column(String(36), ForeignKey("bookings.id"), primary_key=True)
    service_partner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    offered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_notified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BookingExclusion(Base):
    __tablename__ = "booking_exclusions"
    booking_id: Mapped[str] = mapped_column(String(36), ForeignKey("bookings.id"), primary_key=True)
    service_partner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    reason: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PayoutLedger(Base):
    __tablename__ = "payout_ledger"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    partner_id: Mapped[str] = mapped_column(String(36), ForeignKey("partners.id"))
    service_partner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    booking_id: Mapped[str] = mapped_column(String(36), ForeignKey("bookings.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(40))
    booking_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    payload: Mapped[str] = mapped_column(Text, default="{}")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(36))
    meta: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
