from __future__ import annotations

import json
import urllib.request

from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AuditLog, Notification, User, utcnow


class ChannelError(RuntimeError):
    """Outbound channel send failed. The DB row is still the fallback."""


class ChannelNotConfigured(ChannelError):
    """Channel selected but its credentials are missing."""


class NotificationChannel:
    """Outbound fan-out for dispatch events (offer, accept, reassign, ...).

    Console today; WhatsApp BSP later by dropping credentials into settings.
    Call sites stay the same.
    """

    name = "base"

    def send(
        self,
        *,
        user_id: str,
        mobile: str,
        ntype: str,
        booking_id: str | None,
        payload: dict,
    ) -> None:
        raise NotImplementedError


class ConsoleNotificationChannel(NotificationChannel):
    """Dev default: print to server stdout. Always available."""

    name = "console"

    def send(self, *, user_id, mobile, ntype, booking_id, payload) -> None:
        extra = f" booking={booking_id}" if booking_id else ""
        print(f"[NOTIFY] user={user_id} type={ntype}{extra} {payload}", flush=True)


class WhatsAppNotificationChannel(NotificationChannel):
    """BSP-backed WhatsApp sender. Requires settings; fails closed otherwise.

    The payload shape is intentionally generic (event + params) so any BSP
    template mapping can sit behind api_base without touching dispatch code.
    """

    name = "whatsapp"

    def __init__(self, *, api_base: str, api_key: str, sender: str) -> None:
        if not api_base or not api_key or not sender:
            raise ChannelNotConfigured("whatsapp credentials missing")
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.sender = sender

    def send(self, *, user_id, mobile, ntype, booking_id, payload) -> None:
        if not mobile:
            raise ChannelError("no mobile for whatsapp send")
        body = json.dumps(
            {
                "from": self.sender,
                "to": mobile,
                "event": ntype,
                "booking_id": booking_id,
                "params": payload,
            }
        ).encode()
        req = urllib.request.Request(
            f"{self.api_base}/messages",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                if res.status >= 400:
                    raise ChannelError(f"whatsapp http {res.status}")
        except ChannelError:
            raise
        except Exception as exc:
            raise ChannelError(f"whatsapp send failed: {exc}") from exc


_override: NotificationChannel | None = None


def configure_notification_channel(channel: NotificationChannel | None) -> None:
    """Pin a channel (tests / bootstrap). None restores settings default."""
    global _override
    _override = channel


def get_notification_channel() -> NotificationChannel:
    if _override is not None:
        return _override
    if settings.whatsapp_enabled:
        return WhatsAppNotificationChannel(
            api_base=settings.whatsapp_api_base,
            api_key=settings.whatsapp_api_key,
            sender=settings.whatsapp_sender,
        )
    return ConsoleNotificationChannel()


def notify(db: Session, user_id: str, ntype: str, booking_id: str | None = None, **payload) -> None:
    # Core insert (not ORM add): identical row — id/created_at client-side
    # defaults still fire — but without per-row unit-of-work overhead. A
    # repool sweep writes tens of thousands of these.
    db.execute(
        insert(Notification).values(
            user_id=user_id,
            type=ntype,
            booking_id=booking_id,
            payload=json.dumps(payload),
        )
    )
    try:
        user = db.get(User, user_id)
        get_notification_channel().send(
            user_id=user_id,
            mobile=user.mobile if user else "",
            ntype=ntype,
            booking_id=booking_id,
            payload=payload,
        )
    except (ChannelError, ChannelNotConfigured) as exc:
        # Fallback: the DB + in-app notification above still stands.
        print(f"[NOTIFY] channel_error user={user_id} type={ntype} err={exc}", flush=True)


def audit(db: Session, actor: str | None, action: str, entity_type: str, entity_id: str, **meta) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            meta=json.dumps(meta),
            created_at=utcnow(),
        )
    )
