"""Tests for HAclaw conversations.json storage with rotation."""

from __future__ import annotations

from pathlib import Path

from custom_components.haclaw.storage.conversations import (
    append_message,
    clear_all,
    clear_conversation,
    list_conversations,
    load_conversation,
    rotate_if_needed,
)


def test_load_returns_none_when_missing(tmp_path: Path) -> None:
    assert load_conversation(tmp_path / "conv.json", "missing") is None


def test_append_message_creates_conversation(tmp_path: Path) -> None:
    path = tmp_path / "conv.json"
    append_message(path, "c1", {"role": "user", "content": "你好"})
    conv = load_conversation(path, "c1")
    assert conv is not None
    assert conv["messages"][0]["content"] == "你好"
    assert "created_at" in conv
    assert "updated_at" in conv


def test_append_message_caps_per_conversation_at_200(tmp_path: Path) -> None:
    path = tmp_path / "conv.json"
    for i in range(205):
        append_message(path, "c1", {"role": "user", "content": f"msg{i}"})
    conv = load_conversation(path, "c1")
    assert conv is not None
    assert len(conv["messages"]) == 200
    assert conv["messages"][-1]["content"] == "msg204"


def test_rotate_keeps_max_50_conversations(tmp_path: Path) -> None:
    path = tmp_path / "conv.json"
    for i in range(55):
        append_message(path, f"c{i}", {"role": "user", "content": "x"})
    rotate_if_needed(path)
    ids = [c["id"] for c in list_conversations(path)]
    assert len(ids) == 50
    assert "c0" not in ids
    assert "c54" in ids


def test_clear_conversation_empties_messages_keeps_record(tmp_path: Path) -> None:
    path = tmp_path / "conv.json"
    append_message(path, "c1", {"role": "user", "content": "x"})
    clear_conversation(path, "c1")
    conv = load_conversation(path, "c1")
    assert conv is not None
    assert conv["messages"] == []


def test_clear_all_removes_everything(tmp_path: Path) -> None:
    path = tmp_path / "conv.json"
    append_message(path, "c1", {"role": "user", "content": "x"})
    append_message(path, "c2", {"role": "user", "content": "y"})
    clear_all(path)
    assert list_conversations(path) == []


def test_rotate_handles_oversized_file(tmp_path: Path) -> None:
    path = tmp_path / "conv.json"
    big_content = "z" * 1000
    for i in range(8):
        append_message(path, f"c{i}", {"role": "user", "content": big_content * 1000})
    rotate_if_needed(path)
    assert path.stat().st_size < 5 * 1024 * 1024 * 1.5
    assert len(list_conversations(path)) >= 1
