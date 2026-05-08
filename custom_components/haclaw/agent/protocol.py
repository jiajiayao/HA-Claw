"""Strict model response protocol validation for HAclaw."""

from __future__ import annotations

import json
from typing import Any


SUPPORTED_TYPES = {
    "final_response",
    "tool_call",
    "automation_draft",
    "clarification",
    "risk_confirmation",
}
RISK_LEVELS = {"low", "medium", "high", "critical"}


class ProtocolError(ValueError):
    """Raised when model output does not match the HAclaw protocol."""


def parse_agent_response(
    raw_response: str,
    *,
    allowed_tools: set[str] | None = None,
) -> dict[str, Any]:
    """Parse and validate a JSON-only model response."""
    payload = _load_json_only(raw_response)
    if not isinstance(payload, dict):
        raise ProtocolError("Model response must be a JSON object.")

    response_type = payload.get("type")
    if response_type not in SUPPORTED_TYPES:
        raise ProtocolError(f"Unsupported response type: {response_type!r}.")

    if response_type == "final_response":
        _require_string(payload, "message")
    elif response_type == "tool_call":
        _validate_tool_call(payload, allowed_tools)
    elif response_type == "automation_draft":
        _validate_automation_draft(payload)
    elif response_type == "clarification":
        _validate_clarification(payload)
    elif response_type == "risk_confirmation":
        _validate_risk_confirmation(payload)

    return payload


def _load_json_only(raw_response: str) -> Any:
    decoder = json.JSONDecoder()
    text = raw_response.strip()
    if not text:
        raise ProtocolError("Model response is empty.")

    try:
        payload, offset = decoder.raw_decode(text)
    except json.JSONDecodeError as err:
        raise ProtocolError(f"Model response is not valid JSON: {err.msg}.") from err

    if text[offset:].strip():
        raise ProtocolError("Model response contains prose outside JSON.")
    return payload


def _validate_tool_call(
    payload: dict[str, Any],
    allowed_tools: set[str] | None,
) -> None:
    tool = _require_string(payload, "tool")
    args = payload.get("args")
    if args is None:
        payload["args"] = {}
    elif not isinstance(args, dict):
        raise ProtocolError("tool_call.args must be an object.")

    if allowed_tools is not None and tool not in allowed_tools:
        raise ProtocolError(f"Unknown or unavailable tool: {tool}.")


def _validate_automation_draft(payload: dict[str, Any]) -> None:
    _require_string(payload, "title")
    _require_string(payload, "description")

    automation = payload.get("automation")
    if not isinstance(automation, dict):
        raise ProtocolError("automation_draft.automation must be an object.")

    _require_string(automation, "alias")
    if "trigger" not in automation:
        raise ProtocolError("automation_draft.automation.trigger is required.")
    if "action" not in automation:
        raise ProtocolError("automation_draft.automation.action is required.")
    if not isinstance(automation["trigger"], (list, dict)):
        raise ProtocolError("automation trigger must be a list or object.")
    if not isinstance(automation["action"], (list, dict)):
        raise ProtocolError("automation action must be a list or object.")

    risk_level = payload.get("risk_level")
    if risk_level not in RISK_LEVELS:
        raise ProtocolError("automation_draft.risk_level is invalid.")
    if not isinstance(payload.get("requires_confirmation"), bool):
        raise ProtocolError("automation_draft.requires_confirmation must be boolean.")


def _validate_clarification(payload: dict[str, Any]) -> None:
    _require_string(payload, "message")
    candidates = payload.get("candidates")
    if candidates is not None and not isinstance(candidates, list):
        raise ProtocolError("clarification.candidates must be a list when present.")


def _validate_risk_confirmation(payload: dict[str, Any]) -> None:
    _require_string(payload, "message")
    if payload.get("risk_level") not in RISK_LEVELS:
        raise ProtocolError("risk_confirmation.risk_level is invalid.")
    if not isinstance(payload.get("planned_action"), dict):
        raise ProtocolError("risk_confirmation.planned_action must be an object.")


def _require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProtocolError(f"{key} must be a non-empty string.")
    return value


# Range B chat UI protocol additions (mode-aware parser + migration).
# See spec §7.5, §7.6, §7.7.

from ..const import MODE_AUTOMATION, MODE_EXECUTE, MODE_PLAN  # noqa: E402

PROTOCOL_TYPES = SUPPORTED_TYPES

ALLOWED_TYPES_BY_MODE: dict[str, set[str]] = {
    MODE_PLAN: {"final_response", "clarification"},
    MODE_AUTOMATION: {"final_response", "clarification", "automation_draft"},
    MODE_EXECUTE: {
        "final_response",
        "clarification",
        "automation_draft",
        "risk_confirmation",
        "tool_call",
    },
}


def parse_assistant_json(raw: str) -> dict[str, Any]:
    """Parse a model JSON response and apply clarification migration.

    Lighter than parse_agent_response: no per-type validation here;
    callers pair this with validate_for_mode().
    """
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"模型输出不是合法 JSON: {exc.msg}") from exc
    if not isinstance(obj, dict):
        raise ProtocolError("模型输出 JSON 必须是对象")
    if "type" not in obj:
        raise ProtocolError("模型输出缺少 type 字段")
    if obj["type"] not in PROTOCOL_TYPES:
        raise ProtocolError(f"模型输出 type 不在 whitelist 内: {obj['type']!r}")
    if obj["type"] == "clarification":
        obj = migrate_clarification(obj)
    return obj


def migrate_clarification(msg: dict[str, Any]) -> dict[str, Any]:
    """Migrate legacy {entity_id, name} candidates to {id, label, subtitle}."""
    candidates = msg.get("candidates")
    if not isinstance(candidates, list):
        return msg
    migrated = []
    for cand in candidates:
        if not isinstance(cand, dict):
            continue
        if "id" in cand and "label" in cand:
            migrated.append(cand)
            continue
        eid = cand.get("entity_id")
        name = cand.get("name", eid)
        if eid:
            migrated.append({"id": eid, "label": name, "subtitle": eid})
    msg = dict(msg)
    msg["candidates"] = migrated
    msg.setdefault("allow_free_text", False)
    return msg


def validate_for_mode(msg: dict[str, Any], mode: str) -> None:
    """Validate that the assistant message type is allowed in the given mode.

    Also performs schema checks specific to range-B types (answerable
    clarification, automation_draft.rationale required).
    """
    msg_type = msg.get("type")
    allowed = ALLOWED_TYPES_BY_MODE.get(mode, set())
    if msg_type not in allowed:
        raise ProtocolError(f"模式 {mode} 不允许 type={msg_type!r}")

    if msg_type == "clarification":
        cands = msg.get("candidates", [])
        if not isinstance(cands, list):
            raise ProtocolError("clarification.candidates 必须是数组")
        if not cands and msg.get("allow_free_text") is not True:
            raise ProtocolError(
                "clarification 需要 candidates 或 allow_free_text=true"
            )
        for c in cands:
            if not isinstance(c, dict) or "id" not in c or "label" not in c:
                raise ProtocolError("clarification candidate 必须含 id 和 label")

    if msg_type == "automation_draft":
        if "rationale" not in msg or not isinstance(msg["rationale"], dict):
            raise ProtocolError("automation_draft 缺少 rationale 字段")
        required = {"entities", "trigger", "conditions", "actions", "edge_cases"}
        missing = required - set(msg["rationale"].keys())
        if missing:
            raise ProtocolError(
                f"automation_draft.rationale 缺少字段: {sorted(missing)}"
            )
