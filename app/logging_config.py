"""Structured application logging. Never log secrets (passwords, OTPs, tokens)."""
import json
import logging
import sys
from datetime import datetime, timezone

from .config import settings

SENSITIVE_KEYS = {
    "password", "hashed_password", "otp", "code", "token", "access_token",
    "authorization", "secret", "secret_key", "smtp_password", "sms_api_token",
    "whatsapp_api_token", "dev_otp", "cookie",
}


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in ("method", "path", "status", "duration_ms", "user_id", "role",
                    "endpoint", "result", "ip", "request_id"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info and record.exc_info[1]:
            payload["error"] = type(record.exc_info[1]).__name__
            if settings.is_debug:
                payload["error_detail"] = str(record.exc_info[1])
        return json.dumps(payload, default=str)


def redact(value: str) -> str:
    if not value:
        return value
    return "[redacted]"


def setup_logging():
    root = logging.getLogger("suryasetu")
    if root.handlers:
        return root
    root.setLevel(getattr(logging, (settings.log_level or "INFO").upper(), logging.INFO))
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    root.addHandler(handler)
    root.propagate = False
    return root


logger = setup_logging()
