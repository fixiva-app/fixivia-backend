from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import AuditLog, Notification, utcnow


def notify(db: Session, user_id: str, ntype: str, booking_id: str | None = None, **payload) -> None:
    row = Notification(
        user_id=user_id,
        type=ntype,
        booking_id=booking_id,
        payload=json.dumps(payload),
    )
    db.add(row)
    extra = f" booking={booking_id}" if booking_id else ""
    print(f"[NOTIFY] user={user_id} type={ntype}{extra} {payload}", flush=True)


def audit(db: Session, actor: str | None, action: str, entity_type: str, entity_id: str, **meta) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            meta=json.dumps(meta),
            created_at=utcnow(),
        )
    )
