from __future__ import annotations

from app.models import User


def user_public(user: User) -> dict:
    return {
        "id": user.id,
        "mobile": user.mobile,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "partner_id": user.partner_id,
        "locale": user.locale,
        "status": user.status,
    }


def mask_mobile(mobile: str) -> str:
    digits = "".join(ch for ch in mobile if ch.isdigit())
    if len(digits) < 4:
        return "****"
    return f"{digits[:-4].rjust(len(digits) - 4, '*')}****{digits[-4:]}"
