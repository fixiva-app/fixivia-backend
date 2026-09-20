from datetime import datetime, timedelta, timezone

import pytest

from app.domain.otp import (
    OtpPurpose,
    codes_match,
    generate_code,
    make_challenge,
    reuse_start_work_otp,
    verify_challenge,
)


def test_generate_code_is_six_digits():
    code = generate_code()
    assert len(code) == 6
    assert code.isdigit()


def test_hash_is_not_plaintext():
    ch, code = make_challenge(OtpPurpose.LOGIN, "+919000000000", "pepper", 10)
    assert code not in ch.code_hash
    assert codes_match(code, ch.code_hash, "pepper")
    assert not codes_match("000000", ch.code_hash, "pepper")


def test_verify_success_and_expiry_and_wrong_code():
    now = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
    ch, code = make_challenge(OtpPurpose.REGISTER, "+91", "p", 10, now=now, code="123456")
    verify_challenge(ch, "123456", "p", now=now)
    with pytest.raises(ValueError, match="otp_invalid"):
        verify_challenge(ch, "000000", "p", now=now)
    with pytest.raises(ValueError, match="otp_expired"):
        verify_challenge(ch, "123456", "p", now=now + timedelta(minutes=11))


def test_start_work_otp_reused_on_reassign():
    assert reuse_start_work_otp("abc") is True
    assert reuse_start_work_otp(None) is False
    assert reuse_start_work_otp("") is False
