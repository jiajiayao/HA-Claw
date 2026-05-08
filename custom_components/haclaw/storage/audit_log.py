"""Audit log helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
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


def append_audit_event(path: Path, event: dict[str, Any]) -> None:
    """Append one redacted audit event to HAclaw managed JSONL storage."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        **_redact(event),
    }
    with path.open("a", encoding="utf-8") as audit_file:
        audit_file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***REDACTED***" if str(key).lower() in SENSITIVE_KEYS else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value
