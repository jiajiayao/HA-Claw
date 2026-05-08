"""Tests for LLM-safe Home Assistant entity context helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.haclaw.tools.entity import (
    build_entity_context,
    find_entity_candidates,
    list_controllable_entities,
)


def _state(entity_id: str, state: str = "off", name: str | None = None) -> MagicMock:
    state_obj = MagicMock()
    state_obj.entity_id = entity_id
    state_obj.state = state
    state_obj.attributes = {"friendly_name": name} if name else {}
    return state_obj


def _hass(states: list[MagicMock]) -> MagicMock:
    hass = MagicMock()
    hass.states.async_all.return_value = states
    return hass


def test_list_controllable_entities_filters_read_only_sensors() -> None:
    hass = _hass([
        _state("sensor.pm25", "12", "PM2.5"),
        _state("fan.mi_air_purifier", "off", "米家空气净化器"),
        _state("switch.purifier_plug", "on", "净化器插座"),
    ])

    entities = list_controllable_entities(hass)

    assert [entity["entity_id"] for entity in entities] == [
        "fan.mi_air_purifier",
        "switch.purifier_plug",
    ]
    assert entities[0]["label"] == "米家空气净化器"


def test_find_entity_candidates_prefers_purifier_matches() -> None:
    hass = _hass([
        _state("light.living_room", "off", "客厅灯"),
        _state("fan.mi_air_purifier", "off", "米家空气净化器"),
        _state("switch.purifier_plug", "on", "净化器插座"),
    ])

    candidates = find_entity_candidates(hass, "生成晚 7 点开净化器的自动化")

    assert [candidate["id"] for candidate in candidates] == [
        "fan.mi_air_purifier",
        "switch.purifier_plug",
    ]
    assert candidates[0]["label"] == "米家空气净化器"
    assert "fan.mi_air_purifier" in candidates[0]["subtitle"]


def test_build_entity_context_recommends_adding_devices_when_empty() -> None:
    context = build_entity_context(_hass([_state("sensor.pm25", "12", "PM2.5")]))

    assert "没有扫描到可控制设备实体" in context
    assert "小米" in context
    assert "不要要求用户手输 entity_id" in context


def test_build_entity_context_lists_clickable_entity_candidates() -> None:
    context = build_entity_context(
        _hass([_state("fan.mi_air_purifier", "off", "米家空气净化器")])
    )

    assert "当前 HA 可控制设备实体" in context
    assert "fan.mi_air_purifier" in context
    assert "clarification.candidates" in context
    assert "不要要求用户手输 entity_id" in context
