"""Draft storage helpers for automations and dashboards."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from custom_components.haclaw.tools.automation import AutomationValidationResult


DRAFT_STORE_VERSION = 1


class DraftStorageError(RuntimeError):
    """Raised when HAclaw managed draft storage cannot be read or written."""


def create_automation_draft_record(
    *,
    title: str,
    description: str,
    validation: AutomationValidationResult,
    source: str = "service",
) -> dict[str, Any]:
    """Build a persistable automation draft record."""
    now = _utc_now()
    return {
        "id": uuid4().hex,
        "type": "automation",
        "title": title.strip(),
        "description": description.strip(),
        "automation": validation.automation,
        "risk_level": validation.risk_level,
        "requires_confirmation": validation.requires_confirmation,
        "approved": False,
        "source": source,
        "created_at": now,
        "updated_at": now,
        "validation": {
            "entity_ids": sorted(validation.entity_ids),
            "service_calls": [service.key for service in validation.service_calls],
            "errors": list(validation.errors),
            "warnings": list(validation.warnings),
        },
    }


def load_draft_store(path: Path) -> dict[str, Any]:
    """Load HAclaw draft storage from JSON."""
    if not path.exists():
        return {"version": DRAFT_STORE_VERSION, "drafts": []}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        raise DraftStorageError("Unable to load HAclaw draft storage.") from err

    if not isinstance(data, dict) or not isinstance(data.get("drafts"), list):
        raise DraftStorageError("HAclaw draft storage has an invalid structure.")

    data.setdefault("version", DRAFT_STORE_VERSION)
    return data


def save_draft_store(path: Path, store: dict[str, Any]) -> None:
    """Persist HAclaw draft storage atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(
        path,
        json.dumps(store, ensure_ascii=False, indent=2) + "\n",
    )


def append_draft(path: Path, draft: dict[str, Any]) -> dict[str, Any]:
    """Append a draft and return it."""
    store = load_draft_store(path)
    store["drafts"].append(draft)
    save_draft_store(path, store)
    return draft


def get_draft(path: Path, draft_id: str) -> dict[str, Any] | None:
    """Return a draft by id."""
    store = load_draft_store(path)
    for draft in store["drafts"]:
        if draft.get("id") == draft_id:
            return draft
    return None


def load_draft_aliases(path: Path) -> set[str]:
    """Load aliases from saved automation drafts."""
    store = load_draft_store(path)
    aliases: set[str] = set()
    for draft in store["drafts"]:
        automation = draft.get("automation")
        if not isinstance(automation, dict):
            continue
        alias = automation.get("alias")
        if isinstance(alias, str) and alias.strip():
            aliases.add(alias.strip())
    return aliases


def mark_draft_approved(path: Path, draft_id: str) -> dict[str, Any]:
    """Mark a draft as approved and persist the change."""
    store = load_draft_store(path)
    for draft in store["drafts"]:
        if draft.get("id") == draft_id:
            draft["approved"] = True
            draft["updated_at"] = _utc_now()
            save_draft_store(path, store)
            return draft
    raise DraftStorageError(f"Draft does not exist: {draft_id}.")


def load_automation_aliases(path: Path) -> set[str]:
    """Load aliases from a HAclaw-managed automations YAML file."""
    automations = _load_automation_list(path)
    return {
        automation["alias"].strip()
        for automation in automations
        if isinstance(automation, dict)
        and isinstance(automation.get("alias"), str)
        and automation["alias"].strip()
    }


def append_automation(path: Path, automation: dict[str, Any]) -> None:
    """Append an automation to HAclaw-managed automations YAML."""
    automations = _load_automation_list(path)
    automations.append(dict(automation))
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(
        path,
        yaml.safe_dump(automations, allow_unicode=True, sort_keys=False),
    )


def _load_automation_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as err:
        raise DraftStorageError("Unable to load HAclaw automations YAML.") from err

    if data is None:
        return []
    if not isinstance(data, list):
        raise DraftStorageError("HAclaw automations YAML must contain a list.")
    return data


def _atomic_write_text(path: Path, content: str) -> None:
    tmp_path = path.with_name(f".{path.name}.tmp")
    try:
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(path)
    except OSError as err:
        raise DraftStorageError(f"Unable to write {path.name}.") from err


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
