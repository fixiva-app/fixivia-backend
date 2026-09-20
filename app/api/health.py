from __future__ import annotations

from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"ok": True, "service": settings.app_name, "flavor": settings.flavor}
