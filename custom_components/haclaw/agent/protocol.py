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
