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
async def test_run_single_turn_recommends_adding_devices_when_none_exist(
    tmp_path: Path,
) -> None:
    storage = tmp_path / "conv.json"
    provider = _make_provider([])
    result = await run_single_turn(
        conversations_path=storage,
        ui_state_path=tmp_path / "ui.json",
        presence_path=tmp_path / "presence.json",
        conversation_id="c1",
        user_message="生成晚 7 点开净化器的自动化",
        mode=MODE_AUTOMATION,
        provider_client=provider,
        model_name="mimo",
        entity_context="当前没有扫描到可控制设备实体。",
        has_controllable_entities=False,
    )

    assert result["assistant_message"]["type"] == "final_response"
    assert "没有发现可控制设备" in result["assistant_message"]["message"]
    assert "小米" in result["assistant_message"]["message"]
    provider.chat_with_usage.assert_not_awaited()
    saved = json.loads(storage.read_text(encoding="utf-8"))
    assert saved["conversations"][0]["messages"][1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_run_single_turn_returns_device_picker_for_matching_entities(
    tmp_path: Path,
) -> None:
    provider = _make_provider([])
    result = await run_single_turn(
        conversations_path=tmp_path / "conv.json",
        ui_state_path=tmp_path / "ui.json",
        presence_path=tmp_path / "presence.json",
        conversation_id="c1",
        user_message="生成晚 7 点开净化器的自动化",
        mode=MODE_AUTOMATION,
        provider_client=provider,
        model_name="mimo",
        entity_context="当前 HA 可控制设备实体: fan.mi_air_purifier",
        has_controllable_entities=True,
        entity_candidates=[
            {
                "id": "fan.mi_air_purifier",
                "label": "米家空气净化器",
                "subtitle": "fan.mi_air_purifier · fan · off",
            }
        ],
    )

    assert result["assistant_message"] == {
        "type": "clarification",
        "message": "我扫描到这些可能的设备,请选择要用于自动化的那个。",
        "candidates": [
            {
                "id": "fan.mi_air_purifier",
                "label": "米家空气净化器",
                "subtitle": "fan.mi_air_purifier · fan · off",
            }
        ],
        "allow_free_text": False,
    }
    provider.chat_with_usage.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_single_turn_does_not_preflight_non_device_automation(
    tmp_path: Path,
) -> None:
    provider = _make_provider(['{"type":"final_response","message":"ok"}'])
    result = await run_single_turn(
        conversations_path=tmp_path / "conv.json",
        ui_state_path=tmp_path / "ui.json",
        presence_path=tmp_path / "presence.json",
        conversation_id="c1",
        user_message="每天晚上 7 点提醒我喝水",
        mode=MODE_AUTOMATION,
        provider_client=provider,
        model_name="mimo",
        entity_context="当前没有扫描到可控制设备实体。",
        has_controllable_entities=False,
    )

    assert result["assistant_message"] == {"type": "final_response", "message": "ok"}
    provider.chat_with_usage.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_single_turn_includes_entity_context_in_system_prompt(
    tmp_path: Path,
) -> None:
    provider = _make_provider(['{"type":"final_response","message":"ok"}'])
    await run_single_turn(
        conversations_path=tmp_path / "conv.json",
        ui_state_path=tmp_path / "ui.json",
        presence_path=tmp_path / "presence.json",
        conversation_id="c1",
        user_message="hi",
        mode=MODE_AUTOMATION,
        provider_client=provider,
        model_name="mimo",
        entity_context="当前 HA 可控制设备实体: fan.mi_air_purifier",
        has_controllable_entities=True,
    )

    messages = provider.chat_with_usage.await_args.args[0]
    assert "fan.mi_air_purifier" in messages[0]["content"]
    assert "不要要求用户手输 entity_id" in messages[0]["content"]


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
