# HAclaw Chat UI v1.0 (Range B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the form-based `haclaw-panel.js` with a Claude Desktop Lite chat-first UI, driven by a new minimal `haclaw/chat` WebSocket command, supporting three modes (plan/automation/execute), asking-answer flow with chip-first UX, install_prompt cross-agent collaboration templates, and onboarding (env check + presence binding).

**Architecture:** Backend gains an `agent/` package (prompts / protocol / chat_session) and 3 storage modules (conversations / presence / ui_state) plus a `tools/environment.py`. Existing `tools/automation.py` extends with `missing_integrations`. A new WS command `haclaw/chat` orchestrates mode-aware LLM calls, JSON-protocol filtering, and conversation persistence. The frontend is rewritten as a chat-first single-file web component using HA's existing `_hass.connection` for both WS commands and service calls. Strict safety boundary: HAclaw never installs, never collects credentials, never executes tools (in B scope).

**Tech Stack:** Python 3.14 + Home Assistant 2025.x (`pytest`, `pytest-homeassistant-custom-component`, `voluptuous`); JavaScript (vanilla web component, no build step, ES2022).

**Spec reference:** `docs/superpowers/specs/2026-05-08-haclaw-chat-ui-design.md`

---

## File structure

### New (backend)

| File | Responsibility |
|------|---------------|
| `custom_components/haclaw/agent/__init__.py` | package marker (empty) |
| `custom_components/haclaw/agent/prompts.py` | `BASE_SYSTEM_PROMPT` + 3 `MODE_SUFFIX_*` + `build_system_prompt(mode, ctx)` |
| `custom_components/haclaw/agent/protocol.py` | `parse_assistant_json`, `ALLOWED_TYPES_BY_MODE`, clarification schema migration, `validate_for_mode` (rationale check) |
| `custom_components/haclaw/agent/chat_session.py` | `run_single_turn(...)` |
| `custom_components/haclaw/storage/conversations.py` | `load_conversation`, `append_message`, `clear_conversation`, `clear_all`, rotation |
| `custom_components/haclaw/storage/presence.py` | `load_binding`, `save_binding`, `list_candidates(hass)` |
| `custom_components/haclaw/storage/ui_state.py` | `load_state`, `update_state(**fields)` |
| `custom_components/haclaw/tools/environment.py` | env detection (3 required + advanced) + `INSTALL_PROMPT_TEMPLATES` + `render_install_prompt` |

### New (tests)

`tests/test_prompts.py`, `tests/test_protocol.py`, `tests/test_chat_session.py`, `tests/test_environment.py`, `tests/test_presence.py`, `tests/test_conversations_storage.py`, `tests/test_ui_state.py`.

### Modify (backend)

- `custom_components/haclaw/__init__.py` — register WS commands, register new services
- `custom_components/haclaw/services.yaml` — declare new services
- `custom_components/haclaw/const.py` — add storage filename + service-name constants
- `custom_components/haclaw/tools/automation.py` — add `missing_integrations` to `ValidationResult`
- `tests/test_automation.py` — cases for `missing_integrations`
- `tests/test_integration_services.py` — cases for new services + WS commands

### Modify (frontend)

- `custom_components/haclaw/frontend/haclaw-panel.js` — full rewrite (incremental tasks)

---

## Frontend safety pattern (used throughout Phase 5)

**Existing codebase pattern**: `haclaw-panel.js` already uses `this.innerHTML = template-string` plus a `_escape(value)` helper for interpolated values. Phase 5 follows this established pattern — **all user/model strings MUST go through `_escape()` before interpolation**. Static template literals (e.g., labels, class names) are safe. To make this explicit and reduce per-call risk, Phase 5 introduces a tagged template helper `_html(strings, ...values)` that auto-escapes every interpolated value, so engineers can't forget to escape:

```javascript
// Defined in the panel class
_html(strings, ...values) {
  let out = strings[0];
  for (let i = 0; i < values.length; i++) {
    out += this._escape(values[i]) + strings[i + 1];
  }
  return out;
}
```

When a step says "render an HTML fragment", use ``this._html`...`` for any fragment that contains a `${userValue}` interpolation. For pure-static fragments (no `${}`), regular template literals are fine. **Never use raw `innerHTML = unsafe_string`.**

---

## Phase 1 — Constants & storage foundation

### Task 1: Add storage and service constants

**Files:** Modify `custom_components/haclaw/const.py`

- [ ] **Step 1: Append constants to `const.py`**

```python
# New storage files (range B)
CONVERSATIONS_FILE = "conversations.json"
PRESENCE_FILE = "presence.json"
UI_STATE_FILE = "ui_state.json"

# New service names (range B)
SERVICE_GET_ENVIRONMENT_READINESS = "get_environment_readiness"
SERVICE_LIST_PRESENCE_CANDIDATES = "list_presence_candidates"
SERVICE_GET_PRESENCE_BINDING = "get_presence_binding"
SERVICE_BIND_PRESENCE_ENTITY = "bind_presence_entity"
SERVICE_SWITCH_MODEL = "switch_model"

# New WS commands
WS_TYPE_CHAT = "haclaw/chat"
WS_TYPE_CONVERSATIONS_LIST = "haclaw/conversations/list"
WS_TYPE_CONVERSATIONS_CLEAR = "haclaw/conversations/clear"

# Chat session limits
MAX_USER_MESSAGE_CHARS = 4000
MAX_HISTORY_CHARS = 8000
DEFAULT_CHAT_MAX_TOKENS = 1024
MAX_CONVERSATIONS = 50
MAX_MESSAGES_PER_CONVERSATION = 200
MAX_CONVERSATIONS_FILE_BYTES = 5 * 1024 * 1024

# Modes
MODE_PLAN = "plan"
MODE_AUTOMATION = "automation"
MODE_EXECUTE = "execute"
ALL_MODES = (MODE_PLAN, MODE_AUTOMATION, MODE_EXECUTE)
DEFAULT_MODE = MODE_AUTOMATION
```

- [ ] **Step 2: Commit**

```bash
git add custom_components/haclaw/const.py
git commit -m "feat: add chat UI constants for storage, services, modes"
```

---

### Task 2: `storage/ui_state.py`

**Files:**
- Create: `custom_components/haclaw/storage/ui_state.py`
- Create: `tests/test_ui_state.py`

- [ ] **Step 1: Write failing tests** in `tests/test_ui_state.py`:

```python
"""Tests for HAclaw ui_state.json storage."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.haclaw.storage.ui_state import (
    DEFAULT_UI_STATE,
    load_state,
    update_state,
)


def test_load_state_returns_defaults_when_file_missing(tmp_path: Path) -> None:
    state = load_state(tmp_path / "ui_state.json")
    assert state == DEFAULT_UI_STATE


def test_load_state_reads_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "ui_state.json"
    path.write_text(json.dumps({"last_mode": "plan"}), encoding="utf-8")
    state = load_state(path)
    assert state["last_mode"] == "plan"
    assert state["env_check_dismissed"] is False


def test_load_state_falls_back_when_last_mode_invalid(tmp_path: Path) -> None:
    path = tmp_path / "ui_state.json"
    path.write_text(json.dumps({"last_mode": "garbage"}), encoding="utf-8")
    state = load_state(path)
    assert state["last_mode"] == "automation"


def test_update_state_merges_and_persists(tmp_path: Path) -> None:
    path = tmp_path / "ui_state.json"
    update_state(path, last_mode="plan")
    update_state(path, env_check_dismissed=True)
    state = load_state(path)
    assert state["last_mode"] == "plan"
    assert state["env_check_dismissed"] is True


def test_load_state_handles_corrupt_file(tmp_path: Path) -> None:
    path = tmp_path / "ui_state.json"
    path.write_text("{not json", encoding="utf-8")
    state = load_state(path)
    assert state == DEFAULT_UI_STATE
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_ui_state.py -v
```

Expected: ImportError on `storage.ui_state`.

- [ ] **Step 3: Implement `custom_components/haclaw/storage/ui_state.py`**

```python
"""HAclaw UI state file (last_mode, env_check_dismissed, etc.)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..const import ALL_MODES, DEFAULT_MODE

DEFAULT_UI_STATE: dict[str, Any] = {
    "env_check_dismissed": False,
    "execute_mode_warning_seen": False,
    "last_mode": DEFAULT_MODE,
    "last_conversation_id": None,
}


def load_state(path: Path) -> dict[str, Any]:
    """Load UI state from disk, falling back to defaults on any error."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return dict(DEFAULT_UI_STATE)

    state = dict(DEFAULT_UI_STATE)
    if isinstance(raw, dict):
        for key in DEFAULT_UI_STATE:
            if key in raw:
                state[key] = raw[key]

    if state["last_mode"] not in ALL_MODES:
        state["last_mode"] = DEFAULT_MODE
    return state


def update_state(path: Path, **fields: Any) -> dict[str, Any]:
    """Merge fields into the on-disk state and return the new state."""
    state = load_state(path)
    state.update(fields)
    if state["last_mode"] not in ALL_MODES:
        state["last_mode"] = DEFAULT_MODE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_ui_state.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add custom_components/haclaw/storage/ui_state.py tests/test_ui_state.py
git commit -m "feat: add ui_state.json storage with mode/dismissal persistence"
```

---

### Task 3: `storage/presence.py`

**Files:**
- Create: `custom_components/haclaw/storage/presence.py`
- Create: `tests/test_presence.py`

- [ ] **Step 1: Write failing tests** in `tests/test_presence.py`:

```python
"""Tests for HAclaw presence binding storage."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from custom_components.haclaw.storage.presence import (
    BindingError,
    list_candidates,
    load_binding,
    save_binding,
)


def test_load_binding_returns_none_when_missing(tmp_path: Path) -> None:
    assert load_binding(tmp_path / "presence.json") is None


def test_save_binding_rejects_unknown_domain(tmp_path: Path) -> None:
    with pytest.raises(BindingError, match="domain"):
        save_binding(
            tmp_path / "presence.json",
            entity_id="light.kitchen",
            entity_exists=lambda eid: True,
        )


def test_save_binding_rejects_missing_entity(tmp_path: Path) -> None:
    with pytest.raises(BindingError, match="不存在"):
        save_binding(
            tmp_path / "presence.json",
            entity_id="person.ghost",
            entity_exists=lambda eid: False,
        )


def test_save_binding_persists_entity_and_timestamp(tmp_path: Path) -> None:
    path = tmp_path / "presence.json"
    save_binding(path, entity_id="person.jiajia", entity_exists=lambda eid: True)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["me_person_entity_id"] == "person.jiajia"
    assert "bound_at" in saved


def test_load_binding_after_save(tmp_path: Path) -> None:
    path = tmp_path / "presence.json"
    save_binding(path, entity_id="device_tracker.phone", entity_exists=lambda eid: True)
    binding = load_binding(path)
    assert binding == "device_tracker.phone"


def test_list_candidates_orders_persons_first() -> None:
    state_a = MagicMock(entity_id="device_tracker.phone", state="home")
    state_a.attributes = {"friendly_name": "Phone"}
    state_b = MagicMock(entity_id="person.jiajia", state="not_home")
    state_b.attributes = {"friendly_name": "Jiajia"}
    state_c = MagicMock(entity_id="light.kitchen", state="on")
    state_c.attributes = {"friendly_name": "Kitchen"}

    hass = MagicMock()
    hass.states.async_all.return_value = [state_a, state_b, state_c]

    candidates = list_candidates(hass)
    assert [c["id"] for c in candidates] == [
        "person.jiajia",
        "device_tracker.phone",
    ]
    assert candidates[0]["label"] == "Jiajia"
    assert candidates[0]["subtitle"].startswith("person.jiajia")
```

- [ ] **Step 2: Confirm failing**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_presence.py -v
```

- [ ] **Step 3: Implement `custom_components/haclaw/storage/presence.py`**

```python
"""HAclaw presence entity binding (only stores entity_id, never raw MAC/GPS)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


class BindingError(Exception):
    """Raised when a presence binding request is invalid."""


def load_binding(path: Path) -> str | None:
    """Return the bound entity_id, or None if not bound or unreadable."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    value = raw.get("me_person_entity_id") if isinstance(raw, dict) else None
    return value if isinstance(value, str) and value else None


def save_binding(
    path: Path,
    *,
    entity_id: str,
    entity_exists: Callable[[str], bool],
) -> None:
    """Persist the user-selected presence entity. Validates domain and existence."""
    if not isinstance(entity_id, str) or "." not in entity_id:
        raise BindingError("entity_id 格式不合法")
    domain = entity_id.split(".", 1)[0]
    if domain not in {"person", "device_tracker"}:
        raise BindingError("entity_id 的 domain 必须是 person 或 device_tracker")
    if not entity_exists(entity_id):
        raise BindingError(f"实体 {entity_id} 不存在于 Home Assistant 状态中")

    payload = {
        "me_person_entity_id": entity_id,
        "bound_at": datetime.now(timezone.utc).isoformat(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def list_candidates(hass: Any) -> list[dict[str, str]]:
    """Return person.* (first) and device_tracker.* candidates."""
    persons: list[dict[str, str]] = []
    trackers: list[dict[str, str]] = []
    for state in hass.states.async_all():
        eid = state.entity_id
        domain = eid.split(".", 1)[0]
        if domain not in {"person", "device_tracker"}:
            continue
        friendly = state.attributes.get("friendly_name", eid)
        bucket = persons if domain == "person" else trackers
        bucket.append({
            "id": eid,
            "label": friendly,
            "subtitle": f"{eid} · {state.state}",
        })
    persons.sort(key=lambda c: c["id"])
    trackers.sort(key=lambda c: c["id"])
    return persons + trackers
```

- [ ] **Step 4: Confirm pass**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_presence.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add custom_components/haclaw/storage/presence.py tests/test_presence.py
git commit -m "feat: add presence entity binding storage (entity_id only, no MAC/GPS)"
```

---

### Task 4: `storage/conversations.py`

**Files:**
- Create: `custom_components/haclaw/storage/conversations.py`
- Create: `tests/test_conversations_storage.py`

- [ ] **Step 1: Write failing tests** in `tests/test_conversations_storage.py`:

```python
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
```

- [ ] **Step 2: Confirm failing**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_conversations_storage.py -v
```

- [ ] **Step 3: Implement `custom_components/haclaw/storage/conversations.py`**

```python
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
```

- [ ] **Step 4: Confirm pass**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_conversations_storage.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add custom_components/haclaw/storage/conversations.py tests/test_conversations_storage.py
git commit -m "feat: add conversations.json storage with FIFO + size rotation"
```

---

## Phase 2 — Agent core (prompts / protocol / chat session)

### Task 5: `agent/prompts.py`

**Files:**
- Create: `custom_components/haclaw/agent/__init__.py`
- Create: `custom_components/haclaw/agent/prompts.py`
- Create: `tests/test_prompts.py`

- [ ] **Step 1: Write failing tests** in `tests/test_prompts.py`:

```python
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
```

- [ ] **Step 2: Confirm failing**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_prompts.py -v
```

- [ ] **Step 3: Create empty `agent/__init__.py`**

```python
"""HAclaw agent package: prompts, protocol, chat session."""
```

- [ ] **Step 4: Implement `agent/prompts.py`**

```python
"""HAclaw system prompt assembly. See spec §7.3."""

from __future__ import annotations

from ..const import ALL_MODES, MODE_AUTOMATION, MODE_EXECUTE, MODE_PLAN

BASE_SYSTEM_PROMPT = """\
你是 HAclaw,Home Assistant 的中文 AI 助手。
严格遵守:
- 只输出合法 JSON,不要在 JSON 外混入 Markdown 或解释文字
- 协议类型白名单(具体允许哪些由当前模式决定): final_response / clarification / automation_draft / risk_confirmation / tool_call
- 用中文回复
- 不要编造实体 ID
- 高风险操作(开锁、撤防、重启 HA、shell)必须用 risk_confirmation 类型
- 不要请求用户提供 API key、token、密码、MAC、GPS 坐标

当前已知用户上下文:
- 绑定的存在实体: {me_status}
- 当前模型: {model_name}

特殊指令:
- 如果"绑定的存在实体"为"未绑定",并且用户的请求涉及到家/离家/在家时/不在家时类自动化,请返回 final_response 类型,且 message 字段必须包含字符串 "[BIND_PRESENCE]"(放在中文说明的开头);前端会据此插入绑定向导卡片。其他场景下严禁使用此 marker。
"""

MODE_SUFFIX_PLAN = """\
当前模式:📋 计划模式。
- 你**只能**返回 final_response 或 clarification 两种类型
- 即使用户要求"生成自动化",也只用 final_response 描述你建议的自动化思路,不要返回 automation_draft
- 即使用户要求"打开/关闭设备",也只用 final_response 描述步骤,不要返回 tool_call
- 这是用户用来想清楚需求的模式,不要执行任何动作
"""

MODE_SUFFIX_AUTOMATION = """\
当前模式:⚡ 自动化模式。

【核心原则:先问清楚,再生成】
不要直接返回 automation_draft,除非以下维度都已经从对话里明确:
  1. 实体: 哪个 entity_id(必须真实存在于 hass.states,不要编造)
  2. 触发: 类型(time/state/numeric_state/存在感应/设备事件)+ 精确参数
  3. 条件: 是否需要附加 condition(用户没说默认就是没有,不要自作主张加上)
  4. 动作参数: 灯亮度、空调温度、扫地机房间等
  5. 边缘情况: 设备离线?多次触发去重?— 这一项可在 rationale 里说"未问及,默认 X"

【提问规则】
- 缺信息时优先用 clarification 类型问
- candidates 必须 2-6 项
- 一次只问一个最关键的维度
- 最多 4 轮 clarification,4 轮后用合理默认值生成 draft + rationale 标注"假设了 X"

【何时设 allow_free_text=true(必须设的场景)】
- 时间相关(用户可能要"19:30")
- 日期/节假日(中国节假日不能简单二分)
- 数值阈值
- 自动化命名 / 设备别名
- 用户在之前轮次已经给出非 preset 答案

【关于节假日 / 工作日】
- HA 自带 workday 集成支持中国大陆节假日
- 用户提到"节假日 / 法定假 / 春节 / 国庆"时:
  - 已有 workday config_entry → 直接在 condition 里引用 binary_sensor.workday
  - 没有 → clarification 问 [是,加上 workday] [先用工作日近似] [我自己后面装]

【生成 draft 之前的最后一步】
信息够了时,先返回 final_response 给一句简明摘要(< 60 字)让用户校对。
用户回"嗯"/"是"/"对"/"OK"/"好的"/"行"/"可以"/"开始吧"/"go"等正面词,下一轮再返回 automation_draft。

【automation_draft 必须包含 rationale 字段】
rationale: { entities, trigger, conditions, actions, edge_cases } 每项记录来自对话哪一轮的回答。

【绝不要做的事】
- 不要编造实体 ID
- 不要假设默认值不告知用户
- 不要一次问 5 个以上问题
- 不要返回 tool_call(本期没工具执行)
"""

MODE_SUFFIX_EXECUTE = """\
当前模式:🛠 执行模式(实验中,工具执行层 v1.x 才上线)。
- 允许返回 tool_call 提议设备控制 — 但用户已知本期 tool_call 只展示不执行
- 高风险操作(开锁、撤防、重启 HA、shell_command.*、xiaomi_miot.get_token)必须用 risk_confirmation
- 允许其他全部协议类型
- tool_call 的 args 字段要给出完整、可执行的实体 ID 和参数
"""


_MODE_SUFFIXES = {
    MODE_PLAN: MODE_SUFFIX_PLAN,
    MODE_AUTOMATION: MODE_SUFFIX_AUTOMATION,
    MODE_EXECUTE: MODE_SUFFIX_EXECUTE,
}


def build_system_prompt(
    *,
    mode: str,
    me_entity_id: str | None,
    model_name: str,
) -> str:
    if mode not in ALL_MODES:
        raise ValueError(f"unknown mode: {mode}")
    me_status = me_entity_id or "未绑定"
    base = BASE_SYSTEM_PROMPT.format(me_status=me_status, model_name=model_name)
    return base + "\n\n" + _MODE_SUFFIXES[mode]
```

- [ ] **Step 5: Confirm pass**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_prompts.py -v
```

Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add custom_components/haclaw/agent/__init__.py custom_components/haclaw/agent/prompts.py tests/test_prompts.py
git commit -m "feat: HAclaw system prompt builder with 3 mode suffixes"
```

---

### Task 6: `agent/protocol.py`

**Files:**
- Create: `custom_components/haclaw/agent/protocol.py`
- Create: `tests/test_protocol.py`

- [ ] **Step 1: Write failing tests** in `tests/test_protocol.py`:

```python
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


def test_clarification_rejects_too_few_candidates() -> None:
    msg = {
        "type": "clarification",
        "message": "?",
        "candidates": [{"id": "x", "label": "x"}],
    }
    with pytest.raises(ProtocolError, match="2"):
        validate_for_mode(msg, MODE_AUTOMATION)


def test_automation_draft_missing_rationale_fails() -> None:
    msg = {"type": "automation_draft", "title": "x", "automation": {"alias": "x"}}
    with pytest.raises(ProtocolError, match="rationale"):
        validate_for_mode(msg, MODE_AUTOMATION)


def test_allowed_types_by_mode_constants() -> None:
    assert ALLOWED_TYPES_BY_MODE[MODE_PLAN] == {"final_response", "clarification"}
    assert "automation_draft" in ALLOWED_TYPES_BY_MODE[MODE_AUTOMATION]
    assert "tool_call" in ALLOWED_TYPES_BY_MODE[MODE_EXECUTE]
```

- [ ] **Step 2: Confirm failing**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_protocol.py -v
```

- [ ] **Step 3: Implement `agent/protocol.py`**

```python
"""HAclaw assistant message JSON protocol parser + per-mode validator."""

from __future__ import annotations

import json
from typing import Any

from ..const import MODE_AUTOMATION, MODE_EXECUTE, MODE_PLAN


class ProtocolError(Exception):
    """Raised when the model output violates the HAclaw JSON protocol."""


PROTOCOL_TYPES = {
    "final_response",
    "clarification",
    "automation_draft",
    "risk_confirmation",
    "tool_call",
}

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
    msg_type = msg.get("type")
    allowed = ALLOWED_TYPES_BY_MODE.get(mode, set())
    if msg_type not in allowed:
        raise ProtocolError(f"模式 {mode} 不允许 type={msg_type!r}")

    if msg_type == "clarification":
        cands = msg.get("candidates", [])
        if not isinstance(cands, list) or len(cands) < 2:
            raise ProtocolError("clarification 至少需要 2 个 candidates")
        for c in cands:
            if not isinstance(c, dict) or "id" not in c or "label" not in c:
                raise ProtocolError("clarification candidate 必须含 id 和 label")

    if msg_type == "automation_draft":
        if "rationale" not in msg or not isinstance(msg["rationale"], dict):
            raise ProtocolError("automation_draft 缺少 rationale 字段")
        required = {"entities", "trigger", "conditions", "actions", "edge_cases"}
        missing = required - set(msg["rationale"].keys())
        if missing:
            raise ProtocolError(f"automation_draft.rationale 缺少字段: {sorted(missing)}")
```

- [ ] **Step 4: Confirm pass**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_protocol.py -v
```

Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add custom_components/haclaw/agent/protocol.py tests/test_protocol.py
git commit -m "feat: HAclaw JSON protocol parser with per-mode allowed types"
```

---

### Task 7: `agent/chat_session.py`

**Files:**
- Create: `custom_components/haclaw/agent/chat_session.py`
- Create: `tests/test_chat_session.py`

- [ ] **Step 1: Write failing tests** in `tests/test_chat_session.py`:

```python
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
```

- [ ] **Step 2: Confirm failing**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_chat_session.py -v
```

- [ ] **Step 3: Implement `agent/chat_session.py`**

```python
"""HAclaw single-turn chat session orchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..const import (
    DEFAULT_CHAT_MAX_TOKENS,
    MAX_HISTORY_CHARS,
    MAX_USER_MESSAGE_CHARS,
)
from ..storage import conversations as conv_store
from ..storage.presence import load_binding
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
) -> dict[str, Any]:
    if not user_message.strip():
        raise ChatSessionError("用户消息不能为空")
    if len(user_message) > MAX_USER_MESSAGE_CHARS:
        raise ChatSessionError(
            f"用户消息长度超过 {MAX_USER_MESSAGE_CHARS} 字符上限"
        )

    me_entity = load_binding(presence_path)
    system_prompt = build_system_prompt(
        mode=mode, me_entity_id=me_entity, model_name=model_name,
    )

    history = _load_history_messages(conversations_path, conversation_id)
    conv_store.append_message(
        conversations_path, conversation_id,
        {"role": "user", "content": user_message},
    )

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
        {"role": "assistant", "type": assistant_msg["type"], "content": assistant_msg},
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
```

- [ ] **Step 4: Confirm pass**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_chat_session.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add custom_components/haclaw/agent/chat_session.py tests/test_chat_session.py
git commit -m "feat: HAclaw single-turn chat session with protocol retry"
```

---

## Phase 3 — Tools

### Task 8: `tools/environment.py`

**Files:**
- Create: `custom_components/haclaw/tools/environment.py`
- Create: `tests/test_environment.py`

- [ ] **Step 1: Write failing tests** in `tests/test_environment.py`:

```python
"""Tests for HAclaw environment readiness + install_prompt rendering."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.haclaw.tools.environment import (
    INSTALL_PROMPT_TEMPLATES,
    INTEGRATION_METADATA,
    detect_environment_readiness,
    render_install_prompt,
)


def _make_hass(*, has_xiaomi: bool, device_trackers: int, install_type: str = "OS") -> MagicMock:
    hass = MagicMock()
    states = [MagicMock(entity_id=f"device_tracker.dev{i}") for i in range(device_trackers)]
    hass.states.async_all.return_value = states
    hass.config_entries.async_entries.return_value = [MagicMock()] if has_xiaomi else []
    hass.config.path = lambda *parts: "/" + "/".join(("config",) + parts)
    hass.config.config_source = install_type
    return hass


def test_detect_all_failing() -> None:
    hass = _make_hass(has_xiaomi=False, device_trackers=0)
    result = detect_environment_readiness(hass, dismissed=False, provider_ok=False)
    assert result["failing_required_count"] == 3
    assert all(item["ok"] is False for item in result["items"])


def test_detect_partial_pass() -> None:
    hass = _make_hass(has_xiaomi=True, device_trackers=2)
    result = detect_environment_readiness(hass, dismissed=False, provider_ok=True)
    assert result["failing_required_count"] == 0


def test_advanced_includes_hacs() -> None:
    hass = _make_hass(has_xiaomi=False, device_trackers=0)
    result = detect_environment_readiness(hass, dismissed=False, provider_ok=False)
    advanced_ids = [item["id"] for item in result["advanced"]]
    assert "hacs" in advanced_ids


def test_render_install_prompt_replaces_known_keeps_user() -> None:
    hass = _make_hass(has_xiaomi=False, device_trackers=0)
    rendered = render_install_prompt("xiaomi_miot", hass)
    assert rendered is not None
    assert "{{HA_KNOWN: HA_CONFIG_DIR}}" not in rendered["body"]
    assert "/config" in rendered["body"]
    assert "{{TODO_USER: XIAOMI_EMAIL}}" in rendered["body"]
    assert "XIAOMI_EMAIL" in rendered["todo_user_fields"]


def test_render_install_prompt_unknown_returns_none() -> None:
    hass = _make_hass(has_xiaomi=False, device_trackers=0)
    assert render_install_prompt("nonexistent", hass) is None


def test_integration_metadata_known_domains() -> None:
    assert "xiaomi_miot" in INTEGRATION_METADATA
    assert "hacs" in INTEGRATION_METADATA
    assert INTEGRATION_METADATA["xiaomi_miot"]["install_link"].startswith("http")


def test_install_prompt_templates_have_safety_clauses() -> None:
    for body in INSTALL_PROMPT_TEMPLATES.values():
        assert "HA_CONFIG_DIR" in body
        assert "不要" in body
```

- [ ] **Step 2: Confirm failing**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_environment.py -v
```

- [ ] **Step 3: Implement `tools/environment.py`**

```python
"""HAclaw environment readiness check + install_prompt template rendering."""

from __future__ import annotations

import re
from typing import Any

INTEGRATION_METADATA: dict[str, dict[str, str]] = {
    "xiaomi_miot": {
        "integration_name": "Xiaomi Miot Auto",
        "install_link": "https://github.com/al-one/hass-xiaomi-miot",
    },
    "hacs": {
        "integration_name": "HACS",
        "install_link": "https://hacs.xyz/",
    },
    "mobile_app": {
        "integration_name": "HA Companion App",
        "install_link": "https://companion.home-assistant.io/",
    },
    "xiaomi_miio": {
        "integration_name": "Xiaomi Miio (legacy)",
        "install_link": "https://www.home-assistant.io/integrations/xiaomi_miio/",
    },
}


INSTALL_PROMPT_TEMPLATES: dict[str, str] = {
    "hacs": """\
帮我在 Home Assistant 上安装 HACS。

环境(HAclaw 已探测):
- HA 配置目录: {{HA_KNOWN: HA_CONFIG_DIR}}
- HA 部署类型: {{HA_KNOWN: HA_INSTALL_TYPE}}

要求:
1. 用 HACS 官方安装方式 https://hacs.xyz/docs/setup/download
2. {{TODO_AGENT: 安装完成后告诉我下一步要做什么}}
3. **不要**把任何 token / 密码写入任何文件或 commit 到 git
4. 不要绕过 HA 自身的认证流程,不要直接修改 .storage
""",
    "xiaomi_miot": """\
帮我在 Home Assistant 上安装 Xiaomi Miot Auto(通过 HACS)。

环境(HAclaw 已探测):
- HA 配置目录: {{HA_KNOWN: HA_CONFIG_DIR}}
- HA 部署类型: {{HA_KNOWN: HA_INSTALL_TYPE}}
- 前提: HACS 已安装

凭据(运行时由我给你,不要写文件):
- 小米账号邮箱: {{TODO_USER: XIAOMI_EMAIL}}
- 小米账号密码: {{TODO_USER: XIAOMI_PASSWORD}}

要求:
1. HACS 添加自定义仓库 https://github.com/al-one/hass-xiaomi-miot
2. HACS 安装 Xiaomi Miot Auto
3. 重启 HA
4. 引导我在 HA UI 添加 Xiaomi Miot 集成,我在那里输入凭据
5. **绝不要**把上面凭据写到任何文件或 commit
6. {{TODO_AGENT: 完成后告诉我装好的设备数量}}
""",
}


_TODO_USER_RE = re.compile(r"\{\{TODO_USER:\s*([A-Z_][A-Z0-9_]*)\s*\}\}")
_HA_KNOWN_RE = re.compile(r"\{\{HA_KNOWN:\s*([A-Z_][A-Z0-9_]*)\s*\}\}")


def _detect_install_type(config_source: Any) -> str:
    src = str(config_source or "").lower()
    if "os" in src or "supervised" in src:
        return "HA OS / Supervised"
    if "container" in src or "docker" in src:
        return "Container"
    return "Core / Unknown"


def render_install_prompt(domain: str, hass: Any) -> dict[str, Any] | None:
    template = INSTALL_PROMPT_TEMPLATES.get(domain)
    if template is None:
        return None
    meta = INTEGRATION_METADATA.get(domain, {})
    title = "安装 " + meta.get("integration_name", domain)

    known_values = {
        "HA_CONFIG_DIR": hass.config.path(),
        "HA_INSTALL_TYPE": _detect_install_type(getattr(hass.config, "config_source", "")),
    }
    body = _HA_KNOWN_RE.sub(
        lambda m: known_values.get(m.group(1), m.group(0)),
        template,
    )
    todo_user_fields = sorted(set(_TODO_USER_RE.findall(body)))
    return {"title": title, "body": body, "todo_user_fields": todo_user_fields}


def detect_environment_readiness(
    hass: Any,
    *,
    dismissed: bool,
    provider_ok: bool,
) -> dict[str, Any]:
    items = []
    items.append({
        "id": "provider",
        "label": "Provider 连通",
        "ok": provider_ok,
        "hint": None if provider_ok else "Provider 还没接通",
        "links": [{"text": "HAclaw 集成", "url": "/config/integrations/integration/haclaw"}] if not provider_ok else [],
        "install_prompt": None,
    })

    has_tracker = any(
        s.entity_id.startswith("device_tracker.") for s in hass.states.async_all()
    )
    items.append({
        "id": "device_tracker",
        "label": "蓝牙/WiFi 存在感应",
        "ok": has_tracker,
        "hint": None if has_tracker else "找不到任何 device_tracker 实体",
        "links": [
            {"text": "Companion App", "url": INTEGRATION_METADATA["mobile_app"]["install_link"]},
            {"text": "蓝牙追踪", "url": "https://www.home-assistant.io/integrations/bluetooth_le_tracker/"},
        ] if not has_tracker else [],
        "install_prompt": None,
    })

    xiaomi_ok = bool(hass.config_entries.async_entries("xiaomi_miot"))
    items.append({
        "id": "xiaomi_miot",
        "label": "Xiaomi Home",
        "ok": xiaomi_ok,
        "hint": None if xiaomi_ok else "没装 Xiaomi Miot Auto",
        "links": [{"text": "Xiaomi Miot Auto", "url": INTEGRATION_METADATA["xiaomi_miot"]["install_link"]}] if not xiaomi_ok else [],
        "install_prompt": None if xiaomi_ok else render_install_prompt("xiaomi_miot", hass),
    })

    advanced = []
    hacs_ok = bool(hass.config_entries.async_entries("hacs"))
    advanced.append({
        "id": "hacs",
        "label": "HACS",
        "ok": hacs_ok,
        "hint": None if hacs_ok else "门槛较高,通常通过 shell 命令安装",
        "links": [{"text": "HACS 官方", "url": INTEGRATION_METADATA["hacs"]["install_link"]}] if not hacs_ok else [],
        "install_prompt": None if hacs_ok else render_install_prompt("hacs", hass),
    })

    failing_required_count = sum(1 for it in items if not it["ok"])

    return {
        "items": items,
        "advanced": advanced,
        "dismissed": dismissed,
        "failing_required_count": failing_required_count,
    }
```

- [ ] **Step 4: Confirm pass**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_environment.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add custom_components/haclaw/tools/environment.py tests/test_environment.py
git commit -m "feat: env readiness detection + install_prompt cross-agent templates"
```

---

### Task 9: `tools/automation.py` — `missing_integrations`

**Files:**
- Modify: `custom_components/haclaw/tools/automation.py`
- Modify: `tests/test_automation.py`

- [ ] **Step 1: Inspect existing automation.py**

```bash
grep -n "ValidationResult\|missing_integrations" custom_components/haclaw/tools/automation.py
```

You'll see a `ValidationResult` dataclass and `validate_automation_draft` function.

- [ ] **Step 2: Append failing tests** to `tests/test_automation.py` (top imports may need updating to include `validate_automation_draft`):

```python
def test_validate_reports_missing_integration_for_xiaomi_miot() -> None:
    automation = {
        "alias": "test xiaomi miot",
        "trigger": [{"platform": "time", "at": "19:00"}],
        "action": [
            {"service": "xiaomi_miot.set_property",
             "target": {"entity_id": "fan.purifier"}}
        ],
    }
    result = validate_automation_draft(
        automation,
        known_entity_ids={"fan.purifier"},
        service_exists=lambda dom, svc: False,
        existing_aliases=set(),
    )
    miss = [m for m in result.missing_integrations if m["domain"] == "xiaomi_miot"]
    assert len(miss) == 1
    assert miss[0]["integration_name"] == "Xiaomi Miot Auto"
    assert miss[0]["install_link"].startswith("http")


def test_validate_unknown_domain_falls_back() -> None:
    automation = {
        "alias": "weird",
        "trigger": [{"platform": "time", "at": "19:00"}],
        "action": [{"service": "frobozz.bar", "target": {}}],
    }
    result = validate_automation_draft(
        automation,
        known_entity_ids=set(),
        service_exists=lambda dom, svc: False,
        existing_aliases=set(),
    )
    miss = next(m for m in result.missing_integrations if m["domain"] == "frobozz")
    assert miss["integration_name"] == "frobozz"
    assert miss["install_link"] is None


def test_validate_no_missing_when_all_services_exist() -> None:
    automation = {
        "alias": "all good",
        "trigger": [{"platform": "time", "at": "19:00"}],
        "action": [{"service": "light.turn_on", "target": {"entity_id": "light.x"}}],
    }
    result = validate_automation_draft(
        automation,
        known_entity_ids={"light.x"},
        service_exists=lambda dom, svc: True,
        existing_aliases=set(),
    )
    assert result.missing_integrations == []
```

- [ ] **Step 3: Confirm failing**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_automation.py -v -k "missing_integration or fall_back"
```

- [ ] **Step 4: Modify `custom_components/haclaw/tools/automation.py`**

At the top, add the import:

```python
from .environment import INTEGRATION_METADATA
```

In the `ValidationResult` dataclass, add the new field with a default:

```python
@dataclass
class ValidationResult:
    valid: bool
    automation: dict
    errors: list[str]
    warnings: list[str]
    risk_level: str
    requires_confirmation: bool
    missing_integrations: list[dict] = field(default_factory=list)
```

(If `field` is not imported from `dataclasses`, add `from dataclasses import dataclass, field`.)

In `validate_automation_draft`, after the existing actions loop and before constructing the return value, scan domains:

```python
seen_domains: set[str] = set()
missing_integrations: list[dict] = []
for action in (automation.get("action") or []):
    if not isinstance(action, dict):
        continue
    service = action.get("service")
    if not isinstance(service, str) or "." not in service:
        continue
    domain, _ = service.split(".", 1)
    if domain in seen_domains:
        continue
    seen_domains.add(domain)
    if service_exists(domain, service):
        continue
    meta = INTEGRATION_METADATA.get(domain, {})
    missing_integrations.append({
        "domain": domain,
        "service": service,
        "integration_name": meta.get("integration_name", domain),
        "install_link": meta.get("install_link"),
        "reason": f"草稿用到了 {service} 服务但未检测到这个集成",
    })
```

In the `return ValidationResult(...)` constructor call, add `missing_integrations=missing_integrations`.

- [ ] **Step 5: Confirm pass**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_automation.py -v
```

Expected: existing tests still pass + 3 new tests pass.

- [ ] **Step 6: Commit**

```bash
git add custom_components/haclaw/tools/automation.py tests/test_automation.py
git commit -m "feat: validate_automation_draft surfaces missing_integrations"
```

---

## Phase 4 — Backend services & WebSocket commands

### Task 10: Presence binding services

**Files:**
- Modify: `custom_components/haclaw/__init__.py`
- Modify: `custom_components/haclaw/services.yaml`
- Modify: `tests/test_integration_services.py`

- [ ] **Step 1: Append service declarations to `services.yaml`**

```yaml
list_presence_candidates:
  name: List presence candidates
  description: Return person.* and device_tracker.* entities for the binding card.
  fields: {}

get_presence_binding:
  name: Get presence binding
  description: Return the currently bound presence entity_id, or null.
  fields: {}

bind_presence_entity:
  name: Bind presence entity
  description: Persist the user-selected presence entity_id.
  fields:
    entity_id:
      name: Entity ID
      description: Must start with person. or device_tracker.
      required: true
      selector:
        text:
```

- [ ] **Step 2: Add presence handlers + registrations to `__init__.py`**

Imports at top (add to existing imports):

```python
from .const import (
    PRESENCE_FILE,
    SERVICE_BIND_PRESENCE_ENTITY,
    SERVICE_GET_PRESENCE_BINDING,
    SERVICE_LIST_PRESENCE_CANDIDATES,
)
from .storage.presence import (
    BindingError,
    list_candidates,
    load_binding,
    save_binding,
)
```

Schemas (near other schemas):

```python
LIST_PRESENCE_CANDIDATES_SCHEMA = vol.Schema({})
GET_PRESENCE_BINDING_SCHEMA = vol.Schema({})
BIND_PRESENCE_ENTITY_SCHEMA = vol.Schema({vol.Required("entity_id"): cv.string})
```

Handlers:

```python
async def _async_handle_list_presence_candidates(call: ServiceCall) -> dict[str, Any]:
    return {"candidates": list_candidates(call.hass)}


async def _async_handle_get_presence_binding(call: ServiceCall) -> dict[str, Any]:
    path = _storage_path(call.hass, PRESENCE_FILE)
    binding = await call.hass.async_add_executor_job(load_binding, path)
    return {"me_person_entity_id": binding}


async def _async_handle_bind_presence_entity(call: ServiceCall) -> dict[str, Any]:
    hass = call.hass
    entity_id = call.data["entity_id"]
    path = _storage_path(hass, PRESENCE_FILE)

    def _save() -> None:
        save_binding(
            path,
            entity_id=entity_id,
            entity_exists=lambda eid: hass.states.get(eid) is not None,
        )

    try:
        await hass.async_add_executor_job(_save)
    except BindingError as err:
        return {"success": False, "message": str(err)}

    await _async_append_audit(hass, {
        "tool": SERVICE_BIND_PRESENCE_ENTITY,
        "result": "presence_bound",
        "entity_id": entity_id,
    })
    return {"success": True, "me_person_entity_id": entity_id}
```

Register in `_async_register_services` (mirror existing pattern):

```python
hass.services.async_register(
    DOMAIN, SERVICE_LIST_PRESENCE_CANDIDATES,
    _async_handle_list_presence_candidates,
    schema=LIST_PRESENCE_CANDIDATES_SCHEMA,
    supports_response=SupportsResponse.OPTIONAL,
)
hass.services.async_register(
    DOMAIN, SERVICE_GET_PRESENCE_BINDING,
    _async_handle_get_presence_binding,
    schema=GET_PRESENCE_BINDING_SCHEMA,
    supports_response=SupportsResponse.OPTIONAL,
)
hass.services.async_register(
    DOMAIN, SERVICE_BIND_PRESENCE_ENTITY,
    _async_handle_bind_presence_entity,
    schema=BIND_PRESENCE_ENTITY_SCHEMA,
    supports_response=SupportsResponse.OPTIONAL,
)
```

Add the three service names to the iteration tuple in `_async_remove_services`.

- [ ] **Step 3: Add tests in `tests/test_integration_services.py`**

```python
@pytest.mark.asyncio
async def test_bind_presence_entity_rejects_wrong_domain(hass, configured_entry) -> None:
    response = await hass.services.async_call(
        DOMAIN, "bind_presence_entity",
        {"entity_id": "light.kitchen"},
        blocking=True, return_response=True,
    )
    assert response["success"] is False
    assert "domain" in response["message"]


@pytest.mark.asyncio
async def test_bind_presence_entity_rejects_missing_entity(hass, configured_entry) -> None:
    response = await hass.services.async_call(
        DOMAIN, "bind_presence_entity",
        {"entity_id": "person.ghost"},
        blocking=True, return_response=True,
    )
    assert response["success"] is False


@pytest.mark.asyncio
async def test_bind_persists_and_get_returns(hass, configured_entry) -> None:
    hass.states.async_set("person.jiajia", "home", {"friendly_name": "Jiajia"})
    bind_resp = await hass.services.async_call(
        DOMAIN, "bind_presence_entity",
        {"entity_id": "person.jiajia"},
        blocking=True, return_response=True,
    )
    assert bind_resp["success"] is True

    get_resp = await hass.services.async_call(
        DOMAIN, "get_presence_binding",
        {}, blocking=True, return_response=True,
    )
    assert get_resp["me_person_entity_id"] == "person.jiajia"


@pytest.mark.asyncio
async def test_list_presence_candidates_orders_persons_first(hass, configured_entry) -> None:
    hass.states.async_set("device_tracker.phone", "home", {"friendly_name": "Phone"})
    hass.states.async_set("person.jiajia", "home", {"friendly_name": "Jiajia"})
    response = await hass.services.async_call(
        DOMAIN, "list_presence_candidates",
        {}, blocking=True, return_response=True,
    )
    ids = [c["id"] for c in response["candidates"]]
    assert ids[0] == "person.jiajia"
```

- [ ] **Step 4: Run tests**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_integration_services.py -v -k "presence"
```

- [ ] **Step 5: Commit**

```bash
git add custom_components/haclaw/__init__.py custom_components/haclaw/services.yaml tests/test_integration_services.py
git commit -m "feat: add presence list/get/bind services"
```

---

### Task 11: `get_environment_readiness` service

**Files:**
- Modify: `custom_components/haclaw/__init__.py`
- Modify: `custom_components/haclaw/services.yaml`
- Modify: `tests/test_integration_services.py`

- [ ] **Step 1: Append to `services.yaml`**

```yaml
get_environment_readiness:
  name: Get environment readiness
  description: Detect HACS / Xiaomi / device_tracker readiness for HAclaw onboarding.
  fields: {}
```

- [ ] **Step 2: Implement handler in `__init__.py`**

Imports:

```python
from .const import SERVICE_GET_ENVIRONMENT_READINESS, UI_STATE_FILE
from .storage.ui_state import load_state
from .tools.environment import detect_environment_readiness
```

Schema + handler:

```python
GET_ENVIRONMENT_READINESS_SCHEMA = vol.Schema({})


async def _async_handle_get_environment_readiness(call: ServiceCall) -> dict[str, Any]:
    hass = call.hass
    ui_state = await hass.async_add_executor_job(
        load_state, _storage_path(hass, UI_STATE_FILE),
    )

    provider_ok = False
    try:
        provider = _get_provider_config(hass)
        if provider.get(CONF_API_KEY) and provider.get(CONF_BASE_URL):
            provider_ok = True
    except HomeAssistantError:
        provider_ok = False

    return await hass.async_add_executor_job(
        lambda: detect_environment_readiness(
            hass,
            dismissed=ui_state.get("env_check_dismissed", False),
            provider_ok=provider_ok,
        )
    )
```

Register the service (mirror others) and add to remove iteration tuple.

- [ ] **Step 3: Add test**

```python
@pytest.mark.asyncio
async def test_get_environment_readiness_returns_three_required(
    hass, configured_entry,
) -> None:
    response = await hass.services.async_call(
        DOMAIN, "get_environment_readiness",
        {}, blocking=True, return_response=True,
    )
    ids = [item["id"] for item in response["items"]]
    assert ids == ["provider", "device_tracker", "xiaomi_miot"]
    advanced_ids = [item["id"] for item in response["advanced"]]
    assert "hacs" in advanced_ids
```

- [ ] **Step 4: Run tests**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_integration_services.py -v -k "environment_readiness"
```

- [ ] **Step 5: Commit**

```bash
git add custom_components/haclaw/__init__.py custom_components/haclaw/services.yaml tests/test_integration_services.py
git commit -m "feat: add get_environment_readiness service"
```

---

### Task 12: `switch_model` service

**Files:**
- Modify: `custom_components/haclaw/__init__.py`
- Modify: `custom_components/haclaw/services.yaml`
- Modify: `tests/test_integration_services.py`

- [ ] **Step 1: Append to `services.yaml`**

```yaml
switch_model:
  name: Switch model
  description: Update only the model field on the HAclaw config entry options.
  fields:
    model:
      name: Model
      description: New model identifier.
      required: true
      selector:
        text:
```

- [ ] **Step 2: Handler in `__init__.py`**

```python
from .const import SERVICE_SWITCH_MODEL

SWITCH_MODEL_SCHEMA = vol.Schema({vol.Required("model"): cv.string})


async def _async_handle_switch_model(call: ServiceCall) -> dict[str, Any]:
    hass = call.hass
    new_model = call.data["model"].strip()
    if not new_model:
        return {"success": False, "message": "model 不能为空"}

    entries = _domain_data(hass)["entries"]
    if not entries:
        return {"success": False, "message": "尚未配置 HAclaw entry"}
    entry_state = next(iter(entries.values()))
    entry: ConfigEntry = entry_state["entry"]

    new_options = dict(entry.options)
    new_options[CONF_MODEL] = new_model
    hass.config_entries.async_update_entry(entry, options=new_options)
    entry_state["provider"] = {**dict(entry.data), **new_options}

    return {"success": True, "model": new_model}
```

Register and add to remove tuple.

- [ ] **Step 3: Add test**

```python
@pytest.mark.asyncio
async def test_switch_model_updates_entry_options(hass, configured_entry) -> None:
    response = await hass.services.async_call(
        DOMAIN, "switch_model",
        {"model": "deepseek-coder"},
        blocking=True, return_response=True,
    )
    assert response["success"] is True
    assert configured_entry.options[CONF_MODEL] == "deepseek-coder"


@pytest.mark.asyncio
async def test_switch_model_rejects_empty(hass, configured_entry) -> None:
    response = await hass.services.async_call(
        DOMAIN, "switch_model",
        {"model": "  "},
        blocking=True, return_response=True,
    )
    assert response["success"] is False
```

- [ ] **Step 4: Run tests**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_integration_services.py -v -k "switch_model"
```

- [ ] **Step 5: Commit**

```bash
git add custom_components/haclaw/__init__.py custom_components/haclaw/services.yaml tests/test_integration_services.py
git commit -m "feat: add switch_model service for in-panel model switching"
```

---

### Task 13: `haclaw/chat` WebSocket command

**Files:**
- Modify: `custom_components/haclaw/__init__.py`
- Modify: `tests/test_integration_services.py`

- [ ] **Step 1: Add WS imports**

```python
from homeassistant.components import websocket_api

from .agent.chat_session import ChatSessionError, run_single_turn
from .const import (
    ALL_MODES,
    CONVERSATIONS_FILE,
    DEFAULT_MODE,
    UI_STATE_FILE,
    WS_TYPE_CHAT,
)
```

- [ ] **Step 2: Implement WS handler**

```python
@websocket_api.websocket_command({
    vol.Required("type"): WS_TYPE_CHAT,
    vol.Required("conversation_id"): str,
    vol.Required("user_message"): str,
    vol.Optional("mode", default=DEFAULT_MODE): vol.In(ALL_MODES),
})
@websocket_api.async_response
async def _async_handle_ws_chat(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    try:
        provider = _get_provider_config(hass)
        client = _build_provider_client(provider)
        result = await run_single_turn(
            conversations_path=_storage_path(hass, CONVERSATIONS_FILE),
            ui_state_path=_storage_path(hass, UI_STATE_FILE),
            presence_path=_storage_path(hass, PRESENCE_FILE),
            conversation_id=msg["conversation_id"],
            user_message=msg["user_message"],
            mode=msg["mode"],
            provider_client=client,
            model_name=str(provider.get(CONF_MODEL, "")),
        )
    except ChatSessionError as err:
        connection.send_error(msg["id"], "haclaw_chat_error", str(err))
        return
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "haclaw_config_error", str(err))
        return
    connection.send_result(msg["id"], result)
```

- [ ] **Step 3: Register WS command**

In `_domain_data`'s default dict, add `"ws_registered": False`.

Add new helper `_async_register_ws_commands` (idempotent):

```python
def _async_register_ws_commands(hass: HomeAssistant) -> None:
    domain_data = _domain_data(hass)
    if domain_data.get("ws_registered", False):
        return
    websocket_api.async_register_command(hass, _async_handle_ws_chat)
    domain_data["ws_registered"] = True
```

Call it from `async_setup_entry` after `_async_register_services`:

```python
_async_register_ws_commands(hass)
```

- [ ] **Step 4: Add WS test**

```python
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_ws_chat_returns_final_response(
    hass, configured_entry, hass_ws_client,
) -> None:
    fake = {
        "conversation_id": "c1",
        "assistant_message": {"type": "final_response", "message": "hi"},
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        "model": "mimo",
    }
    with patch(
        "custom_components.haclaw.agent.chat_session.run_single_turn",
        new=AsyncMock(return_value=fake),
    ):
        client = await hass_ws_client(hass)
        await client.send_json({
            "id": 1, "type": "haclaw/chat",
            "conversation_id": "c1", "user_message": "hi", "mode": "automation",
        })
        msg = await client.receive_json()
    assert msg["success"] is True
    assert msg["result"]["assistant_message"]["type"] == "final_response"


@pytest.mark.asyncio
async def test_ws_chat_rejects_invalid_mode(
    hass, configured_entry, hass_ws_client,
) -> None:
    client = await hass_ws_client(hass)
    await client.send_json({
        "id": 2, "type": "haclaw/chat",
        "conversation_id": "c1", "user_message": "hi", "mode": "garbage",
    })
    msg = await client.receive_json()
    assert msg["success"] is False
```

- [ ] **Step 5: Run tests**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_integration_services.py -v -k "ws_chat"
```

- [ ] **Step 6: Commit**

```bash
git add custom_components/haclaw/__init__.py tests/test_integration_services.py
git commit -m "feat: add haclaw/chat WS command wired to chat_session"
```

---

### Task 14: Conversations list/clear WS commands

**Files:**
- Modify: `custom_components/haclaw/__init__.py`
- Modify: `tests/test_integration_services.py`

- [ ] **Step 1: Add WS handlers**

```python
from .const import WS_TYPE_CONVERSATIONS_CLEAR, WS_TYPE_CONVERSATIONS_LIST
from .storage.conversations import (
    clear_all,
    clear_conversation,
    list_conversations,
)


@websocket_api.websocket_command({
    vol.Required("type"): WS_TYPE_CONVERSATIONS_LIST,
})
@websocket_api.async_response
async def _async_handle_ws_conversations_list(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    path = _storage_path(hass, CONVERSATIONS_FILE)
    convs = await hass.async_add_executor_job(list_conversations, path)
    summary = [{
        "id": c["id"],
        "created_at": c.get("created_at"),
        "updated_at": c.get("updated_at"),
        "message_count": len(c.get("messages", [])),
    } for c in convs]
    connection.send_result(msg["id"], {"conversations": summary})


@websocket_api.websocket_command({
    vol.Required("type"): WS_TYPE_CONVERSATIONS_CLEAR,
    vol.Optional("conversation_id"): str,
})
@websocket_api.async_response
async def _async_handle_ws_conversations_clear(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    path = _storage_path(hass, CONVERSATIONS_FILE)
    if "conversation_id" in msg and msg["conversation_id"]:
        await hass.async_add_executor_job(clear_conversation, path, msg["conversation_id"])
    else:
        await hass.async_add_executor_job(clear_all, path)
    connection.send_result(msg["id"], {"success": True})
```

In `_async_register_ws_commands`, also register these two:

```python
websocket_api.async_register_command(hass, _async_handle_ws_conversations_list)
websocket_api.async_register_command(hass, _async_handle_ws_conversations_clear)
```

- [ ] **Step 2: Add tests**

```python
@pytest.mark.asyncio
async def test_ws_conversations_list_returns_summary(
    hass, configured_entry, hass_ws_client,
) -> None:
    from custom_components.haclaw.storage.conversations import append_message
    convs_path = Path(hass.config.path("haclaw", "conversations.json"))
    append_message(convs_path, "c1", {"role": "user", "content": "hi"})

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "haclaw/conversations/list"})
    msg = await client.receive_json()
    assert msg["success"] is True
    assert msg["result"]["conversations"][0]["id"] == "c1"
    assert msg["result"]["conversations"][0]["message_count"] == 1


@pytest.mark.asyncio
async def test_ws_conversations_clear_specific(
    hass, configured_entry, hass_ws_client,
) -> None:
    from custom_components.haclaw.storage.conversations import append_message
    convs_path = Path(hass.config.path("haclaw", "conversations.json"))
    append_message(convs_path, "c1", {"role": "user", "content": "hi"})

    client = await hass_ws_client(hass)
    await client.send_json({
        "id": 1, "type": "haclaw/conversations/clear",
        "conversation_id": "c1",
    })
    msg = await client.receive_json()
    assert msg["success"] is True
```

- [ ] **Step 3: Run tests**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/test_integration_services.py -v -k "conversations"
```

- [ ] **Step 4: Commit**

```bash
git add custom_components/haclaw/__init__.py tests/test_integration_services.py
git commit -m "feat: add conversations list/clear WS commands for history drawer"
```

---

## Phase 5 — Frontend rewrite (single file, incremental)

The whole `haclaw-panel.js` is rewritten. Each task **replaces or extends** the file with a more complete version. Manual verification by reloading the HA panel between tasks.

**Throughout Phase 5**: All HTML fragments containing `${userValue}` interpolations MUST use the ``this._html`...`` tagged template helper (defined below). This auto-escapes values to prevent XSS. Static fragments without `${}` may use regular template literals.

### Task 15: Frontend skeleton — status bar + empty state + input + mode chips

**Files:** Modify `custom_components/haclaw/frontend/haclaw-panel.js` (full rewrite)

- [ ] **Step 1: Replace `haclaw-panel.js` with the skeleton**

```javascript
// custom_components/haclaw/frontend/haclaw-panel.js
class HAclawPanel extends HTMLElement {
  constructor() {
    super();
    this._hass = undefined;
    this._messages = [];
    this._mode = this._restoreMode();
    this._modelName = "";
    this._providerOk = false;
    this._envFailingCount = 0;
    this._presenceBound = false;
    this._envCardShown = false;
    this._envState = null;
    this._busy = false;
    this._conversationId = `conv_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    this._suggestionChips = [
      "打开客厅灯",
      "生成晚 7 点开净化器的自动化",
      "当前模型连得通吗",
      "认领我的存在实体",
      "检查我的 HA 环境",
      "解释一下 automations.yaml 是什么",
    ];
  }

  set hass(hass) {
    this._hass = hass;
    this._readModelFromHass();
    this._render();
  }

  connectedCallback() {
    this._render();
    this._refreshState();
  }

  _restoreMode() {
    try {
      const v = localStorage.getItem("haclaw.last_mode");
      if (["plan", "automation", "execute"].includes(v)) return v;
    } catch (_e) { /* ignore */ }
    return "automation";
  }

  _readModelFromHass() {
    if (!this._hass) return;
    const entries = Object.values(this._hass.config?.entries || {})
      .filter((e) => e.domain === "haclaw");
    const opts = entries[0]?.options || entries[0]?.data || {};
    this._modelName = opts.model || "";
  }

  async _refreshState() {
    if (!this._hass) return;
    const dismissedLocal = (() => {
      try { return localStorage.getItem("haclaw.env_dismissed") === "1"; }
      catch (_e) { return false; }
    })();

    try {
      const result = await this._callService("get_environment_readiness", {});
      if (result) {
        this._envState = result;
        if (dismissedLocal) result.dismissed = true;
        this._providerOk = result.items?.[0]?.ok ?? false;
        this._envFailingCount = result.failing_required_count ?? 0;
        if (!result.dismissed && this._envFailingCount > 0 && !this._envCardShown) {
          this._messages.unshift({ kind: "env_check", payload: result });
          this._envCardShown = true;
        }
      }
    } catch (_e) { /* ignore */ }

    try {
      const presence = await this._callService("get_presence_binding", {});
      this._presenceBound = Boolean(presence?.me_person_entity_id);
    } catch (_e) { this._presenceBound = false; }

    this._render();
  }

  async _callService(service, data) {
    const result = await this._hass.connection.sendMessagePromise({
      type: "call_service",
      domain: "haclaw",
      service,
      service_data: data,
      return_response: true,
    });
    return result?.response;
  }

  _onSend() {
    const input = this.querySelector("#chat-input");
    if (!input) return;
    const text = input.value.trim();
    if (!text || this._busy) return;
    input.value = "";
    this._appendUserMessage(text);
  }

  _appendUserMessage(text) {
    this._messages.push({ kind: "user_text", text });
    this._render();
  }

  _onChipClick(text) {
    this._appendUserMessage(text);
  }

  _switchMode(m) {
    this._mode = m;
    try { localStorage.setItem("haclaw.last_mode", m); } catch (_e) { /* ignore */ }
    this._render();
  }

  _html(strings, ...values) {
    let out = strings[0];
    for (let i = 0; i < values.length; i++) {
      out += this._escape(values[i]) + strings[i + 1];
    }
    return out;
  }

  _escape(s) {
    return String(s ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  _modeLabel(m) {
    return ({plan: "📋 计划", automation: "⚡ 自动化", execute: "🛠 执行 ⚠️"}[m] || m);
  }

  _renderMessage(m) {
    if (m.kind === "user_text") {
      return this._html`<div class="bubble user">${m.text}</div>`;
    }
    return "";
  }

  _render() {
    if (!this.isConnected) return;

    const status = `${this._modelName || "未配置"} · ${this._providerOk ? "✅" : "❌"}`;
    const failingBadge = this._envFailingCount > 0
      ? this._html`<span class="badge warn">⚠️${String(this._envFailingCount)}</span>` : "";
    const presenceHint = this._presenceBound ? "" : `<span class="badge hint">💡未绑存在</span>`;

    const empty = this._messages.length === 0;
    const greetingHTML = empty ? `
      <div class="empty">
        <h2>HAclaw,你想让我做什么?</h2>
        <div class="chips">
          ${this._suggestionChips.map((c) =>
            this._html`<button class="chip" data-chip="${c}">${c}</button>`
          ).join("")}
        </div>
      </div>
    ` : "";

    const messagesHTML = this._messages.map((m) => this._renderMessage(m)).join("");

    const modesHTML = ["plan", "automation", "execute"].map((m) =>
      `<button class="mode-chip ${m === this._mode ? "active" : ""}" data-mode="${m}">${this._escape(this._modeLabel(m))}</button>`
    ).join("");

    this.innerHTML = `
      <main class="page">
        <header class="topbar">
          <div class="left">${this._html`HAclaw · ${status}`}</div>
          <div class="right">${presenceHint}${failingBadge}<button class="icon-btn" id="open-settings">⚙</button><button class="icon-btn" id="open-drawer">☰</button></div>
        </header>
        <section class="conversation">${greetingHTML}${messagesHTML}</section>
        <footer class="composer">
          <div class="modes">${modesHTML}</div>
          ${this._mode === "execute" ? `<div class="execute-warn">⚠️ 执行模式实验中,本期不会真正控制设备</div>` : ""}
          <div class="input-row">
            <input id="chat-input" type="text" placeholder="输入消息..." />
            <button id="send-btn">发送</button>
          </div>
        </footer>
      </main>
      <style>${this._styles()}</style>
    `;

    this._wireEvents();
  }

  _wireEvents() {
    this.querySelectorAll(".chip[data-chip]").forEach((el) => {
      el.addEventListener("click", () => this._onChipClick(el.dataset.chip));
    });
    this.querySelectorAll(".mode-chip[data-mode]").forEach((el) => {
      el.addEventListener("click", () => this._switchMode(el.dataset.mode));
    });
    this.querySelector("#send-btn")?.addEventListener("click", () => this._onSend());
    this.querySelector("#chat-input")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") this._onSend();
    });
  }

  _styles() {
    return `
      .page { display: flex; flex-direction: column; height: 100vh; color: var(--primary-text-color); }
      .topbar { display: flex; justify-content: space-between; align-items: center;
        padding: 8px 16px; border-bottom: 1px solid var(--divider-color); }
      .topbar .right { display: flex; gap: 8px; align-items: center; }
      .badge { font-size: 12px; padding: 2px 8px; border-radius: 12px; }
      .badge.warn { background: rgba(219, 68, 55, 0.15); color: #db4437; }
      .badge.hint { background: rgba(255, 193, 7, 0.15); color: #b88d00; }
      .icon-btn { background: transparent; border: 0; cursor: pointer; font-size: 18px; }
      .conversation { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
      .empty { text-align: center; margin-top: 60px; }
      .empty h2 { font-size: 28px; font-weight: 650; margin: 0 0 24px; }
      .empty .chips { display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; }
      .chip { padding: 12px 20px; border: 1px solid var(--divider-color); border-radius: 24px;
        background: var(--card-background-color); cursor: pointer; font-size: 14px; min-height: 44px; color: var(--primary-text-color); }
      .chip:hover { background: var(--secondary-background-color); }
      .composer { border-top: 1px solid var(--divider-color); padding: 12px 16px; }
      .modes { display: flex; gap: 8px; margin-bottom: 8px; }
      .mode-chip { padding: 6px 14px; border: 1px solid var(--divider-color); border-radius: 16px;
        background: transparent; cursor: pointer; font-size: 13px; color: var(--primary-text-color); }
      .mode-chip.active { background: var(--primary-color); color: var(--text-primary-color); border-color: var(--primary-color); }
      .execute-warn { color: #db4437; font-size: 12px; padding: 4px 8px; }
      .input-row { display: flex; gap: 8px; }
      .input-row input { flex: 1; padding: 10px 12px; border: 1px solid var(--divider-color);
        border-radius: 6px; background: var(--card-background-color); color: var(--primary-text-color); }
      .input-row button { padding: 10px 20px; background: var(--primary-color); color: var(--text-primary-color);
        border: 0; border-radius: 6px; cursor: pointer; min-height: 44px; }
      .bubble { padding: 12px 16px; border-radius: 12px; max-width: 75%; word-wrap: break-word; }
      .bubble.user { background: var(--primary-color); color: var(--text-primary-color); align-self: flex-end; }
      .bubble.assistant { background: var(--card-background-color); border: 1px solid var(--divider-color); align-self: flex-start; }

      @media (max-width: 640px) {
        .topbar .right .icon-btn:nth-child(3) { display: none; }
        .empty .chips { flex-direction: column; }
        .modes { flex-wrap: wrap; }
        .mode-chip { flex: 1; min-width: 80px; }
      }
    `;
  }
}

customElements.define("haclaw-panel", HAclawPanel);
```

- [ ] **Step 2: Manual verify**

```bash
~/.venvs/haclaw-ha/bin/hass --script check_config -c ~/.ha-dev/haclaw
scripts/run_hass_dev.sh
```

Open `http://localhost:8123/haclaw`. Verify status bar, greeting, 6 chips, mode chips, input. Click chip → user bubble; type and send → user bubble (no assistant reply yet, that's Task 16).

- [ ] **Step 3: Commit**

```bash
git add custom_components/haclaw/frontend/haclaw-panel.js
git commit -m "feat(panel): chat-first skeleton — status bar, empty state, input, mode chips"
```

---

### Task 16: Wire chat WS + render `final_response`

**Files:** Modify `custom_components/haclaw/frontend/haclaw-panel.js`

- [ ] **Step 1: Add `_sendChat` and update `_onSend` and `_renderMessage`**

In `_onSend`, after `this._appendUserMessage(text);`, add `this._sendChat(text);`.

Add `_sendChat`:

```javascript
async _sendChat(text) {
  this._busy = true;
  this._messages.push({ kind: "thinking" });
  this._render();
  try {
    const result = await this._hass.connection.sendMessagePromise({
      type: "haclaw/chat",
      conversation_id: this._conversationId,
      user_message: text,
      mode: this._mode,
    });
    this._messages.pop();
    this._messages.push({ kind: "assistant_msg", payload: result.assistant_message });
  } catch (err) {
    this._messages.pop();
    this._messages.push({ kind: "error", text: err?.message || "请求失败" });
  } finally {
    this._busy = false;
    this._render();
  }
}
```

Update `_renderMessage`:

```javascript
_renderMessage(m) {
  if (m.kind === "user_text") {
    return this._html`<div class="bubble user">${m.text}</div>`;
  }
  if (m.kind === "thinking") {
    return `<div class="bubble assistant thinking">思考中...</div>`;
  }
  if (m.kind === "error") {
    return this._html`<div class="bubble error">⚠️ ${m.text}</div>`;
  }
  if (m.kind === "assistant_msg") {
    return this._renderAssistant(m.payload);
  }
  return "";
}

_renderAssistant(payload) {
  if (payload?.type === "final_response") {
    const text = payload.message || "";
    const display = text.replace(/^\[BIND_PRESENCE\]\s*/, "");
    return this._html`<div class="bubble assistant">${display}</div>`;
  }
  return this._html`<div class="bubble assistant">${JSON.stringify(payload)}</div>`;
}
```

Append styles:

```javascript
// inside _styles return string, append:
.bubble.thinking { font-style: italic; opacity: 0.6; }
.bubble.error { background: rgba(255, 193, 7, 0.15); border: 1px solid #b88d00; align-self: flex-start; }
```

- [ ] **Step 2: Manual verify**

Reload panel. Type "你好" → see "思考中..." → real model reply. (If no provider configured, you'll see error bubble — that's expected.)

- [ ] **Step 3: Commit**

```bash
git add custom_components/haclaw/frontend/haclaw-panel.js
git commit -m "feat(panel): wire haclaw/chat WS and render final_response"
```

---

### Task 17: `clarification` component — chips + free-text input

**Files:** Modify `custom_components/haclaw/frontend/haclaw-panel.js`

- [ ] **Step 1: Extend `_renderAssistant` and add card renderer**

Update dispatch in `_renderAssistant`:

```javascript
_renderAssistant(payload) {
  if (payload?.type === "final_response") {
    return this._renderFinalResponseBubble(payload);
  }
  if (payload?.type === "clarification") {
    return this._renderClarificationCard(payload);
  }
  return this._html`<div class="bubble assistant">${JSON.stringify(payload)}</div>`;
}

_renderFinalResponseBubble(payload) {
  const text = payload.message || "";
  const display = text.replace(/^\[BIND_PRESENCE\]\s*/, "");
  return this._html`<div class="bubble assistant">${display}</div>`;
}

_renderClarificationCard(payload) {
  const cands = Array.isArray(payload.candidates) ? payload.candidates : [];
  const allowFree = Boolean(payload.allow_free_text);
  const placeholder = payload.free_text_placeholder || "或者直接输入...";
  const cardId = `clar_${this._messages.length}`;

  const chipsHTML = cands.map((c) =>
    this._html`<button class="cand-chip" data-card="${cardId}" data-label="${c.label || ""}">
      <span class="cand-label">${c.label || ""}</span>
      ${c.subtitle ? this._html`<span class="cand-sub">${c.subtitle}</span>` : ""}
    </button>`
  ).join("");

  const freeHTML = allowFree ? this._html`
    <div class="cand-free">
      <span class="cand-free-hint">或者自定义:</span>
      <div class="cand-free-row">
        <input type="text" class="cand-free-input" data-card="${cardId}" placeholder="${placeholder}" />
        <button class="cand-free-send" data-card="${cardId}">发送</button>
      </div>
    </div>
  ` : "";

  return this._html`<div class="card clarification" data-card-id="${cardId}">
    <div class="card-msg">${payload.message || ""}</div>
    <div class="cand-chips">${{__raw: chipsHTML}}</div>
    ${{__raw: freeHTML}}
  </div>`.replace(/&quot;__raw&quot;:&quot;([^&]*?)&quot;/g, "$1");
}
```

The `_html` tag escapes everything. To embed pre-built sub-fragments (which are themselves already escaped via `_html`), the safest pattern: skip the outer tagged template for the wrapper and use plain template strings for static parts + pre-escaped substrings:

Replace the `_renderClarificationCard` return statement with plain template literal where only `payload.message` and `cardId` are escaped:

```javascript
return `<div class="card clarification" data-card-id="${this._escape(cardId)}">
  <div class="card-msg">${this._escape(payload.message || "")}</div>
  <div class="cand-chips">${chipsHTML}</div>
  ${freeHTML}
</div>`;
```

(Replace the messy regex hack with direct interpolation; both `chipsHTML` and `freeHTML` are already escaped via `_html` inside their own builders.)

- [ ] **Step 2: Wire chip + free-text handlers in `_wireEvents`**

```javascript
this.querySelectorAll(".cand-chip[data-label]").forEach((el) => {
  el.addEventListener("click", () => {
    const label = el.dataset.label;
    this._appendUserMessage(label);
    this._sendChat(label);
  });
});
this.querySelectorAll(".cand-free-send[data-card]").forEach((el) => {
  el.addEventListener("click", () => {
    const card = el.dataset.card;
    const inp = this.querySelector(`.cand-free-input[data-card="${card}"]`);
    const text = inp?.value.trim();
    if (!text) return;
    inp.value = "";
    this._appendUserMessage(text);
    this._sendChat(text);
  });
});
this.querySelectorAll(".cand-free-input[data-card]").forEach((el) => {
  el.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      this.querySelector(`.cand-free-send[data-card="${el.dataset.card}"]`)?.click();
    }
  });
});
```

- [ ] **Step 3: Append styles**

```css
.card { border: 1px solid var(--divider-color); border-radius: 12px;
  padding: 12px; align-self: flex-start; max-width: 90%; background: var(--card-background-color); }
.card-msg { font-weight: 600; margin-bottom: 12px; }
.cand-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.cand-chip { display: flex; flex-direction: column; align-items: flex-start; padding: 10px 14px;
  border: 1px solid var(--divider-color); border-radius: 10px; background: var(--card-background-color);
  cursor: pointer; min-width: 120px; min-height: 44px; color: var(--primary-text-color); }
.cand-chip:hover { background: var(--secondary-background-color); }
.cand-label { font-size: 14px; font-weight: 600; }
.cand-sub { font-size: 11px; color: var(--secondary-text-color); margin-top: 2px; }
.cand-free { margin-top: 12px; }
.cand-free-hint { font-size: 12px; color: var(--secondary-text-color); }
.cand-free-row { display: flex; gap: 8px; margin-top: 6px; }
.cand-free-input { flex: 1; padding: 10px; border: 1px solid var(--divider-color);
  border-radius: 6px; background: var(--card-background-color); color: var(--primary-text-color);
  min-height: 40px; }
.cand-free-send { padding: 10px 16px; background: var(--primary-color); color: var(--text-primary-color);
  border: 0; border-radius: 6px; cursor: pointer; min-height: 40px; }
```

- [ ] **Step 4: Manual verify**

Trigger a clarification (e.g., "晚上开净化器" with multiple matching entities). See chips. Click chip → next round. With `allow_free_text=true` (e.g., 节假日 case), see input + send.

- [ ] **Step 5: Commit**

```bash
git add custom_components/haclaw/frontend/haclaw-panel.js
git commit -m "feat(panel): clarification chip card with free-text input box"
```

---

### Task 18: `automation_draft` card with rationale + missing_integrations + approve

**Files:** Modify `custom_components/haclaw/frontend/haclaw-panel.js`

- [ ] **Step 1: Add dispatch for automation_draft**

In `_renderAssistant`:

```javascript
if (payload?.type === "automation_draft") {
  return this._renderDraftCard(payload);
}
```

Implement (note: payload is cached in DOM via JSON.stringify + base64 to avoid HTML attribute escaping mishaps):

```javascript
_renderDraftCard(payload) {
  const cardId = `draft_${this._messages.length}`;
  const requires = Boolean(payload.requires_confirmation);
  const missing = Array.isArray(payload.missing_integrations) ? payload.missing_integrations : [];
  const hasRationale = payload.rationale && typeof payload.rationale === "object";
  const yaml = JSON.stringify(payload.automation || {}, null, 2);
  const title = payload.title || payload.automation?.alias || "未命名草稿";
  const risk = payload.risk_level || "low";
  const approveLabel = requires ? "审批并确认风险" : "审批写入";

  // Cache payload via base64 to avoid attribute escaping issues
  const cached = btoa(unescape(encodeURIComponent(JSON.stringify(payload))));

  const missingHTML = missing.map((m) => `
    <div class="warn-row">
      ⚠️ 草稿用到 <code>${this._escape(m.service || "")}</code>,但 ${this._escape(m.integration_name || "")} 未检测到。
      ${m.install_link ? this._html`<a href="${m.install_link}" target="_blank">官方指引</a>` : ""}
      ${m.install_prompt ? this._html`<button class="btn-install-prompt" data-card="${cardId}" data-domain="${m.domain || ""}">📋 安装指令</button>` : ""}
    </div>
  `).join("");

  const rationaleHTML = !hasRationale ? `
    <div class="warn-box small">⚠️ 模型未提供设计依据(rationale),无法审计这个草稿是怎么推演出来的;建议丢弃后再试一次。</div>
  ` : `
    <div class="rationale">
      <div class="rationale-title">设计依据(从对话推演)</div>
      <div class="rationale-row"><b>实体:</b> ${this._renderRationaleField(payload.rationale.entities)}</div>
      <div class="rationale-row"><b>触发:</b> ${this._renderRationaleField(payload.rationale.trigger)}</div>
      <div class="rationale-row"><b>条件:</b> ${this._renderRationaleField(payload.rationale.conditions)}</div>
      <div class="rationale-row"><b>动作:</b> ${this._renderRationaleField(payload.rationale.actions)}</div>
      <div class="rationale-row"><b>边缘情况:</b> ${this._renderRationaleField(payload.rationale.edge_cases)}</div>
    </div>
  `;

  const approveDisabled = (!hasRationale || missing.length > 0) ? "disabled" : "";
  const approveTitle = approveDisabled ? "先解决警告(rationale 或缺集成)再审批" : "";

  const inAutomationMode = this._mode === "automation";
  const planHint = !inAutomationMode ? "(切到自动化模式后才能审批写入)" : "";

  return `<div class="card draft" data-card-id="${this._escape(cardId)}" data-payload="${this._escape(cached)}">
    <div class="draft-head">
      <span class="draft-title">${this._escape(title)}</span>
      <span class="draft-risk risk-${this._escape(risk)}">${this._escape(risk)}</span>
    </div>
    ${missing.length > 0 ? `<div class="warn-box">${missingHTML}</div>` : ""}
    ${rationaleHTML}
    <details class="draft-yaml"><summary>查看 YAML</summary><pre>${this._escape(yaml)}</pre></details>
    <div class="draft-actions">
      <button class="btn-primary btn-approve" data-card="${this._escape(cardId)}" ${approveDisabled} ${approveTitle ? `title="${this._escape(approveTitle)}"` : ""} ${!inAutomationMode ? "disabled" : ""}>
        ${this._escape(approveLabel)} ${this._escape(planHint)}
      </button>
      <button class="btn-secondary" data-card="${this._escape(cardId)}" data-action="discard">丢弃</button>
      <button class="btn-secondary" data-card="${this._escape(cardId)}" data-action="edit">修改后再说</button>
    </div>
  </div>`;
}

_renderRationaleField(v) {
  if (Array.isArray(v)) {
    return v.length === 0 ? "<span class=\"muted\">无</span>" : v.map((x) => this._escape(String(x))).join("、");
  }
  return this._escape(String(v ?? "无"));
}
```

- [ ] **Step 2: Wire approve / discard / edit / install in `_wireEvents`**

```javascript
this.querySelectorAll(".btn-approve[data-card]").forEach((el) => {
  el.addEventListener("click", () => this._onApproveDraft(el.closest(".card.draft")));
});
this.querySelectorAll(".card.draft [data-action='discard']").forEach((el) => {
  el.addEventListener("click", () => {
    const card = el.closest(".card.draft");
    card?.classList.add("discarded");
    const actions = card?.querySelector(".draft-actions");
    if (actions) actions.innerHTML = "<span class=\"muted\">已丢弃</span>";
  });
});
this.querySelectorAll(".card.draft [data-action='edit']").forEach((el) => {
  el.addEventListener("click", () => {
    const card = el.closest(".card.draft");
    const yaml = card?.querySelector(".draft-yaml pre")?.textContent || "";
    const input = this.querySelector("#chat-input");
    if (input) { input.value = yaml; input.focus(); }
  });
});
this.querySelectorAll(".btn-install-prompt[data-domain]").forEach((el) => {
  el.addEventListener("click", () => this._openInstallModal(el.dataset.domain));
});
```

Add helpers:

```javascript
async _onApproveDraft(cardEl) {
  if (!cardEl) return;
  let payload;
  try {
    payload = JSON.parse(decodeURIComponent(escape(atob(cardEl.dataset.payload))));
  } catch (_e) {
    this._toast("草稿数据无效");
    return;
  }

  let draftId;
  try {
    const created = await this._callService("create_automation_draft", {
      title: payload.title || payload.automation?.alias || "草稿",
      description: payload.description || "",
      automation: payload.automation,
      source: "panel",
    });
    if (!created?.success) {
      this._toast(created?.message || "创建草稿失败");
      return;
    }
    draftId = created.draft.id;
  } catch (err) {
    this._toast(err?.message || "创建草稿失败");
    return;
  }

  try {
    const approved = await this._callService("approve_automation_draft", {
      draft_id: draftId,
      confirmed: Boolean(payload.requires_confirmation),
    });
    if (!approved?.success) {
      this._toast(approved?.message || "审批失败");
      return;
    }
    this._toast(approved.message || "已写入");
    const actions = cardEl.querySelector(".draft-actions");
    if (actions) actions.innerHTML = "<span class=\"muted\">已审批写入</span>";
  } catch (err) {
    this._toast(err?.message || "审批失败");
  }
}

_toast(text) {
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = text;
  this.appendChild(t);
  setTimeout(() => t.remove(), 2500);
}
```

- [ ] **Step 3: Append styles**

```css
.card.draft .draft-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.card.draft .draft-title { font-weight: 700; }
.draft-risk { font-size: 11px; padding: 2px 8px; border-radius: 10px; text-transform: uppercase; }
.risk-low { background: rgba(27,143,77,0.15); color: #1b8f4d; }
.risk-medium { background: rgba(255,193,7,0.15); color: #b88d00; }
.risk-high, .risk-critical { background: rgba(219,68,55,0.15); color: #db4437; }
.warn-box { border: 1px solid #b88d00; background: rgba(255,193,7,0.1);
  padding: 8px 12px; border-radius: 8px; margin: 8px 0; font-size: 13px; }
.warn-box.small { font-size: 12px; }
.warn-row { margin: 4px 0; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.warn-row code { padding: 1px 4px; background: rgba(0,0,0,0.05); border-radius: 4px; }
.btn-install-prompt { padding: 4px 10px; background: var(--primary-color); color: var(--text-primary-color);
  border: 0; border-radius: 6px; cursor: pointer; font-size: 12px; }
.rationale { margin: 8px 0; padding: 8px 12px; background: rgba(0,0,0,0.04); border-radius: 8px; font-size: 13px; }
.rationale-title { font-weight: 700; margin-bottom: 6px; }
.rationale-row { margin: 2px 0; }
.rationale-row .muted { color: var(--secondary-text-color); }
.draft-yaml { margin: 8px 0; }
.draft-yaml pre { max-height: 240px; overflow: auto; padding: 8px;
  background: rgba(0,0,0,0.05); border-radius: 6px; font-family: ui-monospace, monospace; font-size: 12px; }
.draft-actions { display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap; }
.btn-primary { padding: 8px 14px; background: var(--primary-color); color: var(--text-primary-color);
  border: 0; border-radius: 6px; cursor: pointer; min-height: 40px; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { padding: 8px 14px; background: transparent; color: var(--primary-text-color);
  border: 1px solid var(--divider-color); border-radius: 6px; cursor: pointer; min-height: 40px; }
.toast { position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%);
  padding: 10px 16px; background: rgba(0,0,0,0.85); color: white; border-radius: 8px;
  font-size: 13px; z-index: 1000; max-width: 80%; }
.discarded { opacity: 0.5; }
.muted { color: var(--secondary-text-color); }
```

- [ ] **Step 4: Manual verify**

Trigger a draft (e.g., "我每天 19 点开客厅灯,周末也开"). Card folds with title + risk. Expand YAML; rationale visible. Approve calls services; toast appears. Plan mode → button disabled with hint.

- [ ] **Step 5: Commit**

```bash
git add custom_components/haclaw/frontend/haclaw-panel.js
git commit -m "feat(panel): automation_draft card with rationale, missing-integrations, approve flow"
```

---

### Task 19: `risk_confirmation`, `tool_call`, fallback rendering

**Files:** Modify `custom_components/haclaw/frontend/haclaw-panel.js`

- [ ] **Step 1: Extend dispatch**

In `_renderAssistant`, add:

```javascript
if (payload?.type === "risk_confirmation") {
  return this._renderRiskCard(payload);
}
if (payload?.type === "tool_call") {
  return this._renderToolCallLine(payload);
}
```

Implement:

```javascript
_renderRiskCard(payload) {
  const planned = payload.planned_action ? JSON.stringify(payload.planned_action, null, 2) : "";
  const risk = payload.risk_level || "high";
  const detailsHTML = planned ? `<details><summary>计划动作</summary><pre>${this._escape(planned)}</pre></details>` : "";
  return `<div class="card risk risk-${this._escape(risk)}">
    <div class="risk-head">⚠️ 高风险操作 · ${this._escape(risk)}</div>
    <div class="risk-msg">${this._escape(payload.message || "")}</div>
    ${detailsHTML}
    <div class="draft-actions">
      <button class="btn-primary" disabled title="工具执行层 v1.x 启用,本期不真执行">确认执行</button>
      <button class="btn-secondary">取消</button>
    </div>
  </div>`;
}

_renderToolCallLine(payload) {
  const tool = payload.tool || "?";
  return this._html`<div class="tool-call-line">↪ 模型尝试调用 <code>${tool}</code>(本阶段不执行)</div>`;
}
```

Append styles:

```css
.card.risk { border-color: #db4437; background: rgba(219,68,55,0.05); }
.card.risk .risk-head { color: #db4437; font-weight: 700; margin-bottom: 8px; }
.card.risk .risk-msg { margin-bottom: 8px; }
.card.risk pre { background: rgba(0,0,0,0.05); padding: 6px; border-radius: 6px; font-size: 12px; }
.tool-call-line { font-size: 12px; color: var(--secondary-text-color); align-self: flex-start;
  font-style: italic; padding: 6px 12px; }
.tool-call-line code { background: rgba(0,0,0,0.05); padding: 1px 4px; border-radius: 4px; }
```

- [ ] **Step 2: Manual verify**

Switch to execute mode, ask "打开客厅灯" → see `tool_call` gray line. Trigger high-risk (e.g., "我到家就解锁前门") → red card.

- [ ] **Step 3: Commit**

```bash
git add custom_components/haclaw/frontend/haclaw-panel.js
git commit -m "feat(panel): risk_confirmation card and tool_call gray line"
```

---

### Task 20: Environment readiness card + install_prompt modal

**Files:** Modify `custom_components/haclaw/frontend/haclaw-panel.js`

- [ ] **Step 1: Add env_check render in `_renderMessage`**

```javascript
if (m.kind === "env_check") {
  return this._renderEnvCheckCard(m.payload);
}
```

Implement:

```javascript
_renderEnvCheckCard(state) {
  const items = [...(state.items || []), ...(state.advanced || [])];
  const rowsHTML = items.map((it) => {
    const linksHTML = (it.links || []).map((l) =>
      this._html`<a href="${l.url}" target="_blank">${l.text}</a>`
    ).join(" · ");
    const installBtn = it.install_prompt
      ? this._html`<button class="btn-install-prompt" data-domain="${it.id}">📋 安装指令</button>`
      : "";
    const hint = !it.ok && it.hint ? this._html`<span class="env-hint">${it.hint}</span>` : "";
    return `<div class="env-row ${it.ok ? "ok" : "fail"}">
      <span class="env-status">${it.ok ? "✅" : "⚠️"}</span>
      <span class="env-label">${this._escape(it.label || "")}</span>
      ${hint}
      <span class="env-actions">${linksHTML} ${installBtn}</span>
    </div>`;
  }).join("");

  return `<div class="card env-check">
    <div class="env-head">🛠 首次设置 · 我建议先检查这些</div>
    ${rowsHTML}
    <div class="env-foot">
      <button class="btn-secondary" data-action="env-dismiss">全部跳过,以后再说</button>
      <button class="btn-secondary" data-action="env-recheck">重新检查</button>
    </div>
  </div>`;
}
```

- [ ] **Step 2: Wire env actions + install modal**

In `_wireEvents`:

```javascript
this.querySelectorAll("[data-action='env-dismiss']").forEach((el) => {
  el.addEventListener("click", () => this._dismissEnv());
});
this.querySelectorAll("[data-action='env-recheck']").forEach((el) => {
  el.addEventListener("click", () => {
    this._envCardShown = false;
    this._messages = this._messages.filter((m) => m.kind !== "env_check");
    try { localStorage.removeItem("haclaw.env_dismissed"); } catch (_e) { /* ignore */ }
    this._refreshState();
  });
});
this.querySelectorAll(".btn-install-prompt[data-domain]").forEach((el) => {
  el.addEventListener("click", () => this._openInstallModal(el.dataset.domain));
});
```

Add helpers:

```javascript
_dismissEnv() {
  try { localStorage.setItem("haclaw.env_dismissed", "1"); } catch (_e) { /* ignore */ }
  this._messages = this._messages.filter((m) => m.kind !== "env_check");
  this._render();
}

_openInstallModal(domain) {
  const items = [...(this._envState?.items || []), ...(this._envState?.advanced || [])];
  let prompt = items.find((i) => i.id === domain)?.install_prompt || null;
  if (!prompt) prompt = this._findDraftMissingPrompt(domain);
  if (!prompt) return;

  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.innerHTML = `
    <div class="modal">
      <div class="modal-head">
        <span>${this._escape("安装指令 — " + (prompt.title || ""))}</span>
        <button class="modal-close">✕</button>
      </div>
      <div class="modal-info">粘贴到 Claude Code / Codex / 其他 AI agent。⚠️ 黄底字段是占位符,在你的 AI agent 那边亲自填,不要在这里改。</div>
      <textarea class="modal-body" readonly></textarea>
      <div class="modal-foot">
        <button class="btn-primary modal-copy">📋 复制</button>
        <button class="btn-secondary modal-close">关闭</button>
      </div>
    </div>
  `;
  // Set body via textContent to avoid HTML interpretation
  overlay.querySelector(".modal-body").value = prompt.body || "";
  document.body.appendChild(overlay);

  overlay.querySelectorAll(".modal-close").forEach((b) => b.addEventListener("click", () => overlay.remove()));
  overlay.querySelector(".modal-copy")?.addEventListener("click", async () => {
    const text = overlay.querySelector(".modal-body").value;
    try {
      await navigator.clipboard.writeText(text);
      this._toast("已复制 · 粘贴到你的 AI agent · 黄底占位符在那边亲自填");
    } catch (_e) {
      this._toast("复制失败,请手动复制");
    }
  });
}

_findDraftMissingPrompt(domain) {
  for (const m of this._messages) {
    if (m.kind !== "assistant_msg") continue;
    const missing = m.payload?.missing_integrations || [];
    const found = missing.find((mi) => mi.domain === domain);
    if (found?.install_prompt) return found.install_prompt;
  }
  return null;
}
```

Append styles:

```css
.card.env-check .env-head { font-weight: 700; margin-bottom: 8px; }
.env-row { display: flex; gap: 8px; align-items: center; padding: 6px 0;
  flex-wrap: wrap; border-bottom: 1px solid var(--divider-color); }
.env-row:last-child { border-bottom: 0; }
.env-row .env-label { font-weight: 600; }
.env-row .env-hint { color: var(--secondary-text-color); font-size: 12px; }
.env-row .env-actions { margin-left: auto; display: flex; gap: 8px; flex-wrap: wrap; }
.env-foot { display: flex; gap: 8px; margin-top: 12px; justify-content: flex-end; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center; z-index: 2000; }
.modal { background: var(--card-background-color); color: var(--primary-text-color);
  border-radius: 12px; max-width: 700px; width: 92%; max-height: 86vh; display: flex; flex-direction: column; }
.modal-head { display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px; border-bottom: 1px solid var(--divider-color); font-weight: 700; }
.modal-close { background: transparent; border: 0; cursor: pointer; font-size: 18px; color: var(--primary-text-color); }
.modal-info { padding: 8px 16px; font-size: 12px; background: rgba(33,150,243,0.1); color: #1976d2; }
.modal-body { flex: 1; min-height: 240px; padding: 12px; font-family: ui-monospace, monospace;
  font-size: 12px; border: 0; resize: vertical; background: rgba(0,0,0,0.03); color: var(--primary-text-color); }
.modal-foot { padding: 12px 16px; display: flex; gap: 8px; justify-content: flex-end;
  border-top: 1px solid var(--divider-color); }
@media (max-width: 640px) {
  .modal { width: 96%; max-height: 92vh; }
}
```

- [ ] **Step 3: Manual verify**

Reload panel. If env not all green, env card appears at top. Click `📋 安装指令` → modal with template, read-only. Copy → toast. Click 全部跳过 → card removed; reload → no card.

- [ ] **Step 4: Commit**

```bash
git add custom_components/haclaw/frontend/haclaw-panel.js
git commit -m "feat(panel): env-check card + install_prompt modal (read-only + copy)"
```

---

### Task 21: Presence binding card + chip trigger + BIND_PRESENCE marker

**Files:** Modify `custom_components/haclaw/frontend/haclaw-panel.js`

- [ ] **Step 1: Override `_onChipClick` for the binding chip**

Replace `_onChipClick`:

```javascript
_onChipClick(text) {
  if (text === "认领我的存在实体") {
    this._maybeInjectPresenceCard();
    return;
  }
  this._appendUserMessage(text);
  this._sendChat(text);
}
```

- [ ] **Step 2: Detect BIND_PRESENCE marker in `_renderFinalResponseBubble` and schedule injection**

```javascript
_renderFinalResponseBubble(payload) {
  const text = payload.message || "";
  if (text.startsWith("[BIND_PRESENCE]")) {
    queueMicrotask(() => this._maybeInjectPresenceCard());
  }
  const display = text.replace(/^\[BIND_PRESENCE\]\s*/, "");
  return this._html`<div class="bubble assistant">${display}</div>`;
}
```

- [ ] **Step 3: Add presence card and bind logic**

```javascript
async _maybeInjectPresenceCard() {
  if (this._messages.some((m) => m.kind === "presence_bind" || m.kind === "presence_bind_done")) return;
  try {
    const result = await this._callService("list_presence_candidates", {});
    const candidates = result?.candidates || [];
    if (candidates.length === 0) {
      this._messages.push({ kind: "presence_bind_empty" });
    } else {
      this._messages.push({ kind: "presence_bind", candidates });
    }
    this._render();
  } catch (_e) { /* ignore */ }
}

async _bindPresence(entity_id) {
  try {
    const result = await this._callService("bind_presence_entity", { entity_id });
    if (!result?.success) {
      this._toast(result?.message || "绑定失败");
      return;
    }
    this._presenceBound = true;
    this._toast(`已绑定 ${entity_id}`);
    this._messages = this._messages.map((m) =>
      m.kind === "presence_bind" ? { kind: "presence_bind_done", entity_id } : m
    );
    this._render();
  } catch (err) {
    this._toast(err?.message || "绑定失败");
  }
}
```

In `_renderMessage`, add dispatches:

```javascript
if (m.kind === "presence_bind") {
  return this._renderPresenceCard(m.candidates);
}
if (m.kind === "presence_bind_empty") {
  return `<div class="card presence empty"><div class="card-msg">没有可用的 person.* / device_tracker.* 实体。请先在 HA 添加 person 或装 Companion App / 蓝牙追踪等集成,然后回来"重新检查环境"。</div></div>`;
}
if (m.kind === "presence_bind_done") {
  return this._html`<div class="card presence done">✅ 已绑定 ${m.entity_id}</div>`;
}
```

Implement:

```javascript
_renderPresenceCard(candidates) {
  const chipsHTML = (candidates || []).map((c) =>
    this._html`<button class="cand-chip" data-presence="${c.id}">
      <span class="cand-label">${c.label}</span>
      <span class="cand-sub">${c.subtitle}</span>
    </button>`
  ).join("");
  return `<div class="card presence">
    <div class="card-msg">认领你的存在实体(只存 entity_id,不会读取 MAC、手机号、GPS 坐标)</div>
    <div class="presence-list">${chipsHTML}</div>
  </div>`;
}
```

In `_wireEvents`:

```javascript
this.querySelectorAll(".cand-chip[data-presence]").forEach((el) => {
  el.addEventListener("click", () => this._bindPresence(el.dataset.presence));
});
```

Append styles:

```css
.card.presence .presence-list { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.card.presence.done { color: #1b8f4d; }
```

- [ ] **Step 4: Manual verify**

Click chip "认领我的存在实体" → presence card with candidates. Click one → toast "已绑定 X", card → done state, top status bar 💡 disappears on next refresh.

- [ ] **Step 5: Commit**

```bash
git add custom_components/haclaw/frontend/haclaw-panel.js
git commit -m "feat(panel): presence binding card with chip trigger and BIND_PRESENCE marker"
```

---

### Task 22: Mode persistence + execute warning dialog

**Files:** Modify `custom_components/haclaw/frontend/haclaw-panel.js`

- [ ] **Step 1: Update `_switchMode`**

```javascript
_switchMode(m) {
  if (m === "execute") {
    const seen = (() => {
      try { return localStorage.getItem("haclaw.execute_warning_seen") === "1"; }
      catch (_e) { return false; }
    })();
    if (!seen) {
      const ok = window.confirm(
        "🛠 执行模式 · 实验中\n\n" +
        "工具执行层 v1.x 启用,本模式现在仅展示模型会怎么提议工具调用,不会真正控制设备。\n\n" +
        "继续切换吗?",
      );
      if (!ok) return;
      try { localStorage.setItem("haclaw.execute_warning_seen", "1"); } catch (_e) { /* ignore */ }
    }
  }
  this._mode = m;
  try { localStorage.setItem("haclaw.last_mode", m); } catch (_e) { /* ignore */ }
  this._render();
}
```

(`_restoreMode` is already in constructor from Task 15.)

- [ ] **Step 2: Manual verify**

Switch to execute → confirm dialog. Confirm → mode switches; reload page → still execute. Switch to plan → reload → still plan.

- [ ] **Step 3: Commit**

```bash
git add custom_components/haclaw/frontend/haclaw-panel.js
git commit -m "feat(panel): execute mode one-time warning + mode persistence"
```

---

### Task 23: Settings modal + history drawer

**Files:** Modify `custom_components/haclaw/frontend/haclaw-panel.js`

- [ ] **Step 1: Wire settings + drawer triggers**

In `_wireEvents`:

```javascript
this.querySelector("#open-settings")?.addEventListener("click", () => this._openSettingsModal());
this.querySelector("#open-drawer")?.addEventListener("click", () => this._openDrawer());
```

- [ ] **Step 2: Add `_openSettingsModal`**

```javascript
_openSettingsModal() {
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.innerHTML = `
    <div class="modal">
      <div class="modal-head">
        <span>设置</span>
        <button class="modal-close">✕</button>
      </div>
      <div class="modal-section">
        <h3>Provider</h3>
        <div>当前模型: <code class="current-model"></code></div>
        <div class="row">
          <input type="text" id="new-model" placeholder="新模型名,例如 deepseek-coder" />
          <button class="btn-primary" id="apply-model">切换</button>
        </div>
        <div><a href="/config/integrations/integration/haclaw" target="_blank">去 HA 修改高级配置 →</a></div>
      </div>
      <div class="modal-section">
        <h3>环境</h3>
        <button class="btn-secondary" id="recheck-env">重新检查环境</button>
      </div>
      <div class="modal-section">
        <h3>存在感应</h3>
        <button class="btn-secondary" id="rebind-presence">重新绑定</button>
      </div>
      <div class="modal-section">
        <h3>对话</h3>
        <button class="btn-secondary" id="clear-current">清空当前对话</button>
        <button class="btn-secondary" id="clear-all">清空全部历史</button>
      </div>
      <div class="modal-foot">
        <button class="btn-secondary modal-close">关闭</button>
      </div>
    </div>
  `;
  overlay.querySelector(".current-model").textContent = this._modelName || "未配置";
  document.body.appendChild(overlay);
  overlay.querySelectorAll(".modal-close").forEach((b) => b.addEventListener("click", () => overlay.remove()));

  overlay.querySelector("#apply-model")?.addEventListener("click", async () => {
    const newModel = overlay.querySelector("#new-model").value.trim();
    if (!newModel) return;
    const r = await this._callService("switch_model", { model: newModel });
    if (r?.success) {
      this._modelName = newModel;
      this._toast("模型已切换");
      overlay.remove();
      this._render();
    } else {
      this._toast(r?.message || "切换失败");
    }
  });
  overlay.querySelector("#recheck-env")?.addEventListener("click", () => {
    overlay.remove();
    this._envCardShown = false;
    try { localStorage.removeItem("haclaw.env_dismissed"); } catch (_e) { /* ignore */ }
    this._messages = this._messages.filter((m) => m.kind !== "env_check");
    this._refreshState();
  });
  overlay.querySelector("#rebind-presence")?.addEventListener("click", () => {
    overlay.remove();
    this._messages = this._messages.filter((m) => m.kind !== "presence_bind" && m.kind !== "presence_bind_done");
    this._maybeInjectPresenceCard();
  });
  overlay.querySelector("#clear-current")?.addEventListener("click", async () => {
    await this._hass.connection.sendMessagePromise({
      type: "haclaw/conversations/clear",
      conversation_id: this._conversationId,
    });
    this._messages = [];
    this._render();
    overlay.remove();
  });
  overlay.querySelector("#clear-all")?.addEventListener("click", async () => {
    await this._hass.connection.sendMessagePromise({ type: "haclaw/conversations/clear" });
    this._messages = [];
    this._render();
    overlay.remove();
  });
}
```

- [ ] **Step 3: Add `_openDrawer`**

```javascript
async _openDrawer() {
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay drawer";
  overlay.innerHTML = `
    <div class="modal drawer-panel">
      <div class="modal-head">
        <span>对话历史</span>
        <button class="modal-close">✕</button>
      </div>
      <div class="drawer-body" id="drawer-list">加载中...</div>
      <div class="modal-foot">
        <button class="btn-primary" id="new-chat">+ 新对话</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
  overlay.querySelectorAll(".modal-close").forEach((b) => b.addEventListener("click", () => overlay.remove()));
  overlay.querySelector("#new-chat")?.addEventListener("click", () => {
    this._conversationId = `conv_${Date.now()}_${Math.random().toString(36).slice(2,8)}`;
    this._messages = [];
    this._envCardShown = false;
    this._render();
    overlay.remove();
  });

  try {
    const r = await this._hass.connection.sendMessagePromise({
      type: "haclaw/conversations/list",
    });
    const convs = r?.conversations || [];
    const listEl = overlay.querySelector("#drawer-list");
    if (convs.length === 0) {
      listEl.innerHTML = "<div class=\"muted\">暂无历史</div>";
    } else {
      listEl.innerHTML = convs.map((c) =>
        this._html`<div class="drawer-row">${c.id} <span class="muted">· ${String(c.message_count || 0)} 条</span></div>`
      ).join("");
    }
  } catch (_e) {
    overlay.querySelector("#drawer-list").textContent = "加载失败";
  }
}
```

- [ ] **Step 4: Append styles**

```css
.modal-section { padding: 12px 16px; border-bottom: 1px solid var(--divider-color); }
.modal-section h3 { margin: 0 0 8px; font-size: 14px; }
.modal-section .row { display: flex; gap: 8px; margin: 6px 0; }
.modal-section .row input { flex: 1; padding: 8px; border: 1px solid var(--divider-color);
  border-radius: 6px; background: var(--card-background-color); color: var(--primary-text-color); }
.modal.drawer-panel { max-width: 360px; height: 100vh; max-height: 100vh; border-radius: 0;
  position: fixed; right: 0; top: 0; }
.drawer-body { flex: 1; overflow-y: auto; padding: 12px 16px; }
.drawer-row { padding: 8px 0; border-bottom: 1px solid var(--divider-color); font-size: 13px; }
@media (max-width: 640px) {
  .modal.drawer-panel { max-width: 100%; }
}
```

- [ ] **Step 5: Manual verify**

Click ⚙ → settings modal. Switch model → toast + status bar updates. Recheck env → modal closes, env card reappears. Click ☰ → drawer with history; "+ 新对话" creates fresh conv.

- [ ] **Step 6: Commit**

```bash
git add custom_components/haclaw/frontend/haclaw-panel.js
git commit -m "feat(panel): settings modal + history drawer"
```

---

### Task 24: Mobile responsive polish

**Files:** Modify `custom_components/haclaw/frontend/haclaw-panel.js`

- [ ] **Step 1: Tighten mobile breakpoint** by adding/extending the `@media (max-width: 640px)` block in `_styles()`:

```css
@media (max-width: 640px) {
  .topbar .left { font-size: 13px; }
  .empty h2 { font-size: 22px; }
  .empty .chips { flex-direction: column; }
  .modes { flex-wrap: wrap; }
  .mode-chip { flex: 1; min-width: 80px; }
  .draft-actions { flex-wrap: wrap; }
  .bubble { max-width: 90%; }
  .cand-chips { flex-direction: column; }
  .cand-chip { width: 100%; }
}
```

(If existing `@media (max-width: 640px)` block exists from Task 15, **merge** these rules into it rather than duplicating.)

- [ ] **Step 2: Manual verify on Chrome DevTools mobile preview**

Open DevTools → Toolbar → iPhone 12 Pro / 360×800. Confirm: status bar fits, chips stack, mode chips wrap if narrow, modal fills width, send button tappable.

- [ ] **Step 3: Commit**

```bash
git add custom_components/haclaw/frontend/haclaw-panel.js
git commit -m "feat(panel): mobile breakpoints for status bar / chips / modals"
```

---

## Phase 6 — Final verification

### Task 25: Run full test suite + manual acceptance walk

**Files:** none (verification only)

- [ ] **Step 1: Run all tests**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/ -v
```

Expected: all green. Fix any failures before proceeding.

- [ ] **Step 2: HA config check**

```bash
~/.venvs/haclaw-ha/bin/hass --script check_config -c ~/.ha-dev/haclaw
```

Expected: no errors.

- [ ] **Step 3: Manual acceptance walk**

Run dev HA: `scripts/run_hass_dev.sh`. Open `http://localhost:8123/haclaw`.

Walk through every item in spec §14.1 / §14.2:

**Frontend (§14.1):**
- [ ] Status bar shows model + connection status
- [ ] Empty state with greeting + 6 suggestion chips
- [ ] Mode selector visible, default automation (or last selected)
- [ ] First-time env-check card appears (if not all green)
- [ ] Skip → reload → no card; ⚠️N badge in status bar
- [ ] Type "你好" → 思考中 → reply
- [ ] Trigger clarification → chips, click → next message
- [ ] `allow_free_text=false` → no input box; `=true` → real visible input + send
- [ ] chip ≥ 44×44px, font ≥ 14px (DevTools inspect)
- [ ] Mention 节假日 → model addresses workday
- [ ] Vague request → 1-3 clarification rounds before draft
- [ ] Draft card shows YAML + rationale section
- [ ] Plan mode draft button disabled with hint; automation mode enabled
- [ ] Missing rationale → button disabled + warning
- [ ] Missing integrations → warning + 📋 安装指令 button
- [ ] Install modal: read-only textarea, HA_KNOWN replaced, TODO_USER preserved as `{{TODO_USER:...}}`, copy works
- [ ] Switch to execute → confirm dialog → ⚠️ 实验中 label + tool_call gray line
- [ ] Mode persisted across reloads
- [ ] Settings modal: switch model updates status bar
- [ ] Presence chip injects card; pick entity → 💡 disappears after refresh
- [ ] Mobile (Chrome DevTools 360×800) all core paths work

**Backend (§14.2):**
- [ ] Spot check `~/.ha-dev/haclaw/haclaw/conversations.json` — no API key / token / cookie strings
- [ ] Spot check `~/.ha-dev/haclaw/haclaw/audit_log.jsonl` — no full assistant content, no MAC/IMEI
- [ ] No service call to `light.turn_on` etc. happens from a `tool_call` — confirm by `tail -f ~/.ha-dev/haclaw/home-assistant.log` while in execute mode and triggering a tool_call

- [ ] **Step 4: Final test suite + config check**

```bash
~/.venvs/haclaw-ha/bin/pytest tests/ -v && ~/.venvs/haclaw-ha/bin/hass --script check_config -c ~/.ha-dev/haclaw
```

Both must pass.

- [ ] **Step 5: If any small fixes were needed, commit them**

```bash
git status
# If modifications:
git add -A
git commit -m "chore: final verification fixes"
```

---

## Notes for the executing engineer

- **Frequent commits**: every task ends with a commit. Don't batch multiple tasks into one commit.
- **TDD**: always run failing test first to confirm it fails for the right reason, then implement, then run again.
- **Spec is the source of truth**: when in doubt, re-read `docs/superpowers/specs/2026-05-08-haclaw-chat-ui-design.md`. The follow-up `2026-05-08-haclaw-agent-loop-tools-design.md` is **out of scope** — do not implement anything from it.
- **Safety**: never bypass any of the safety claims in spec §3 / §14.2. If a step seems to ask you to take a credential or write to `.storage`, stop and re-read the spec — it's a misread.
- **Frontend** is one file (`haclaw-panel.js`). If it crosses 1200 lines, consider splitting into ES modules — but stay within scope; don't refactor existing logic that's already working.
- **HA dev environment**: `scripts/setup_ha_dev_env.sh` if `~/.venvs/haclaw-ha` doesn't exist. Tests run against `pytest-homeassistant-custom-component`.
- **WS commands** require HA to be restarted on first registration; for incremental dev, restart `scripts/run_hass_dev.sh` after Task 13 / 14.
- **Frontend interpolation**: when a step shows interpolated values (`${userValue}`), use ``this._html`...`` so values are auto-escaped. For static fragments without `${}`, regular template literals are fine. **Never set `innerHTML` to an unescaped user/model string.**

---

## Self-review

**Spec coverage check** (each spec section → covered task):
- §1-§3 (background, goals, security): Task 1 (constants), §3 invariants enforced via Tasks 2/3/13 + acceptance Task 25
- §4 architecture: Tasks 5-14 cover all backend pieces; Tasks 15-24 cover frontend
- §5 frontend layout: Tasks 15 (skeleton), 24 (mobile)
- §6 message components: Tasks 16 (final_response), 17 (clarification), 18 (automation_draft), 19 (risk + tool_call)
- §7 backend chat: Tasks 5 (prompts), 6 (protocol), 7 (chat_session), 13 (WS chat)
- §8 environment readiness: Tasks 8 (detect), 11 (service), 20 (frontend card)
- §9 presence binding: Tasks 3 (storage), 10 (services), 21 (frontend card)
- §10 settings modal: Tasks 12 (switch_model), 23 (frontend modal)
- §11 conversation storage + ui_state: Tasks 4 (conversations), 2 (ui_state), 14 (WS list/clear)
- §12 missing_integrations: Task 9
- §17 mode selector: Tasks 5 (mode prompts), 6 (mode protocol filter), 22 (frontend persistence + execute warning), 15 (frontend chips)
- §18 asking-answer flow: Tasks 5 (prompt with workday/free-text rules), 17 (UX), 18 (rationale rendering)
- §19 install_prompt cross-agent: Tasks 8 (templates + render), 20 (modal in env card), 18 (button in draft card)

**Placeholder scan**: searched plan for "TBD", "TODO", "implement later", "fill in details" — none found. Each step has actual code/commands.

**Type consistency**: 
- `MODE_*` constants used consistently across `const.py`, `prompts.py`, `protocol.py`, `chat_session.py`
- `ProtocolError`, `ChatSessionError`, `BindingError` exception names used consistently
- `INSTALL_PROMPT_TEMPLATES`, `INTEGRATION_METADATA` referenced from both `tools/environment.py` and `tools/automation.py`
- WS command names match between `const.py` and frontend (`haclaw/chat`, `haclaw/conversations/list`, `haclaw/conversations/clear`)
- Service names match between `services.yaml`, `__init__.py`, `const.py`, and frontend `_callService` calls

If any check fails during execution, the engineer should re-read the relevant spec section and fix inline.
