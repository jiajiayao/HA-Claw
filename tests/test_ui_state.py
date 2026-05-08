"""Tests for HAclaw ui_state.json storage."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.haclaw.storage.ui_state import (
    DEFAULT_UI_STATE,
    load_state,
    update_state,
)


def test_load_state_returns_defaults_when_file_missing(tmp_path: Path) -> None:
    state = load_state(tmp_path / "ui_state.json")
    assert state == DEFAULT_UI_STATE


def test_load_state_reads_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "ui_state.json"
    path.write_text(json.dumps({"last_mode": "plan"}), encoding="utf-8")
    state = load_state(path)
    assert state["last_mode"] == "plan"
    assert state["env_check_dismissed"] is False


def test_load_state_falls_back_when_last_mode_invalid(tmp_path: Path) -> None:
    path = tmp_path / "ui_state.json"
    path.write_text(json.dumps({"last_mode": "garbage"}), encoding="utf-8")
    state = load_state(path)
    assert state["last_mode"] == "automation"


def test_update_state_merges_and_persists(tmp_path: Path) -> None:
    path = tmp_path / "ui_state.json"
    update_state(path, last_mode="plan")
    update_state(path, env_check_dismissed=True)
    state = load_state(path)
    assert state["last_mode"] == "plan"
    assert state["env_check_dismissed"] is True


def test_load_state_handles_corrupt_file(tmp_path: Path) -> None:
    path = tmp_path / "ui_state.json"
    path.write_text("{not json", encoding="utf-8")
    state = load_state(path)
    assert state == DEFAULT_UI_STATE
