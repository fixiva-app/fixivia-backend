from __future__ import annotations

from app.config import settings
from app.domain.otp import OtpPurpose
from app.services.notify import WhatsAppNotificationChannel


class OtpSender:
    def send(self, purpose: OtpPurpose, destination: str, code: str, meta: str | None = None) -> None:
        raise NotImplementedError


class ConsoleOtpSender(OtpSender):
    """Dev mock: print to server stdout. Swap for WhatsApp later; call sites stay the same."""

    def send(self, purpose: OtpPurpose, destination: str, code: str, meta: str | None = None) -> None:
        extra = f" {meta}" if meta else ""
        print(f"[OTP] purpose={purpose.value} mobile={destination} code={code}{extra}", flush=True)


class WhatsAppOtpSender(OtpSender):
    """Sends OTP codes through the configured WhatsApp BSP channel."""

    def __init__(self) -> None:
        self._channel = WhatsAppNotificationChannel(
            api_base=settings.whatsapp_api_base,
            api_key=settings.whatsapp_api_key,
            sender=settings.whatsapp_sender,
        )

    def send(self, purpose: OtpPurpose, destination: str, code: str, meta: str | None = None) -> None:
        booking_id = None
        if meta and meta.startswith("booking_id="):
            booking_id = meta.split("=", 1)[1]
        self._channel.send(
            user_id="",
            mobile=destination,
            ntype=f"otp_{purpose.value}",
            booking_id=booking_id,
            payload={"code": code},
        )


def default_otp_sender() -> OtpSender:
    if settings.whatsapp_enabled:
        return WhatsAppOtpSender()
    return ConsoleOtpSender()
