from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.services.tokens import parse_token

bearer = HTTPBearer(auto_error=False)


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(401, "missing_token")
    try:
        payload = parse_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(401, "invalid_token") from exc
    user = db.get(User, payload["sub"])
    if user is None or user.status == "suspended":
        raise HTTPException(401, "user_inactive")
    return user


def require_roles(*roles: str):
    def inner(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "forbidden")
        return user

    return inner
