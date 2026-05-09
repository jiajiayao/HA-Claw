"""Shared redaction helpers for HAclaw managed storage."""

from __future__ import annotations

import re
from typing import Any


SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "cookie",
    "password",
    "refresh_token",
    "secret",
    "token",
}

REDACTED = "***REDACTED***"

_SENSITIVE_ASSIGNMENT_RE = re.compile(
    rf"(?i)\b({'|'.join(re.escape(key) for key in sorted(SENSITIVE_KEYS))})"
    r"(\s*[:=]\s*)"
    r"([^\s,;&]+)"
)


def redact_sensitive(value: Any) -> Any:
    """Return value with known secret-like fields replaced."""
    if isinstance(value, dict):
        return {
            key: REDACTED
            if str(key).lower() in SENSITIVE_KEYS
            else redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, str):
        return _SENSITIVE_ASSIGNMENT_RE.sub(rf"\1\2{REDACTED}", value)
    return value
