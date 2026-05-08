"""HAclaw conversations.json storage with FIFO + size rotation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..const import (
    MAX_CONVERSATIONS,
    MAX_CONVERSATIONS_FILE_BYTES,
    MAX_MESSAGES_PER_CONVERSATION,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"conversations": []}
    if not isinstance(raw, dict) or not isinstance(raw.get("conversations"), list):
        return {"conversations": []}
    return raw


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_conversations(path: Path) -> list[dict[str, Any]]:
    return _read(path)["conversations"]


def load_conversation(path: Path, conversation_id: str) -> dict[str, Any] | None:
    for conv in _read(path)["conversations"]:
        if conv.get("id") == conversation_id:
            return conv
    return None


def append_message(
    path: Path, conversation_id: str, message: dict[str, Any]
) -> dict[str, Any]:
    data = _read(path)
    convs = data["conversations"]
    target = next((c for c in convs if c.get("id") == conversation_id), None)
    if target is None:
        target = {
            "id": conversation_id,
            "created_at": _now(),
            "updated_at": _now(),
            "messages": [],
        }
        convs.append(target)

    msg = dict(message)
    msg.setdefault("ts", _now())
    target["messages"].append(msg)
    target["updated_at"] = _now()

    if len(target["messages"]) > MAX_MESSAGES_PER_CONVERSATION:
        target["messages"] = target["messages"][-MAX_MESSAGES_PER_CONVERSATION:]

    _write(path, data)
    rotate_if_needed(path)
    return target


def clear_conversation(path: Path, conversation_id: str) -> None:
    data = _read(path)
    for conv in data["conversations"]:
        if conv.get("id") == conversation_id:
            conv["messages"] = []
            conv["updated_at"] = _now()
            break
    _write(path, data)


def clear_all(path: Path) -> None:
    _write(path, {"conversations": []})


def rotate_if_needed(path: Path) -> None:
    """FIFO drop oldest conversations until count + size budgets are met."""
    data = _read(path)
    convs = data["conversations"]
    if len(convs) > MAX_CONVERSATIONS:
        convs[:] = convs[-MAX_CONVERSATIONS:]
        _write(path, data)

    if not path.exists():
        return
    while path.stat().st_size > MAX_CONVERSATIONS_FILE_BYTES and len(convs) > 1:
        drop_n = max(1, len(convs) // 4)
        convs[:] = convs[drop_n:]
        _write(path, data)
