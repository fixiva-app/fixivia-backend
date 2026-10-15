"""Unit tests for auth dependencies (token -> user -> roles)."""

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.db import SessionLocal, init_db
from app.deps import current_user, require_roles
from app.models import User
from app.services.tokens import issue_token

init_db()


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_missing_token_401():
    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as ei:
            current_user(None, db)
        assert (ei.value.status_code, ei.value.detail) == (401, "missing_token")
    finally:
        db.close()


def test_invalid_token_401():
    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as ei:
            current_user(_creds("not-a-jwt"), db)
        assert (ei.value.status_code, ei.value.detail) == (401, "invalid_token")
    finally:
        db.close()


def _user(mobile: str, status: str = "active") -> User:
    db = SessionLocal()
    try:
        user = User(role="customer", mobile=mobile, full_name="T",
                    email="", locale="en", status=status)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def test_unknown_or_suspended_user_401():
    db = SessionLocal()
    try:
        ghost = issue_token(user_id="00000000-0000-0000-0000-000000000000",
                            role="customer", partner_id=None)
        with pytest.raises(HTTPException) as ei:
            current_user(_creds(ghost), db)
        assert (ei.value.status_code, ei.value.detail) == (401, "user_inactive")
        suspended = _user("9188888801", status="suspended")
        tok = issue_token(user_id=suspended.id, role="customer", partner_id=None)
        with pytest.raises(HTTPException) as ei:
            current_user(_creds(tok), db)
        assert (ei.value.status_code, ei.value.detail) == (401, "user_inactive")
    finally:
        db.close()


def test_current_user_ok_and_roles():
    user = _user("9188888802")
    tok = issue_token(user_id=user.id, role="customer", partner_id=None)
    db = SessionLocal()
    try:
        who = current_user(_creds(tok), db)
        assert who.id == user.id
        assert require_roles("customer", "sp")(who).id == user.id
        with pytest.raises(HTTPException) as ei:
            require_roles("master_admin")(who)
        assert (ei.value.status_code, ei.value.detail) == (403, "forbidden")
    finally:
        db.close()
