"""Base provider contracts."""

from __future__ import annotations

from typing import Any, Protocol


class BaseChatClient(Protocol):
    """Minimal async chat client interface used by HAclaw."""

    async def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        """Return assistant text for a chat completion request."""
        raise NotImplementedError
