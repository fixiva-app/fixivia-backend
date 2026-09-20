from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user, require_roles
from app.models import (
    CategoryIssueTemplate,
    PartnerCategoryPricing,
    ServiceCategory,
    User,
)
from app.services.notify import audit

router = APIRouter(prefix="/v1", tags=["catalog"])


def _cat_json(c: ServiceCategory, db: Session) -> dict:
    issues = list(
        db.scalars(
            select(CategoryIssueTemplate)
            .where(CategoryIssueTemplate.category_id == c.id)
            .order_by(CategoryIssueTemplate.sort_order)
        )
    )
    return {
        "id": c.id,
        "slug": c.slug,
        "name_en": c.name_en,
        "name_ml": c.name_ml,
        "description_en": c.description_en,
        "skill_set_en": c.skill_set_en,
        "icon": c.icon,
        "estimated_minutes": c.estimated_minutes,
        "is_active": c.is_active,
        "featured_rank": c.featured_rank,
        "problems": [
            {
                "id": i.id,
                "text_en": i.text_en,
                "text_ml": i.text_ml,
                "featured_rank": i.featured_rank,
                "sort_order": i.sort_order,
            }
            for i in issues
        ],
    }


@router.get("/categories")
def list_categories(db: Session = Depends(get_db), active: bool | None = True) -> list[dict]:
    q = select(ServiceCategory)
    if active is True:
        q = q.where(ServiceCategory.is_active.is_(True))
    q = q.order_by(ServiceCategory.name_en)
    return [_cat_json(c, db) for c in db.scalars(q)]


class CategoryBody(BaseModel):
    slug: str
    name_en: str
    name_ml: str = ""
    description_en: str = ""
    description_ml: str = ""
    skill_set_en: str = ""
    skill_set_ml: str = ""
    icon: str = "build"
    estimated_minutes: int = 60
    is_active: bool = True
    featured_rank: int | None = None
    problems: list[dict] = []


def _validate_featured(db: Session, rank: int | None, exclude_id: str | None) -> None:
    if rank is None:
        return
    if rank < 1 or rank > 5:
        raise HTTPException(400, "featured_rank_1_5")
    q = select(ServiceCategory).where(ServiceCategory.featured_rank == rank)
    if exclude_id:
        q = q.where(ServiceCategory.id != exclude_id)
    if db.scalar(q):
        raise HTTPException(409, "featured_rank_taken")


@router.post("/categories")
def create_category(
    body: CategoryBody,
    user: User = Depends(require_roles("master_admin")),
    db: Session = Depends(get_db),
) -> dict:
    _validate_featured(db, body.featured_rank, None)
    c = ServiceCategory(**body.model_dump(exclude={"problems"}))
    db.add(c)
    db.flush()
    _replace_problems(db, c.id, body.problems)
    audit(db, user.id, "category_create", "category", c.id)
    return _cat_json(c, db)


@router.put("/categories/{cat_id}")
def update_category(
    cat_id: str,
    body: CategoryBody,
    user: User = Depends(require_roles("master_admin")),
    db: Session = Depends(get_db),
) -> dict:
    c = db.get(ServiceCategory, cat_id)
    if c is None:
        raise HTTPException(404, "not_found")
    _validate_featured(db, body.featured_rank, cat_id)
    for k, v in body.model_dump(exclude={"problems"}).items():
        setattr(c, k, v)
    old = list(db.scalars(select(CategoryIssueTemplate).where(CategoryIssueTemplate.category_id == cat_id)))
    for row in old:
        db.delete(row)
    db.flush()
    _replace_problems(db, cat_id, body.problems)
    audit(db, user.id, "category_update", "category", cat_id)
    return _cat_json(c, db)


def _replace_problems(db: Session, cat_id: str, problems: list[dict]) -> None:
    featured = [p.get("featured_rank") for p in problems if p.get("featured_rank")]
    if len(featured) != len(set(featured)):
        raise HTTPException(409, "problem_featured_dup")
    for i, p in enumerate(problems):
        rank = p.get("featured_rank")
        if rank is not None and (rank < 1 or rank > 5):
            raise HTTPException(400, "featured_rank_1_5")
        db.add(
            CategoryIssueTemplate(
                category_id=cat_id,
                text_en=p.get("text_en") or p.get("text") or "Issue",
                text_ml=p.get("text_ml") or "",
                sort_order=p.get("sort_order", i),
                featured_rank=rank,
            )
        )


class PriceBody(BaseModel):
    category_id: str
    enabled: bool = True
    visit_charge: Decimal


@router.get("/partner/pricing")
def list_pricing(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    if not user.partner_id:
        raise HTTPException(400, "no_partner")
    rows = db.scalars(select(PartnerCategoryPricing).where(PartnerCategoryPricing.partner_id == user.partner_id))
    return [
        {"category_id": r.category_id, "enabled": r.enabled, "visit_charge": str(r.visit_charge)}
        for r in rows
    ]


@router.put("/partner/pricing")
def upsert_pricing(
    body: PriceBody,
    user: User = Depends(require_roles("partner_owner", "partner_admin")),
    db: Session = Depends(get_db),
) -> dict:
    row = db.get(PartnerCategoryPricing, (user.partner_id, body.category_id))
    if row is None:
        row = PartnerCategoryPricing(partner_id=user.partner_id, category_id=body.category_id)
        db.add(row)
    row.enabled = body.enabled
    row.visit_charge = body.visit_charge
    return {"category_id": row.category_id, "enabled": row.enabled, "visit_charge": str(row.visit_charge)}
