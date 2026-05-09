"""Audit log helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .redaction import SENSITIVE_KEYS, redact_sensitive


def append_audit_event(path: Path, event: dict[str, Any]) -> None:
    """Append one redacted audit event to HAclaw managed JSONL storage."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        **redact_sensitive(event),
    }
    with path.open("a", encoding="utf-8") as audit_file:
        audit_file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _redact(value: Any) -> Any:
    return redact_sensitive(value)
