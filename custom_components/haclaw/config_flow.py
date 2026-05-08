"""Config flow for HAclaw."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_BASE_URL,
    CONF_MODEL,
    CONF_PROVIDER_PRESET,
    CONF_TIMEOUT,
    DEFAULT_TIMEOUT,
    DOMAIN,
    PROVIDER_PRESETS,
)
from .providers.openai_compatible import OpenAICompatibleClient, ProviderError


def _provider_options() -> list[SelectOptionDict]:
    return [
        SelectOptionDict(value=key, label=value["name"])
        for key, value in PROVIDER_PRESETS.items()
    ]


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PROVIDER_PRESET, default="deepseek"): SelectSelector(
            SelectSelectorConfig(options=_provider_options())
        ),
        vol.Required(CONF_API_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Required(
            CONF_BASE_URL,
            default=PROVIDER_PRESETS["deepseek"]["base_url"],
        ): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
        vol.Required(
            CONF_MODEL,
            default=PROVIDER_PRESETS["deepseek"]["model"],
        ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): NumberSelector(
            NumberSelectorConfig(
                min=5,
                max=600,
                mode=NumberSelectorMode.BOX,
                unit_of_measurement="s",
            )
        ),
    }
)


class HAclawConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HAclaw."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HAclawOptionsFlowHandler:
        """Create the options flow."""
        return HAclawOptionsFlowHandler(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = _normalize_user_input(user_input)
            try:
                await _async_validate_provider(data)
            except ProviderError as err:
                errors["base"] = err.code
            else:
                return self.async_create_entry(title="HAclaw", data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, user_input
            ),
            errors=errors,
        )


def _normalize_user_input(user_input: dict[str, Any]) -> dict[str, Any]:
    return {
        CONF_PROVIDER_PRESET: str(user_input[CONF_PROVIDER_PRESET]).strip(),
        CONF_API_KEY: str(user_input[CONF_API_KEY]).strip(),
        CONF_BASE_URL: str(user_input[CONF_BASE_URL]).strip(),
        CONF_MODEL: str(user_input[CONF_MODEL]).strip(),
        CONF_TIMEOUT: int(user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)),
    }


async def _async_validate_provider(data: dict[str, Any]) -> None:
    client = OpenAICompatibleClient(
        api_key=data[CONF_API_KEY],
        base_url=data[CONF_BASE_URL],
        model=data[CONF_MODEL],
        timeout=min(data[CONF_TIMEOUT], 30),
    )
    await client.chat(
        [{"role": "user", "content": "请直接输出：pong"}],
        temperature=0,
        max_tokens=128,
        allow_empty_response=True,
    )


class HAclawOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle editable HAclaw provider settings."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage HAclaw provider options."""
        errors: dict[str, str] = {}
        current = {
            **self._config_entry.data,
            **self._config_entry.options,
        }

        if user_input is not None:
            data = _normalize_user_input(user_input)
            try:
                await _async_validate_provider(data)
            except ProviderError as err:
                errors["base"] = err.code
            else:
                return self.async_create_entry(title="", data=data)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, current
            ),
            errors=errors,
        )
