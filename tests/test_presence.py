"""Tests for HAclaw presence binding storage."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from custom_components.haclaw.storage.presence import (
    BindingError,
    list_candidates,
    load_binding,
    save_binding,
)


def test_load_binding_returns_none_when_missing(tmp_path: Path) -> None:
    assert load_binding(tmp_path / "presence.json") is None


def test_save_binding_rejects_unknown_domain(tmp_path: Path) -> None:
    with pytest.raises(BindingError, match="domain"):
        save_binding(
            tmp_path / "presence.json",
            entity_id="light.kitchen",
            entity_exists=lambda eid: True,
        )


def test_save_binding_rejects_missing_entity(tmp_path: Path) -> None:
    with pytest.raises(BindingError, match="不存在"):
        save_binding(
            tmp_path / "presence.json",
            entity_id="person.ghost",
            entity_exists=lambda eid: False,
        )


def test_save_binding_persists_entity_and_timestamp(tmp_path: Path) -> None:
    path = tmp_path / "presence.json"
    save_binding(path, entity_id="person.jiajia", entity_exists=lambda eid: True)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["me_person_entity_id"] == "person.jiajia"
    assert "bound_at" in saved


def test_load_binding_after_save(tmp_path: Path) -> None:
    path = tmp_path / "presence.json"
    save_binding(path, entity_id="device_tracker.phone", entity_exists=lambda eid: True)
    binding = load_binding(path)
    assert binding == "device_tracker.phone"


def test_list_candidates_orders_persons_first() -> None:
    state_a = MagicMock(entity_id="device_tracker.phone", state="home")
    state_a.attributes = {"friendly_name": "Phone"}
    state_b = MagicMock(entity_id="person.jiajia", state="not_home")
    state_b.attributes = {"friendly_name": "Jiajia"}
    state_c = MagicMock(entity_id="light.kitchen", state="on")
    state_c.attributes = {"friendly_name": "Kitchen"}

    hass = MagicMock()
    hass.states.async_all.return_value = [state_a, state_b, state_c]

    candidates = list_candidates(hass)
    assert [c["id"] for c in candidates] == [
        "person.jiajia",
        "device_tracker.phone",
    ]
    assert candidates[0]["label"] == "Jiajia"
    assert candidates[0]["subtitle"].startswith("person.jiajia")
