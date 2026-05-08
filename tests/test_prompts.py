"""Tests for HAclaw system prompt assembly."""

from __future__ import annotations

import pytest

from custom_components.haclaw.agent.prompts import build_system_prompt
from custom_components.haclaw.const import (
    MODE_AUTOMATION,
    MODE_EXECUTE,
    MODE_PLAN,
)


def test_plan_mode_contains_plan_suffix() -> None:
    prompt = build_system_prompt(mode=MODE_PLAN, me_entity_id=None, model_name="m")
    assert "计划模式" in prompt
    assert "automation_draft" in prompt
    assert "只能" in prompt


def test_automation_mode_contains_chip_first_rules() -> None:
    prompt = build_system_prompt(
        mode=MODE_AUTOMATION, me_entity_id="person.j", model_name="m"
    )
    assert "自动化模式" in prompt
    assert "rationale" in prompt
    assert "allow_free_text" in prompt
    assert "1-6" in prompt
    assert "2-6" not in prompt
    assert "workday" in prompt


def test_execute_mode_marks_experimental() -> None:
    prompt = build_system_prompt(mode=MODE_EXECUTE, me_entity_id=None, model_name="m")
    assert "执行模式" in prompt
    assert "实验中" in prompt or "v1.x" in prompt


def test_unbound_presence_includes_bind_marker_instruction() -> None:
    prompt = build_system_prompt(mode=MODE_AUTOMATION, me_entity_id=None, model_name="m")
    assert "[BIND_PRESENCE]" in prompt
    assert "未绑定" in prompt


def test_bound_presence_shows_entity_in_context() -> None:
    prompt = build_system_prompt(
        mode=MODE_AUTOMATION, me_entity_id="person.jiajia", model_name="m"
    )
    assert "person.jiajia" in prompt


def test_invalid_mode_raises() -> None:
    with pytest.raises(ValueError):
        build_system_prompt(mode="garbage", me_entity_id=None, model_name="m")
