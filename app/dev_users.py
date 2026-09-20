"""Inject one account per role. Local / flavor=dev only.

    cd backend
    source .venv/bin/activate
    python -m app.dev_users
"""

from __future__ import annotations

from app.config import settings
from app.db import SessionLocal, init_db
from app.seed import ensure_dev_users
from app.services.tokens import issue_token


def inject_payload(db) -> list[dict]:
    users = ensure_dev_users(db)
    accounts = []
    for user in users:
        accounts.append(
            {
                "mobile": user.mobile,
                "role": user.role,
                "full_name": user.full_name,
                "email": user.email,
                "user": {
                    "id": user.id,
                    "mobile": user.mobile,
                    "full_name": user.full_name,
                    "email": user.email,
                    "role": user.role,
                    "partner_id": user.partner_id,
                    "locale": user.locale,
                    "status": user.status,
                },
                "token": issue_token(
                    user_id=user.id,
                    role=user.role,
                    partner_id=user.partner_id,
                ),
            }
        )
    return accounts


def main() -> None:
    if settings.flavor != "dev":
        raise SystemExit("Refusing to inject users: flavor is not dev")
    init_db()
    db = SessionLocal()
    try:
        accounts = inject_payload(db)
    finally:
        db.close()
    print("Dev users (OTP login, or paste token). Re-run is safe.\n")
    for acc in accounts:
        print(f"  {acc['role']:<18}  {acc['mobile']}  {acc['full_name']}")
    print("\nLog in on the app with the mobile + OTP from the API console.")
    print("Or POST /v1/dev/inject-users while flavor=dev to get JWTs.\n")
    for acc in accounts:
        print(f"{acc['role']} token:\n{acc['token']}\n")


if __name__ == "__main__":
    main()
