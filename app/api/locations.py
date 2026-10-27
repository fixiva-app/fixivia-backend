from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import CommitRoute, get_db
from app.deps import require_roles
from app.models import Asset, ShopLocation
from app.services.notify import audit

router = APIRouter(prefix="/v1", tags=["locations"], route_class=CommitRoute)

# Business decision: shop locations belong to the business — owners only.
_ADMIN = ("partner_owner",)

_CODE_RE = re.compile(r"^[A-Z0-9]{3}$")


def _location_json(loc: ShopLocation, asset_count: int = 0) -> dict:
    return {
        "id": loc.id,
        "partner_id": loc.partner_id,
        "name": loc.name,
        "code": loc.code,
        "is_active": loc.is_active,
        "asset_count": asset_count,
    }


def _name(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        raise HTTPException(400, "name_required")
    if len(text) > 120:
        raise HTTPException(422, "name_too_long")
    return text


def _code(raw: str) -> str:
    code = (raw or "").strip().upper()
    if not _CODE_RE.match(code):
        raise HTTPException(422, "bad_location_code")
    return code


def _get_location(db: Session, partner_id: str, location_id: str) -> ShopLocation:
    loc = db.get(ShopLocation, location_id)
    if loc is None or loc.partner_id != partner_id:
        raise HTTPException(404, "not_found")
    return loc


def _check_name_free(db: Session, partner_id: str, name: str, ignore_id: str | None = None) -> None:
    clash = db.scalar(
        select(ShopLocation).where(
            ShopLocation.partner_id == partner_id,
            func.lower(ShopLocation.name) == name.lower(),
        )
    )
    if clash is not None and clash.id != ignore_id:
        raise HTTPException(409, "location_name_taken")


class LocationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str
    code: str


class LocationUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = None
    is_active: bool | None = None


@router.get("/locations")
def list_locations(
    db: Session = Depends(get_db),
    user=Depends(require_roles(*_ADMIN)),
) -> list[dict]:
    if not user.partner_id:
        raise HTTPException(403, "no_partner")
    locs = list(
        db.scalars(
            select(ShopLocation)
            .where(ShopLocation.partner_id == user.partner_id)
            .order_by(ShopLocation.name)
        )
    )
    counts: dict[str, int] = {}
    for code, n in db.execute(
        select(Asset.location_code, func.count(Asset.id))
        .where(Asset.partner_id == user.partner_id)
        .group_by(Asset.location_code)
    ):
        counts[code] = n
    return [_location_json(loc, counts.get(loc.code, 0)) for loc in locs]


@router.post("/locations")
def create_location(
    body: LocationCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles(*_ADMIN)),
) -> dict:
    if not user.partner_id:
        raise HTTPException(403, "no_partner")
    name = _name(body.name)
    code = _code(body.code)
    if (
        db.scalar(
            select(ShopLocation).where(
                ShopLocation.partner_id == user.partner_id,
                ShopLocation.code == code,
            )
        )
        is not None
    ):
        raise HTTPException(409, "location_code_taken")
    _check_name_free(db, user.partner_id, name)
    loc = ShopLocation(partner_id=user.partner_id, name=name, code=code)
    db.add(loc)
    db.flush()
    audit(db, user.id, "location_create", "shop_location", loc.id)
    return _location_json(loc)


@router.put("/locations/{location_id}")
def update_location(
    location_id: str,
    body: LocationUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_roles(*_ADMIN)),
) -> dict:
    """Partial update. The code is immutable — printed on QR tags."""
    if not user.partner_id:
        raise HTTPException(403, "no_partner")
    loc = _get_location(db, user.partner_id, location_id)
    if body.name is not None:
        name = _name(body.name)
        _check_name_free(db, user.partner_id, name, ignore_id=loc.id)
        loc.name = name
    if body.is_active is not None:
        loc.is_active = body.is_active
    db.flush()
    audit(db, user.id, "location_update", "shop_location", loc.id)
    return _location_json(loc)


@router.delete("/locations/{location_id}")
def delete_location(
    location_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles(*_ADMIN)),
) -> dict:
    if not user.partner_id:
        raise HTTPException(403, "no_partner")
    loc = _get_location(db, user.partner_id, location_id)
    used = db.scalar(
        select(func.count(Asset.id)).where(
            Asset.partner_id == user.partner_id,
            Asset.location_code == loc.code,
        )
    )
    if used:
        raise HTTPException(409, "location_in_use")
    db.delete(loc)
    db.flush()
    audit(db, user.id, "location_delete", "shop_location", location_id)
    return {"success": True}
