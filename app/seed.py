from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Partner,
    PartnerCategoryPricing,
    PartnerPincode,
    Pincode,
    SaasInvoice,
    ServiceCategory,
    CategoryIssueTemplate,
    ServicePartnerCategory,
    ServicePartnerPincode,
    ServicePartnerProfile,
    User,
    utcnow,
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
    if db.scalar(select(User).limit(1)):
        return
    pins = [
        ("682001", "Ernakulam", "Kochi"),
        ("682011", "Ernakulam", "Kaloor"),
        ("695001", "Thiruvananthapuram", "East Fort"),
        ("673001", "Kozhikode", "SM Street"),
    ]
    for code, dist, loc in pins:
        db.add(Pincode(pincode=code, district=dist, locality=loc, state="Kerala"))

    cats: list[ServiceCategory] = []
    for slug, en, ml, rank in SEED_CATEGORIES:
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
        cats.append(cat)
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

    master = User(
        role="master_admin",
        full_name="Fixiva Master",
        mobile="9000000001",
        email="master@fixiva.local",
        status="active",
    )
    db.add(master)
    db.flush()

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
    owner = User(
        role="partner_owner",
        partner_id=partner.id,
        full_name="Anil Partner",
        mobile="9000000002",
        email="owner@homecare.local",
        status="active",
    )
    db.add(owner)
    db.flush()
    partner.primary_owner_user_id = owner.id
    for pin in ("682001", "682011"):
        db.add(PartnerPincode(partner_id=partner.id, pincode=pin))
    for cat in cats:
        db.add(
            PartnerCategoryPricing(
                partner_id=partner.id,
                category_id=cat.id,
                enabled=True,
                visit_charge=Decimal("499"),
            )
        )

    sp = User(
        role="service_partner",
        partner_id=partner.id,
        full_name="Ravi Technician",
        mobile="9000000003",
        email="ravi@homecare.local",
        status="active",
    )
    db.add(sp)
    db.flush()
    db.add(
        ServicePartnerProfile(
            user_id=sp.id,
            partner_id=partner.id,
            kyc_status="approved",
        )
    )
    db.add(ServicePartnerPincode(user_id=sp.id, pincode="682001"))
    db.add(ServicePartnerPincode(user_id=sp.id, pincode="682011"))
    for cat in cats:
        db.add(ServicePartnerCategory(user_id=sp.id, category_id=cat.id))

    cust = User(
        role="customer",
        full_name="Meera Customer",
        mobile="9000000004",
        email="meera@example.com",
        status="active",
    )
    db.add(cust)

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
    db.commit()
    print("[SEED] demo mobiles master=9000000001 owner=9000000002 sp=9000000003 customer=9000000004", flush=True)
