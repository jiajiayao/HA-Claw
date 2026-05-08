"""Tests for HAclaw environment readiness + install_prompt rendering."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.haclaw.tools.environment import (
    INSTALL_PROMPT_TEMPLATES,
    INTEGRATION_METADATA,
    detect_environment_readiness,
    render_install_prompt,
)


def _make_hass(*, has_xiaomi: bool, device_trackers: int, install_type: str = "OS") -> MagicMock:
    hass = MagicMock()
    states = [MagicMock(entity_id=f"device_tracker.dev{i}") for i in range(device_trackers)]
    hass.states.async_all.return_value = states
    hass.config_entries.async_entries.return_value = [MagicMock()] if has_xiaomi else []
    hass.config.path = lambda *parts: "/" + "/".join(("config",) + parts)
    hass.config.config_source = install_type
    return hass


def test_detect_all_failing() -> None:
    hass = _make_hass(has_xiaomi=False, device_trackers=0)
    result = detect_environment_readiness(hass, dismissed=False, provider_ok=False)
    assert result["failing_required_count"] == 3
    assert all(item["ok"] is False for item in result["items"])


def test_detect_partial_pass() -> None:
    hass = _make_hass(has_xiaomi=True, device_trackers=2)
    result = detect_environment_readiness(hass, dismissed=False, provider_ok=True)
    assert result["failing_required_count"] == 0


def test_advanced_includes_hacs() -> None:
    hass = _make_hass(has_xiaomi=False, device_trackers=0)
    result = detect_environment_readiness(hass, dismissed=False, provider_ok=False)
    advanced_ids = [item["id"] for item in result["advanced"]]
    assert "hacs" in advanced_ids


def test_render_install_prompt_replaces_known_keeps_user() -> None:
    hass = _make_hass(has_xiaomi=False, device_trackers=0)
    rendered = render_install_prompt("xiaomi_miot", hass)
    assert rendered is not None
    assert "{{HA_KNOWN: HA_CONFIG_DIR}}" not in rendered["body"]
    assert "/config" in rendered["body"]
    assert "{{TODO_USER: XIAOMI_EMAIL}}" in rendered["body"]
    assert "XIAOMI_EMAIL" in rendered["todo_user_fields"]


def test_render_install_prompt_unknown_returns_none() -> None:
    hass = _make_hass(has_xiaomi=False, device_trackers=0)
    assert render_install_prompt("nonexistent", hass) is None


def test_integration_metadata_known_domains() -> None:
    assert "xiaomi_miot" in INTEGRATION_METADATA
    assert "hacs" in INTEGRATION_METADATA
    assert INTEGRATION_METADATA["xiaomi_miot"]["install_link"].startswith("http")


def test_install_prompt_templates_have_safety_clauses() -> None:
    for body in INSTALL_PROMPT_TEMPLATES.values():
        assert "HA_CONFIG_DIR" in body
        assert "不要" in body
