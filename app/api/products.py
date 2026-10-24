from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import CommitRoute, get_db
from app.deps import require_roles
from app.models import Product, User
from app.services import image_store
from app.services.notify import audit

router = APIRouter(prefix="/v1", tags=["products"], route_class=CommitRoute)

_ADMIN = ("master_admin", "partner_owner")
_MAX_IMAGE = 2 * 1024 * 1024


def _product_json(p: Product) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "brand": p.brand,
        "model": p.model,
        "sku": p.sku,
        "category": p.category,
        "subcategory": p.subcategory,
        "capacity": p.capacity,
        "technology": p.technology,
        "application": p.application,
        "badge": p.badge,
        "description": p.description,
        "features": p.features or [],
        "specifications": p.specifications or {},
        "applications": p.applications or [],
        "source_url": p.source_url,
        "price_mrp": str(p.price_mrp) if p.price_mrp is not None else None,
        "price_offer": str(p.price_offer) if p.price_offer is not None else None,
        "has_image": p.image_bytes is not None or bool(p.image_key),
        "image_mime": p.image_mime,
        "is_active": p.is_active,
    }


def _clean(value: str | None, field: str) -> str:
    text = (value or "").strip()
    if not text:
        raise HTTPException(400, f"{field}_required")
    return text


def _opt_decimal(raw: str | None, field: str) -> Decimal | None:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        value = Decimal(str(raw).strip())
    except InvalidOperation:
        raise HTTPException(422, f"bad_{field}") from None
    if value < 0:
        raise HTTPException(422, f"bad_{field}")
    return value


def _opt_json_list(raw: str | None, field: str) -> list:
    if raw is None or str(raw).strip() == "":
        return []
    try:
        parsed = json.loads(raw)
    except ValueError:
        raise HTTPException(422, f"bad_{field}") from None
    if not isinstance(parsed, list):
        raise HTTPException(422, f"bad_{field}")
    return parsed


def _opt_json_dict(raw: str | None, field: str) -> dict:
    if raw is None or str(raw).strip() == "":
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError:
        raise HTTPException(422, f"bad_{field}") from None
    if not isinstance(parsed, dict):
        raise HTTPException(422, f"bad_{field}")
    return parsed


async def _read_image(image: UploadFile | None) -> tuple[bytes | None, str]:
    if image is None or not image.filename:
        return None, ""
    if not (image.content_type or "").startswith("image/"):
        raise HTTPException(400, "bad_image_type")
    data = await image.read()
    if len(data) > _MAX_IMAGE:
        raise HTTPException(400, "image_too_large")
    if not data:
        return None, ""
    return data, image.content_type or "application/octet-stream"


@router.get("/products")
def list_products(
    db: Session = Depends(get_db),
    active: str | None = "true",
    brand: str | None = None,
    category: str | None = None,
    q: str | None = None,
) -> list[dict]:
    mode = (active or "true").strip().lower()
    if mode not in ("true", "false", "all"):
        raise HTTPException(422, "bad_active")
    query = select(Product)
    if mode == "true":
        query = query.where(Product.is_active.is_(True))
    elif mode == "false":
        query = query.where(Product.is_active.is_(False))
    if brand:
        query = query.where(Product.brand == brand.strip())
    if category:
        query = query.where(Product.category == category.strip())
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.where(
            or_(Product.name.ilike(like), Product.model.ilike(like),
                Product.sku.ilike(like)))
    query = query.order_by(Product.brand, Product.name)
    return [_product_json(p) for p in db.scalars(query)]


@router.get("/products/{product_id}")
def get_product(product_id: str, db: Session = Depends(get_db)) -> dict:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "not_found")
    return _product_json(product)


@router.get("/products/{product_id}/image")
def get_product_image(product_id: str, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "not_found")
    if product.image_key and image_store.r2_enabled():
        try:
            data = image_store.get_product_image(product.image_key)
        except Exception:
            raise HTTPException(502, "image_store_error") from None
        return Response(content=data,
                        media_type=product.image_mime or "application/octet-stream")
    if not product.image_bytes:
        raise HTTPException(404, "not_found")
    return Response(content=product.image_bytes,
                    media_type=product.image_mime or "application/octet-stream")


@router.post("/products")
async def create_product(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_ADMIN)),
    name: str = Form(""),
    brand: str = Form(""),
    model: str = Form(""),
    sku: str = Form(""),
    category: str = Form(""),
    subcategory: str = Form(""),
    capacity: str = Form(""),
    technology: str = Form(""),
    application: str = Form(""),
    badge: str = Form(""),
    description: str = Form(""),
    features: str | None = Form(None),
    specifications: str | None = Form(None),
    applications: str | None = Form(None),
    source_url: str = Form(""),
    price_mrp: str | None = Form(None),
    price_offer: str | None = Form(None),
    image: UploadFile | None = File(None),
) -> dict:
    clean_sku = _clean(sku, "sku")
    if db.scalar(select(Product).where(Product.sku == clean_sku)):
        raise HTTPException(409, "sku_taken")
    data, mime = await _read_image(image)
    product = Product(
        name=_clean(name, "name"), brand=_clean(brand, "brand"),
        model=model.strip(), sku=clean_sku,
        category=_clean(category, "category"),
        subcategory=subcategory.strip(), capacity=capacity.strip(),
        technology=technology.strip(), application=application.strip(),
        badge=badge.strip(), description=description.strip(),
        features=_opt_json_list(features, "features"),
        specifications=_opt_json_dict(specifications, "specifications"),
        applications=_opt_json_list(applications, "applications"),
        source_url=source_url.strip(),
        price_mrp=_opt_decimal(price_mrp, "price_mrp"),
        price_offer=_opt_decimal(price_offer, "price_offer"),
        image_bytes=data, image_mime=mime, is_active=True,
    )
    db.add(product)
    db.flush()
    if data is not None and image_store.r2_enabled():
        product.image_key = image_store.put_product_image(product.id, data, mime)
        product.image_bytes = None
        db.flush()
    audit(db, user.id, "product_create", "product", product.id)
    return _product_json(product)


@router.put("/products/{product_id}")
async def update_product(
    product_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_ADMIN)),
    name: str | None = Form(None),
    brand: str | None = Form(None),
    model: str | None = Form(None),
    sku: str | None = Form(None),
    category: str | None = Form(None),
    subcategory: str | None = Form(None),
    capacity: str | None = Form(None),
    technology: str | None = Form(None),
    application: str | None = Form(None),
    badge: str | None = Form(None),
    description: str | None = Form(None),
    features: str | None = Form(None),
    specifications: str | None = Form(None),
    applications: str | None = Form(None),
    source_url: str | None = Form(None),
    price_mrp: str | None = Form(None),
    price_offer: str | None = Form(None),
    image: UploadFile | None = File(None),
) -> dict:
    """Partial update: only sent fields change; sent-but-blank required
    fields are rejected."""
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "not_found")
    if sku is not None:
        clean_sku = _clean(sku, "sku")
        clash = db.scalar(select(Product).where(Product.sku == clean_sku))
        if clash is not None and clash.id != product.id:
            raise HTTPException(409, "sku_taken")
        product.sku = clean_sku
    if name is not None:
        product.name = _clean(name, "name")
    if brand is not None:
        product.brand = _clean(brand, "brand")
    if category is not None:
        product.category = _clean(category, "category")
    if model is not None:
        product.model = model.strip()
    if subcategory is not None:
        product.subcategory = subcategory.strip()
    if capacity is not None:
        product.capacity = capacity.strip()
    if technology is not None:
        product.technology = technology.strip()
    if application is not None:
        product.application = application.strip()
    if badge is not None:
        product.badge = badge.strip()
    if description is not None:
        product.description = description.strip()
    if features is not None:
        product.features = _opt_json_list(features, "features")
    if specifications is not None:
        product.specifications = _opt_json_dict(specifications, "specifications")
    if applications is not None:
        product.applications = _opt_json_list(applications, "applications")
    if source_url is not None:
        product.source_url = source_url.strip()
    if price_mrp is not None:
        product.price_mrp = _opt_decimal(price_mrp, "price_mrp")
    if price_offer is not None:
        product.price_offer = _opt_decimal(price_offer, "price_offer")
    data, mime = await _read_image(image)
    if data is not None:
        # One live store at a time: the write sets one, clears the other.
        if image_store.r2_enabled():
            product.image_key = image_store.put_product_image(product.id, data, mime)
            product.image_bytes = None
        else:
            product.image_bytes = data
            product.image_key = None
        product.image_mime = mime
    db.flush()
    audit(db, user.id, "product_update", "product", product.id)
    return _product_json(product)


@router.delete("/products/{product_id}")
def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_ADMIN)),
) -> dict:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "not_found")
    db.delete(product)
    db.flush()
    audit(db, user.id, "product_delete", "product", product_id)
    return {"ok": True, "id": product_id}


@router.post("/products/{product_id}/status")
def set_product_status(
    product_id: str,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*_ADMIN)),
) -> dict:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "not_found")
    flag = body.get("is_active")
    if not isinstance(flag, bool):
        raise HTTPException(422, "bad_is_active")
    product.is_active = flag
    db.flush()
    audit(db, user.id, "product_status", "product", product_id)
    return _product_json(product)
