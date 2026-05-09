"""HAclaw single-turn chat session orchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..const import (
    DEFAULT_CHAT_MAX_TOKENS,
    MAX_HISTORY_CHARS,
    MAX_USER_MESSAGE_CHARS,
    MODE_AUTOMATION,
)
from ..storage import conversations as conv_store
from ..storage.presence import load_binding
from ..storage.redaction import redact_sensitive
from .prompts import build_system_prompt
from .protocol import ProtocolError, parse_assistant_json, validate_for_mode


class ChatSessionError(Exception):
    """Raised on unrecoverable chat session errors after retries."""


_RETRY_SYSTEM_MSG = (
    "上一次模型输出不是合法 JSON 或不在协议类型白名单内,"
    "请只返回符合 HAclaw JSON 协议的对象,不要任何额外文字。"
)


async def run_single_turn(
    *,
    conversations_path: Path,
    ui_state_path: Path,  # noqa: ARG001 - reserved for future signals
    presence_path: Path,
    conversation_id: str,
    user_message: str,
    mode: str,
    provider_client: Any,
    model_name: str,
    max_tokens: int = DEFAULT_CHAT_MAX_TOKENS,
    entity_context: str = "",
    has_controllable_entities: bool = True,
    entity_candidates: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    if not user_message.strip():
        raise ChatSessionError("用户消息不能为空")
    if len(user_message) > MAX_USER_MESSAGE_CHARS:
        raise ChatSessionError(
            f"用户消息长度超过 {MAX_USER_MESSAGE_CHARS} 字符上限"
        )

    me_entity = load_binding(presence_path)
    system_prompt = build_system_prompt(
        mode=mode,
        me_entity_id=me_entity,
        model_name=model_name,
        entity_context=entity_context,
    )

    history = _load_history_messages(conversations_path, conversation_id)
    conv_store.append_message(
        conversations_path, conversation_id,
        {"role": "user", "content": redact_sensitive(user_message)},
    )

    preflight_msg = _preflight_automation_entity_selection(
        user_message=user_message,
        mode=mode,
        history=history,
        has_controllable_entities=has_controllable_entities,
        entity_candidates=entity_candidates or [],
    )
    if preflight_msg is not None:
        conv_store.append_message(
            conversations_path, conversation_id,
            {
                "role": "assistant",
                "type": preflight_msg["type"],
                "content": redact_sensitive(preflight_msg),
            },
        )
        return {
            "conversation_id": conversation_id,
            "assistant_message": preflight_msg,
            "usage": {},
            "model": model_name,
        }

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    try:
        assistant_msg, usage = await _call_with_retry(
            provider_client, messages, mode, max_tokens,
        )
    except ProtocolError as exc:
        raise ChatSessionError(f"模型协议输出无法解析: {exc}") from exc

    conv_store.append_message(
        conversations_path, conversation_id,
        {
            "role": "assistant",
            "type": assistant_msg["type"],
            "content": redact_sensitive(assistant_msg),
        },
    )

    return {
        "conversation_id": conversation_id,
        "assistant_message": assistant_msg,
        "usage": usage,
        "model": model_name,
    }


async def _call_with_retry(
    client: Any,
    messages: list[dict[str, Any]],
    mode: str,
    max_tokens: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    last_error: Exception | None = None
    for _attempt in range(2):
        result = await client.chat_with_usage(messages, max_tokens=max_tokens)
        try:
            parsed = parse_assistant_json(result.content)
            validate_for_mode(parsed, mode)
        except ProtocolError as exc:
            last_error = exc
            messages = list(messages) + [
                {"role": "system", "content": _RETRY_SYSTEM_MSG},
            ]
            continue
        return parsed, dict(result.usage or {})

    assert last_error is not None
    raise last_error


def _load_history_messages(
    path: Path, conversation_id: str
) -> list[dict[str, Any]]:
    conv = conv_store.load_conversation(path, conversation_id)
    if conv is None:
        return []
    out: list[dict[str, Any]] = []
    char_count = 0
    for msg in reversed(conv["messages"]):
        if msg.get("role") == "user":
            entry = {"role": "user", "content": str(msg.get("content", ""))}
        elif msg.get("role") == "assistant":
            payload = msg.get("content")
            if isinstance(payload, dict):
                entry = {"role": "assistant", "content": json.dumps(payload, ensure_ascii=False)}
            else:
                entry = {"role": "assistant", "content": str(payload or "")}
        else:
            continue
        char_count += len(entry["content"])
        if char_count > MAX_HISTORY_CHARS:
            break
        out.append(entry)
    out.reverse()
    return out


def _preflight_automation_entity_selection(
    *,
    user_message: str,
    mode: str,
    history: list[dict[str, Any]],
    has_controllable_entities: bool,
    entity_candidates: list[dict[str, str]],
) -> dict[str, Any] | None:
    if history:
        return None

    if mode != MODE_AUTOMATION or not _looks_like_device_automation_request(
        user_message
    ):
        return None

    if entity_candidates:
        return {
            "type": "clarification",
            "message": "我扫描到这些可能的设备,请选择要用于自动化的那个。",
            "candidates": entity_candidates[:6],
            "allow_free_text": False,
        }

    if not has_controllable_entities:
        return {
            "type": "final_response",
            "message": (
                "我扫描了当前 Home Assistant,没有发现可控制设备实体。"
                "请先在 HA 添加设备或集成;如果你用小米/米家设备,可以通过 "
                "Xiaomi Miot Auto 或 Xiaomi Home 官方集成接入。"
                "添加后我会从设备列表里让你点选,不会要求你手输 entity_id。"
            ),
        }

    return None


def _looks_like_device_automation_request(text: str) -> bool:
    normalized = text.lower()
    device_keywords = (
        "净化器",
        "灯",
        "空调",
        "窗帘",
        "扫地",
        "插座",
        "风扇",
        "purifier",
        "light",
        "climate",
        "vacuum",
    )
    return any(keyword in normalized for keyword in device_keywords)
