"""Shared OpenAI-compatible chat completions client."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ProviderError(RuntimeError):
    """User-readable provider error that never includes secrets."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def normalize_chat_completions_url(base_url: str) -> str:
    """Normalize a root, versioned, or full endpoint into chat completions URL."""
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        raise ProviderError("invalid_base_url", "Base URL 不能为空。")

    if normalized.endswith("/chat/completions"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    return f"{normalized}/v1/chat/completions"


def redact_secret(secret: str | None) -> str:
    """Return a stable masked summary without exposing the full secret."""
    if not secret:
        return ""
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}...{secret[-4:]}"


@dataclass(slots=True)
class ChatCompletionResult:
    """Parsed chat completion result with optional usage metadata."""

    content: str
    usage: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OpenAICompatibleClient:
    """One client for OpenAI-compatible providers and gateways."""

    api_key: str
    base_url: str
    model: str
    timeout: int = 300
    custom_headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.api_key = self.api_key.strip()
        self.base_url = normalize_chat_completions_url(self.base_url)
        self.model = self.model.strip()
        if not self.model:
            raise ProviderError("invalid_model", "模型名称不能为空。")

    def build_payload(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Build an OpenAI-compatible chat completions payload."""
        if not isinstance(messages, list) or not messages:
            raise ProviderError("invalid_messages", "消息列表不能为空。")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        for key in (
            "temperature",
            "top_p",
            "max_tokens",
            "presence_penalty",
            "frequency_penalty",
            "response_format",
            "tools",
            "tool_choice",
            "stream",
        ):
            value = kwargs.get(key)
            if value is not None:
                payload[key] = value
        return payload

    def build_headers(self) -> dict[str, str]:
        """Build redaction-safe HTTP headers for a provider request."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        headers.update(self.custom_headers)
        return headers

    async def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        """Call an OpenAI-compatible chat completions endpoint."""
        result = await self.chat_with_usage(messages, **kwargs)
        return result.content

    async def chat_with_usage(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> ChatCompletionResult:
        """Call chat completions and preserve provider usage fields."""
        try:
            import aiohttp
        except ImportError as err:
            raise ProviderError(
                "missing_dependency",
                "运行 HAclaw 需要 aiohttp；Home Assistant 环境通常已内置。",
            ) from err

        allow_empty_response = bool(kwargs.pop("allow_empty_response", False))
        payload = self.build_payload(messages, **kwargs)
        timeout = aiohttp.ClientTimeout(total=self.timeout)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.base_url,
                    json=payload,
                    headers=self.build_headers(),
                ) as response:
                    response_data = await _read_json_response(response)
                    if response.status in (401, 403):
                        raise ProviderError("invalid_api_key", "API key 无效或无权限。")
                    if response.status == 404:
                        raise ProviderError("model_not_found", "模型不存在或 Base URL 不正确。")
                    if response.status == 429:
                        raise ProviderError("rate_limited", "Provider 当前限流，请稍后再试。")
                    if response.status >= 400:
                        raise ProviderError("provider_error", "Provider 返回错误响应。")
        except TimeoutError as err:
            raise ProviderError("timeout", "Provider 请求超时。") from err
        except aiohttp.ClientError as err:
            raise ProviderError("cannot_connect", "无法连接到 Provider Base URL。") from err

        return extract_chat_completion_result(
            response_data,
            allow_empty_response=allow_empty_response,
        )


def extract_chat_completion_result(
    response_data: dict[str, Any],
    *,
    allow_empty_response: bool = False,
) -> ChatCompletionResult:
    """Extract assistant content and optional usage from a chat response."""
    try:
        message = response_data["choices"][0]["message"]
        content = message["content"]
    except (KeyError, IndexError, TypeError) as err:
        raise ProviderError("invalid_response", "Provider 返回格式无法解析。") from err

    if not isinstance(content, str):
        raise ProviderError("invalid_response", "Provider 返回格式无法解析。")

    usage = response_data.get("usage")
    if not content.strip() and allow_empty_response:
        reasoning_content = message.get("reasoning_content")
        if isinstance(reasoning_content, str) and reasoning_content.strip():
            content = reasoning_content
        elif isinstance(usage, dict):
            content = ""

    if not content.strip() and not allow_empty_response:
        raise ProviderError("empty_response", "Provider 返回了空内容。")

    return ChatCompletionResult(
        content=content,
        usage=usage if isinstance(usage, dict) else {},
    )


async def _read_json_response(response: Any) -> dict[str, Any]:
    try:
        data = await response.json()
    except Exception as err:
        raise ProviderError("json_parse_error", "Provider 返回内容不是合法 JSON。") from err
    if not isinstance(data, dict):
        raise ProviderError("json_parse_error", "Provider 返回 JSON 不是对象。")
    return data
