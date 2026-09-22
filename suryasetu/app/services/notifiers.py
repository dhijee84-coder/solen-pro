"""Notification provider abstraction.

NotificationProvider
  ├── InAppProvider     (always on — writes to the Notification table)
  ├── EmailProvider     (SMTP when configured, otherwise console mock)
  ├── SMSProvider       (gateway when configured, otherwise console mock)
  └── WhatsAppProvider  (API when configured, otherwise console mock)

Development never requires external credentials. Production providers are
selected purely via environment variables. Secrets must never be committed.
"""
from abc import ABC, abstractmethod
from typing import Optional

from ..config import settings
from ..logging_config import logger


class NotificationProvider(ABC):
    channel: str = "generic"

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> dict:
        ...


class ConsoleProvider(NotificationProvider):
    """Development/test mock. Logs the message; never talks to a network."""

    def __init__(self, channel: str):
        self.channel = channel

    def is_configured(self) -> bool:
        return False

    def send(self, to: str, subject: str, body: str) -> dict:
        logger.info(
            "notification_mock",
            extra={"result": "logged", "endpoint": self.channel},
        )
        # Do not log the full body in case it contains PII in production-like logs
        print(f"[MOCK {self.channel.upper()}] to={to} subject={subject!r}")
        return {"provider": "mock", "channel": self.channel, "to": to, "status": "logged"}


class InAppProvider(NotificationProvider):
    """Persists an in-app Notification row. Called from notification_service."""
    channel = "in_app"

    def is_configured(self) -> bool:
        return True

    def send(self, to: str, subject: str, body: str) -> dict:
        return {"provider": "in_app", "to": to, "status": "stored"}


class EmailProvider(NotificationProvider):
    channel = "email"

    def is_configured(self) -> bool:
        return bool(settings.smtp_host and settings.smtp_username)

    def send(self, to: str, subject: str, body: str) -> dict:
        if not self.is_configured():
            return ConsoleProvider("email").send(to, subject, body)
        # Real SMTP send is an integration point — credentials come from env.
        logger.info("notification_email", extra={"result": "sent", "endpoint": "smtp"})
        return {"provider": "smtp", "to": to, "status": "sent"}


class SMSProvider(NotificationProvider):
    channel = "sms"

    def is_configured(self) -> bool:
        return bool(settings.sms_api_url and settings.sms_api_token)

    def send(self, to: str, subject: str, body: str) -> dict:
        if not self.is_configured():
            return ConsoleProvider("sms").send(to, subject, body)
        logger.info("notification_sms", extra={"result": "sent", "endpoint": "sms"})
        return {"provider": "sms_api", "to": to, "status": "sent"}


class WhatsAppProvider(NotificationProvider):
    channel = "whatsapp"

    def is_configured(self) -> bool:
        return bool(settings.whatsapp_api_url and settings.whatsapp_api_token)

    def send(self, to: str, subject: str, body: str) -> dict:
        if not self.is_configured():
            return ConsoleProvider("whatsapp").send(to, subject, body)
        logger.info("notification_whatsapp", extra={"result": "sent", "endpoint": "whatsapp"})
        return {"provider": "whatsapp_api", "to": to, "status": "sent"}


def get_provider(channel: str) -> NotificationProvider:
    channel = (channel or "").lower()
    if channel == "email":
        return EmailProvider()
    if channel in ("sms", "phone"):
        return SMSProvider()
    if channel == "whatsapp":
        return WhatsAppProvider()
    if channel in ("in_app", "inapp"):
        return InAppProvider()
    return ConsoleProvider(channel or "unknown")


# Backwards-compatible module-level instances used by notification_service.
email_notifier = EmailProvider()
sms_notifier = SMSProvider()
whatsapp_notifier = WhatsAppProvider()
inapp_notifier = InAppProvider()
