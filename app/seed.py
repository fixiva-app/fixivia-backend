from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Partner,
    PartnerCategoryPricing,
    PartnerPincode,
    Pincode,
    Product,
    SaasInvoice,
    ServiceCategory,
    CategoryIssueTemplate,
    ServicePartnerCategory,
    ServicePartnerPincode,
    ServicePartnerProfile,
    User,
)

# Demo mobiles for local testing only. OTP login; or POST /v1/dev/inject-users.
DEV_ACCOUNTS = (
    {
        "mobile": "9000000001",
        "role": "master_admin",
        "full_name": "Fixiva Master",
        "email": "master@fixiva.local",
    },
    {
        "mobile": "9000000002",
        "role": "partner_owner",
        "full_name": "Anil Partner",
        "email": "owner@homecare.local",
    },
    {
        "mobile": "9000000003",
        "role": "service_partner",
        "full_name": "Ravi Technician",
        "email": "ravi@homecare.local",
    },
    {
        "mobile": "9000000004",
        "role": "customer",
        "full_name": "Meera Customer",
        "email": "meera@example.com",
    },
)

SEED_CATEGORIES = [
    ("water-purifier-repair", "Water purifier repair", "വാട്ടർ പ്യൂരിഫയർ", 1),
    ("ac-mechanic", "AC mechanic", "എസി മെക്കാനിക്", 2),
    ("tv-mechanic", "TV mechanic", "ടിവി മെക്കാനിക്", 3),
    ("washing-machine-repair", "Washing machine repair", "വാഷിംഗ് മെഷീൻ", 4),
    ("computer-repair", "Computer repair", "കമ്പ്യൂട്ടർ റിപ്പയർ", 5),
    ("inverter-repair", "Inverter repair", "ഇൻവെർട്ടർ", None),
    ("car-wash-home", "Car wash at home", "കാർ വാഷ്", None),
    ("house-cleaning-basic", "House / surrounding cleaning — basic", "വീട് വൃത്തിയാക്കൽ", None),
    ("cleaning-advanced", "Cleaning — advanced", "ആഴത്തിലുള്ള ക്ലീനിംഗ്", None),
    ("water-tank-cleaning", "Water tank cleaning", "ടാങ്ക് ക്ലീനിംഗ്", None),
]

PROBLEMS = [
    "Not cooling",
    "Leak",
    "Noise",
    "Smell",
    "No power",
    "Error code",
    "Installation",
    "Other issue",
]


def seed_if_empty(db: Session) -> None:
    if db.scalar(select(User).limit(1)) is None:
        _seed_geo_and_catalog(db)
        _seed_partner_org(db)
        if settings.flavor != "prod":
            _seed_invoice(db)
    # Unconditional: _seed_products is idempotent and backfills images
    # for rows seeded before product_images existed.
    _seed_products(db)
    ensure_dev_users(db)


def ensure_dev_users(db: Session) -> list[User]:
    """Idempotent: one user per role for local testing. Safe to re-run.

    Base data (geo/catalog/partner org) is seeded in every flavor. On
    prod, demo accounts are skipped; instead the MASTER_MOBILE number
    (if set) gets the single master_admin account.
    """
    if db.scalar(select(Pincode).limit(1)) is None:
        _seed_geo_and_catalog(db)
    partner = db.scalar(select(Partner).limit(1))
    if partner is None:
        partner = _seed_partner_org(db)
    if settings.flavor == "prod":
        users: list[User] = []
        if settings.master_mobile.strip():
            user = db.scalar(select(User).where(User.mobile == settings.master_mobile.strip()))
            if user is None:
                user = _create_dev_user(
                    db,
                    partner,
                    [],
                    {
                        "role": "master_admin",
                        "mobile": settings.master_mobile.strip(),
                        "full_name": "Fixiva Master",
                        "email": "master@fixiva",
                    },
                )
            users.append(user)
        db.commit()
        return users
    cats = list(db.scalars(select(ServiceCategory)))
    users: list[User] = []
    for spec in DEV_ACCOUNTS:
        user = db.scalar(select(User).where(User.mobile == spec["mobile"]))
        if user is None:
            user = _create_dev_user(db, partner, cats, spec)
        users.append(user)
    db.commit()
    print(
        "[SEED] demo mobiles "
        "master=9000000001 owner=9000000002 sp=9000000003 "
        "customer=9000000004",
        flush=True,
    )
    return users


def _create_dev_user(
    db: Session,
    partner: Partner,
    cats: list[ServiceCategory],
    spec: dict,
) -> User:
    role = spec["role"]
    partner_id = None if role in ("master_admin", "customer") else partner.id
    user = User(
        role=role,
        partner_id=partner_id,
        full_name=spec["full_name"],
        mobile=spec["mobile"],
        email=spec["email"],
        status="active",
    )
    db.add(user)
    db.flush()
    if role == "partner_owner":
        partner.primary_owner_user_id = user.id
    if role == "service_partner":
        db.add(
            ServicePartnerProfile(
                user_id=user.id,
                partner_id=partner.id,
                kyc_status="approved",
            )
        )
        db.add(ServicePartnerPincode(user_id=user.id, pincode="682001"))
        db.add(ServicePartnerPincode(user_id=user.id, pincode="682011"))
        for cat in cats:
            db.add(ServicePartnerCategory(user_id=user.id, category_id=cat.id))
    return user


def _seed_geo_and_catalog(db: Session) -> None:
    pins = [
        ("682001", "Ernakulam", "Kochi"),
        ("682011", "Ernakulam", "Kaloor"),
        ("695001", "Thiruvananthapuram", "East Fort"),
        ("673001", "Kozhikode", "SM Street"),
    ]
    for code, dist, loc in pins:
        if db.get(Pincode, code) is None:
            db.add(Pincode(pincode=code, district=dist, locality=loc, state="Kerala"))

    for slug, en, ml, rank in SEED_CATEGORIES:
        existing = db.scalar(select(ServiceCategory).where(ServiceCategory.slug == slug))
        if existing:
            continue
        cat = ServiceCategory(
            slug=slug,
            name_en=en,
            name_ml=ml,
            description_en=f"Home visit for {en.lower()}.",
            skill_set_en="Certified home technician",
            featured_rank=rank,
            icon="build",
        )
        db.add(cat)
        db.flush()
        for i, text in enumerate(PROBLEMS):
            db.add(
                CategoryIssueTemplate(
                    category_id=cat.id,
                    text_en=text,
                    text_ml=text,
                    sort_order=i,
                    featured_rank=(i + 1) if i < 5 else None,
                )
            )
    db.flush()


def _seed_partner_org(db: Session) -> Partner:
    partner = db.scalar(select(Partner).limit(1))
    if partner:
        return partner
    partner = Partner(
        org_type="company",
        trade_name="Kerala HomeCare",
        legal_name="Kerala HomeCare Pvt Ltd",
        status="approved",
        license_fee_amount=Decimal("15000"),
        commission_percent=Decimal("10"),
        office_pincode="682001",
        office_address="MG Road, Kochi",
        personal_email="owner@homecare.local",
        company_email="ops@homecare.local",
    )
    db.add(partner)
    db.flush()
    for pin in ("682001", "682011"):
        db.add(PartnerPincode(partner_id=partner.id, pincode=pin))
    for cat in db.scalars(select(ServiceCategory)):
        db.add(
            PartnerCategoryPricing(
                partner_id=partner.id,
                category_id=cat.id,
                enabled=True,
                visit_charge=Decimal("499"),
            )
        )
    db.flush()
    return partner


def _seed_invoice(db: Session) -> None:
    partner = db.scalar(select(Partner).limit(1))
    if partner is None:
        return
    if db.scalar(select(SaasInvoice).limit(1)):
        return
    today = date.today()
    db.add(
        SaasInvoice(
            partner_id=partner.id,
            period_start=today.replace(day=1),
            period_end=today,
            amount=Decimal("15000"),
            status="sent",
        )
    )
    db.flush()


_IMAGE_MIME = {
    ".webp": "image/webp",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def _seed_image_bytes(name: str | None) -> tuple[bytes | None, str]:
    if not name:
        return None, ""
    img = Path(__file__).resolve().parent / "data" / "product_images" / name
    if not img.is_file():
        return None, ""
    return img.read_bytes(), _IMAGE_MIME.get(img.suffix.lower(), "application/octet-stream")


def _store_seed_image(product: Product, data: bytes, mime: str) -> None:
    """Seed-time image store: R2 when configured, else DB blob."""
    from app.services import image_store

    product.image_mime = mime
    if image_store.r2_enabled():
        product.image_key = image_store.put_product_image(product.id, data, mime)
        product.image_bytes = None
    else:
        product.image_bytes = data


def _seed_products(db: Session) -> None:
    path = Path(__file__).resolve().parent / "data" / "products_seed.json"
    rows = json.loads(path.read_text())
    for r in rows:
        existing = db.scalar(select(Product).where(Product.sku == r["sku"]))
        if existing is not None:
            # Backfill: rows seeded before images existed get theirs now.
            if existing.image_bytes is None and not existing.image_key:
                data, mime = _seed_image_bytes(r.get("image_file"))
                if data is not None:
                    _store_seed_image(existing, data, mime)
            continue
        fields = {k: v for k, v in r.items() if k != "image_file"}
        product = Product(**fields)
        db.add(product)
        db.flush()  # id assigned for the R2 object key
        data, mime = _seed_image_bytes(r.get("image_file"))
        if data is not None:
            _store_seed_image(product, data, mime)
    db.flush()
