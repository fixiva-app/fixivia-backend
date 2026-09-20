from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings

ROLES = (
    "master_admin",
    "partner_owner",
    "partner_admin",
    "service_partner",
    "customer",
)


def issue_token(*, user_id: str, role: str, partner_id: str | None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "partner_id": partner_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=settings.jwt_hours)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def parse_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
