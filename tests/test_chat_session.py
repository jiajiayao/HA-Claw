"""Tests for HAclaw single-turn chat session."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.haclaw.agent.chat_session import (
    ChatSessionError,
    run_single_turn,
)
from custom_components.haclaw.const import MODE_AUTOMATION, MODE_PLAN


def _make_provider(responses: list[str]) -> MagicMock:
    iterator = iter(responses)
    client = MagicMock()
    async def chat_with_usage(messages, **_):  # noqa: ANN001
        nxt = next(iterator)
        result = MagicMock()
        result.content = nxt
        result.usage = {"prompt_tokens": 10, "completion_tokens": 5}
        return result
    client.chat_with_usage = AsyncMock(side_effect=chat_with_usage)
    return client


@pytest.mark.asyncio
async def test_run_single_turn_returns_parsed_message(tmp_path: Path) -> None:
    storage = tmp_path / "conv.json"
    provider = _make_provider(['{"type":"final_response","message":"hi"}'])
    result = await run_single_turn(
        conversations_path=storage,
        ui_state_path=tmp_path / "ui.json",
        presence_path=tmp_path / "presence.json",
        conversation_id="c1",
        user_message="hi",
        mode=MODE_AUTOMATION,
        provider_client=provider,
        model_name="mimo",
    )
    assert result["assistant_message"]["type"] == "final_response"
    saved = json.loads(storage.read_text(encoding="utf-8"))
    msgs = saved["conversations"][0]["messages"]
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_run_single_turn_retries_on_protocol_error(tmp_path: Path) -> None:
    provider = _make_provider([
        "not json",
        '{"type":"final_response","message":"recovered"}',
    ])
    result = await run_single_turn(
        conversations_path=tmp_path / "conv.json",
        ui_state_path=tmp_path / "ui.json",
        presence_path=tmp_path / "presence.json",
        conversation_id="c1",
        user_message="hi",
        mode=MODE_AUTOMATION,
        provider_client=provider,
        model_name="mimo",
    )
    assert result["assistant_message"]["type"] == "final_response"
    assert provider.chat_with_usage.await_count == 2


@pytest.mark.asyncio
async def test_run_single_turn_two_failures_raises(tmp_path: Path) -> None:
    provider = _make_provider(["garbage", "still garbage"])
    with pytest.raises(ChatSessionError):
        await run_single_turn(
            conversations_path=tmp_path / "conv.json",
            ui_state_path=tmp_path / "ui.json",
            presence_path=tmp_path / "presence.json",
            conversation_id="c1",
            user_message="hi",
            mode=MODE_AUTOMATION,
            provider_client=provider,
            model_name="mimo",
        )


@pytest.mark.asyncio
async def test_mode_violation_triggers_retry(tmp_path: Path) -> None:
    draft = json.dumps({
        "type": "automation_draft", "title": "x",
        "automation": {"alias": "x"},
        "rationale": {
            "entities": [], "trigger": "", "conditions": [],
            "actions": [], "edge_cases": "",
        },
    })
    provider = _make_provider([
        draft,
        '{"type":"final_response","message":"converted to text"}',
    ])
    result = await run_single_turn(
        conversations_path=tmp_path / "conv.json",
        ui_state_path=tmp_path / "ui.json",
        presence_path=tmp_path / "presence.json",
        conversation_id="c1",
        user_message="hi",
        mode=MODE_PLAN,
        provider_client=provider,
        model_name="mimo",
    )
    assert result["assistant_message"]["type"] == "final_response"
    assert provider.chat_with_usage.await_count == 2


@pytest.mark.asyncio
async def test_user_message_too_long_raises(tmp_path: Path) -> None:
    provider = _make_provider([])
    with pytest.raises(ChatSessionError, match="长度"):
        await run_single_turn(
            conversations_path=tmp_path / "conv.json",
            ui_state_path=tmp_path / "ui.json",
            presence_path=tmp_path / "presence.json",
            conversation_id="c1",
            user_message="x" * 5000,
            mode=MODE_AUTOMATION,
            provider_client=provider,
            model_name="mimo",
        )
