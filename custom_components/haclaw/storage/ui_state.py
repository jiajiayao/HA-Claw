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
