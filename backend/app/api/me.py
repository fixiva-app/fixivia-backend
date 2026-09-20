from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user
from app.jobs.dispatch_job import dispatch_repool_open
from app.models import Notification, User
from app.services.serializers import user_public

router = APIRouter(prefix="/v1", tags=["me"])


@router.get("/me")
def me(user: User = Depends(current_user)) -> dict:
    return user_public(user)


@router.get("/notifications")
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(
        select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(100)
    )
    return [
        {
            "id": n.id,
            "type": n.type,
            "booking_id": n.booking_id,
            "payload": n.payload,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in rows
    ]


@router.post("/jobs/dispatch-repool")
def cron_repool(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    if user.role != "master_admin":
        from fastapi import HTTPException

        raise HTTPException(403, "forbidden")
    n = dispatch_repool_open(db)
    return {"open_bookings": n}
