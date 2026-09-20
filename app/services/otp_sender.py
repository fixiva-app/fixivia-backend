from __future__ import annotations

from app.domain.otp import OtpPurpose


class OtpSender:
    def send(self, purpose: OtpPurpose, destination: str, code: str, meta: str | None = None) -> None:
        raise NotImplementedError


class ConsoleOtpSender(OtpSender):
    """Dev mock: print to server stdout. Swap for SMS later; call sites stay the same."""

    def send(self, purpose: OtpPurpose, destination: str, code: str, meta: str | None = None) -> None:
        extra = f" {meta}" if meta else ""
        print(f"[OTP] purpose={purpose.value} mobile={destination} code={code}{extra}", flush=True)
