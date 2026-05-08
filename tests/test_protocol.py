"""Tests for HAclaw assistant message protocol parser."""

from __future__ import annotations

import pytest

from custom_components.haclaw.agent.protocol import (
    ALLOWED_TYPES_BY_MODE,
    ProtocolError,
    migrate_clarification,
    parse_assistant_json,
    validate_for_mode,
)
from custom_components.haclaw.const import (
    MODE_AUTOMATION,
    MODE_EXECUTE,
    MODE_PLAN,
)


def test_parse_final_response() -> None:
    msg = parse_assistant_json('{"type":"final_response","message":"hi"}')
    assert msg["type"] == "final_response"


def test_parse_invalid_json_raises() -> None:
    with pytest.raises(ProtocolError, match="JSON"):
        parse_assistant_json("{not json")


def test_parse_missing_type_raises() -> None:
    with pytest.raises(ProtocolError, match="type"):
        parse_assistant_json('{"message":"x"}')


def test_parse_unknown_type_raises() -> None:
    with pytest.raises(ProtocolError):
        parse_assistant_json('{"type":"weird"}')


def test_validate_plan_allows_final_response() -> None:
    validate_for_mode({"type": "final_response", "message": "ok"}, MODE_PLAN)


def test_validate_plan_rejects_automation_draft() -> None:
    msg = {
        "type": "automation_draft",
        "title": "x",
        "automation": {"alias": "x"},
        "rationale": {
            "entities": [], "trigger": "", "conditions": [],
            "actions": [], "edge_cases": "",
        },
    }
    with pytest.raises(ProtocolError, match="plan"):
        validate_for_mode(msg, MODE_PLAN)


def test_validate_automation_rejects_tool_call() -> None:
    with pytest.raises(ProtocolError, match="automation"):
        validate_for_mode({"type": "tool_call", "tool": "t", "args": {}}, MODE_AUTOMATION)


def test_validate_execute_allows_all() -> None:
    validate_for_mode({"type": "tool_call", "tool": "t", "args": {}}, MODE_EXECUTE)


def test_clarification_migration_from_legacy() -> None:
    legacy = {
        "type": "clarification",
        "message": "?",
        "candidates": [
            {"entity_id": "light.a", "name": "灯 A"},
            {"entity_id": "light.b", "name": "灯 B"},
        ],
    }
    out = migrate_clarification(legacy)
    assert out["candidates"][0]["id"] == "light.a"
    assert out["candidates"][0]["label"] == "灯 A"
    assert out["candidates"][0]["subtitle"] == "light.a"
    assert out["allow_free_text"] is False


def test_clarification_allows_single_candidate_confirmation() -> None:
    msg = {
        "type": "clarification",
        "message": "只找到一个灯,是否使用它?",
        "candidates": [{"id": "light.living_room", "label": "客厅灯"}],
    }
    validate_for_mode(msg, MODE_AUTOMATION)


def test_clarification_allows_free_text_without_candidates() -> None:
    msg = {
        "type": "clarification",
        "message": "每天晚上几点开灯?",
        "allow_free_text": True,
        "free_text_placeholder": "例如 19:30",
    }
    validate_for_mode(msg, MODE_AUTOMATION)


def test_clarification_rejects_unanswerable_prompt() -> None:
    msg = {
        "type": "clarification",
        "message": "每天晚上几点开灯?",
        "candidates": [],
    }
    with pytest.raises(ProtocolError, match="candidates|allow_free_text"):
        validate_for_mode(msg, MODE_AUTOMATION)


def test_automation_draft_missing_rationale_fails() -> None:
    msg = {"type": "automation_draft", "title": "x", "automation": {"alias": "x"}}
    with pytest.raises(ProtocolError, match="rationale"):
        validate_for_mode(msg, MODE_AUTOMATION)


def test_allowed_types_by_mode_constants() -> None:
    assert ALLOWED_TYPES_BY_MODE[MODE_PLAN] == {"final_response", "clarification"}
    assert "automation_draft" in ALLOWED_TYPES_BY_MODE[MODE_AUTOMATION]
    assert "tool_call" in ALLOWED_TYPES_BY_MODE[MODE_EXECUTE]
