"""Console OTP sender must stay silent.

Codes leave the backend only via the TEMP-OTP admin API
(/v1/admin/otp-code) — never via stdout. The in-memory cache behind
/v1/dev/otp-code (UI test harness) intentionally stays.
"""

from app.domain.otp import OtpPurpose
from app.services.otp_sender import ConsoleOtpSender, last_console_code


def test_console_sender_prints_nothing(capsys):
    ConsoleOtpSender().send(OtpPurpose.LOGIN, "9198000101", "123456")
    out, err = capsys.readouterr()
    assert out == "", out
    assert err == "", err


def test_console_sender_still_caches_for_dev_hook():
    ConsoleOtpSender().send(OtpPurpose.LOGIN, "9198000102", "654321")
    assert last_console_code("login", "9198000102") == "654321"
    assert last_console_code("login", "9198000101") == "123456"
