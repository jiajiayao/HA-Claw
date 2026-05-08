"""HAclaw presence entity binding (only stores entity_id, never raw MAC/GPS)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


class BindingError(Exception):
    """Raised when a presence binding request is invalid."""


def load_binding(path: Path) -> str | None:
    """Return the bound entity_id, or None if not bound or unreadable."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    value = raw.get("me_person_entity_id") if isinstance(raw, dict) else None
    return value if isinstance(value, str) and value else None


def save_binding(
    path: Path,
    *,
    entity_id: str,
    entity_exists: Callable[[str], bool],
) -> None:
    """Persist the user-selected presence entity. Validates domain and existence."""
    if not isinstance(entity_id, str) or "." not in entity_id:
        raise BindingError("entity_id 格式不合法")
    domain = entity_id.split(".", 1)[0]
    if domain not in {"person", "device_tracker"}:
        raise BindingError("entity_id 的 domain 必须是 person 或 device_tracker")
    if not entity_exists(entity_id):
        raise BindingError(f"实体 {entity_id} 不存在于 Home Assistant 状态中")

    payload = {
        "me_person_entity_id": entity_id,
        "bound_at": datetime.now(timezone.utc).isoformat(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def list_candidates(hass: Any) -> list[dict[str, str]]:
    """Return person.* (first) and device_tracker.* candidates."""
    persons: list[dict[str, str]] = []
    trackers: list[dict[str, str]] = []
    for state in hass.states.async_all():
        eid = state.entity_id
        domain = eid.split(".", 1)[0]
        if domain not in {"person", "device_tracker"}:
            continue
        friendly = state.attributes.get("friendly_name", eid)
        bucket = persons if domain == "person" else trackers
        bucket.append({
            "id": eid,
            "label": friendly,
            "subtitle": f"{eid} · {state.state}",
        })
    persons.sort(key=lambda c: c["id"])
    trackers.sort(key=lambda c: c["id"])
    return persons + trackers
