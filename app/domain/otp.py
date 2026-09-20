from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum


class OtpPurpose(StrEnum):
    REGISTER = "register"
    LOGIN = "login"
    START_WORK = "start_work"


def generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_code(code: str, pepper: str) -> str:
    return hmac.new(pepper.encode(), code.encode(), hashlib.sha256).hexdigest()


def codes_match(code: str, code_hash: str, pepper: str) -> bool:
    return hmac.compare_digest(hash_code(code, pepper), code_hash)


@dataclass(frozen=True)
class OtpChallenge:
    purpose: OtpPurpose
    destination: str
    code_hash: str
    expires_at: datetime
    consumed_at: datetime | None = None
    meta: str | None = None  # e.g. booking_id


def make_challenge(
    purpose: OtpPurpose,
    destination: str,
    pepper: str,
    ttl_minutes: int,
    now: datetime | None = None,
    code: str | None = None,
    meta: str | None = None,
) -> tuple[OtpChallenge, str]:
    now = now or datetime.now(timezone.utc)
    plaintext = code or generate_code()
    challenge = OtpChallenge(
        purpose=purpose,
        destination=destination,
        code_hash=hash_code(plaintext, pepper),
        expires_at=now + timedelta(minutes=ttl_minutes),
        meta=meta,
    )
    return challenge, plaintext


def verify_challenge(
    challenge: OtpChallenge,
    code: str,
    pepper: str,
    now: datetime | None = None,
) -> None:
    now = now or datetime.now(timezone.utc)
    if challenge.consumed_at is not None:
        raise ValueError("otp_already_used")
    if now >= challenge.expires_at:
        raise ValueError("otp_expired")
    if not codes_match(code, challenge.code_hash, pepper):
        raise ValueError("otp_invalid")


def reuse_start_work_otp(existing_hash: str | None) -> bool:
    """On reassign after drop, keep the first-accept OTP."""
    return bool(existing_hash)
