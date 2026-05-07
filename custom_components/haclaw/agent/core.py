"""Core agent loop primitives.

The full HA runtime loop will be built around this module. Keep this file
small until the protocol validator, tool registry, and safety checks have more
coverage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .protocol import parse_agent_response


DEFAULT_MAX_ITERATIONS = 5


@dataclass(slots=True)
class AgentTurnResult:
    """Validated model output for one agent turn."""

    response: dict[str, Any]
    iterations_used: int


def validate_single_turn(
    raw_model_output: str,
    *,
    allowed_tools: set[str] | None = None,
) -> AgentTurnResult:
    """Validate one model output without executing any tools."""
    return AgentTurnResult(
        response=parse_agent_response(raw_model_output, allowed_tools=allowed_tools),
        iterations_used=1,
    )
