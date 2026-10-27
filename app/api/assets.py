from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import CommitRoute, get_db
from app.deps import require_roles
from app.models import Asset, User
from app.services.notify import audit

router = APIRouter(prefix="/v1", tags=["assets"], route_class=CommitRoute)

# Business decision: assets belong to the business — owners and admins only.
_ADMIN = ("partner_owner", "partner_admin")

ASSET_CATEGORIES = (
    "laptop",
    "desktop",
    "mobile_phone",
    "printer",
    "shredder",
    "laptop_charger",
    "mobile_charger",
    "mouse",
    "keyboard",
    "ups",
    "monitor",
    "other",
)

_CODE_RE = re.compile(r"^[A-Z0-9]{3}$")
_SIM_RE = re.compile(r"^\d{10}$")
_MAX_SEQ = 9999


def _asset_json(a: Asset) -> dict:
    return {
        "id": a.id,
        "asset_code": a.asset_code,
        "partner_id": a.partner_id,
        "name": a.name,
        "category": a.category,
        "location": a.location,
        "location_code": a.location_code,
        "assigned_to": a.assigned_to,
        "serial": a.serial,
        "has_sim": a.has_sim,
        "sim_number": a.sim_number,
    }


def _required(text: str, field: str, limit: int) -> str:
    if not text:
        raise HTTPException(400, f"{field}_required")
    if len(text) > limit:
        raise HTTPException(422, f"{field}_too_long")
    return text


def _location_code(raw: str) -> str:
    code = (raw or "").strip().upper()
    if not _CODE_RE.match(code):
        raise HTTPException(422, "bad_location_code")
    return code


def _category(raw: str) -> str:
    value = (raw or "").strip().lower()
    if value not in ASSET_CATEGORIES:
        raise HTTPException(422, "bad_category")
    return value


def _serial(raw: str | None) -> str | None:
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    if len(text) > 80:
        raise HTTPException(422, "serial_too_long")
    return text


def _sim_number(raw: str | None) -> str:
    digits = (raw or "").strip()
    if not _SIM_RE.match(digits):
        raise HTTPException(422, "bad_sim_number")
    return digits


def _check_serial_free(db: Session, serial: str | None, ignore_id: str | None = None) -> None:
    if serial is None:
        return
    clash = db.scalar(select(Asset).where(Asset.serial == serial))
    if clash is not None and clash.id != ignore_id:
        raise HTTPException(409, "serial_taken")


def _next_code(db: Session, partner_id: str, loc: str) -> str:
    prefix = f"AST-{loc}-"
    codes = db.scalars(
        select(Asset.asset_code).where(
            Asset.partner_id == partner_id,
            Asset.asset_code.like(prefix + "%"),
        )
    )
    best = 0
    for code in codes:
        try:
            best = max(best, int(code.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue
    nxt = best + 1
    if nxt > _MAX_SEQ:
        raise HTTPException(409, "code_exhausted")
    return f"{prefix}{nxt:04d}"


def _get_asset(db: Session, user: User, asset_id: str) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None or asset.partner_id != user.partner_id:
        raise HTTPException(404, "not_found")
    return asset


def _stripped() -> ConfigDict:
    return ConfigDict(str_strip_whitespace=True)


class AssetCreate(BaseModel):
    model_config = _stripped()

    name: str
    category: str
    location: str
    location_code: str
    assigned_to: str = ""
    serial: str | None = None
    has_sim: bool = False
    sim_number: str | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return _required(v, "name", 120)

    @field_validator("location")
    @classmethod
    def _location(cls, v: str) -> str:
        return _required(v, "location", 120)

    @field_validator("category")
    @classmethod
    def _category(cls, v: str) -> str:
        return _category(v)

    @field_validator("location_code")
    @classmethod
    def _loc(cls, v: str) -> str:
        return _location_code(v)

    @field_validator("assigned_to")
    @classmethod
    def _assigned(cls, v: str) -> str:
        if len(v) > 120:
            raise HTTPException(422, "assigned_to_too_long")
        return v

    @field_validator("serial")
    @classmethod
    def _serial(cls, v: str | None) -> str | None:
        return _serial(v)

    @model_validator(mode="after")
    def _sim(self) -> "AssetCreate":
        if self.has_sim:
            if not (self.sim_number or "").strip():
                raise HTTPException(400, "sim_number_required")
            self.sim_number = _sim_number(self.sim_number)
        else:
            self.sim_number = None
        return self


class AssetUpdate(BaseModel):
    model_config = _stripped()

    name: str | None = None
    category: str | None = None
    location: str | None = None
    location_code: str | None = None
    assigned_to: str | None = None
    serial: str | None = None
    has_sim: bool | None = None
    sim_number: str | None = None


@router.get("/assets")
def list_assets(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_ADMIN)),
    category: str | None = None,
    location_code: str | None = None,
    q: str | None = None,
) -> list[dict]:
    query = select(Asset).where(Asset.partner_id == user.partner_id)
    if category and category.strip():
        query = query.where(Asset.category == category.strip().lower())
    if location_code and location_code.strip():
        query = query.where(Asset.location_code == location_code.strip().upper())
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.where(
            or_(
                Asset.name.ilike(like),
                Asset.asset_code.ilike(like),
                Asset.serial.ilike(like),
                Asset.assigned_to.ilike(like),
            )
        )
    query = query.order_by(Asset.asset_code)
    return [_asset_json(a) for a in db.scalars(query)]


@router.get("/assets/{asset_id}")
def get_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_ADMIN)),
) -> dict:
    return _asset_json(_get_asset(db, user, asset_id))


@router.post("/assets")
def create_asset(
    body: AssetCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_ADMIN)),
) -> dict:
    if not user.partner_id:
        raise HTTPException(403, "no_partner")
    _check_serial_free(db, body.serial)
    asset = Asset(
        partner_id=user.partner_id,
        asset_code=_next_code(db, user.partner_id, body.location_code),
        name=body.name,
        category=body.category,
        location=body.location,
        location_code=body.location_code,
        assigned_to=body.assigned_to,
        serial=body.serial,
        has_sim=body.has_sim,
        sim_number=body.sim_number or "",
    )
    db.add(asset)
    db.flush()
    audit(db, user.id, "asset_create", "asset", asset.id)
    return _asset_json(asset)


@router.put("/assets/{asset_id}")
def update_asset(
    asset_id: str,
    body: AssetUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_ADMIN)),
) -> dict:
    """Partial update. asset_code and location_code are immutable — the code
    is printed on QR tags, so it must never change."""
    asset = _get_asset(db, user, asset_id)
    if body.location_code is not None and _location_code(body.location_code) != asset.location_code:
        raise HTTPException(422, "location_code_immutable")
    if body.name is not None:
        asset.name = _required(body.name, "name", 120)
    if body.category is not None:
        asset.category = _category(body.category)
    if body.location is not None:
        asset.location = _required(body.location, "location", 120)
    if body.assigned_to is not None:
        if len(body.assigned_to) > 120:
            raise HTTPException(422, "assigned_to_too_long")
        asset.assigned_to = body.assigned_to
    if body.serial is not None:
        serial = _serial(body.serial)
        _check_serial_free(db, serial, ignore_id=asset.id)
        asset.serial = serial
    if body.has_sim is not None:
        if body.has_sim:
            if body.sim_number is None:
                raise HTTPException(400, "sim_number_required")
            asset.sim_number = _sim_number(body.sim_number)
            asset.has_sim = True
        else:
            asset.has_sim = False
            asset.sim_number = ""
    elif body.sim_number is not None:
        if not asset.has_sim:
            raise HTTPException(422, "sim_not_enabled")
        asset.sim_number = _sim_number(body.sim_number)
    db.flush()
    audit(db, user.id, "asset_update", "asset", asset.id)
    return _asset_json(asset)


@router.delete("/assets/{asset_id}")
def delete_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_ADMIN)),
) -> dict:
    asset = _get_asset(db, user, asset_id)
    db.delete(asset)
    db.flush()
    audit(db, user.id, "asset_delete", "asset", asset_id)
    return {"ok": True, "id": asset_id}
