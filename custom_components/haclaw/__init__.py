"""HAclaw integration entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .agent.chat_session import ChatSessionError, run_single_turn
from .const import (
    AUDIT_LOG_FILE,
    AUTOMATIONS_FILE,
    ALL_MODES,
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_MODEL,
    CONF_PROVIDER_PRESET,
    CONF_TIMEOUT,
    CONVERSATIONS_FILE,
    DEFAULT_TIMEOUT,
    DEFAULT_MODE,
    DOMAIN,
    DRAFTS_FILE,
    FRONTEND_PANEL_JS,
    FRONTEND_STATIC_URL,
    FRONTEND_URL_PATH,
    PRESENCE_FILE,
    PROVIDER_PRESETS,
    SERVICE_APPROVE_AUTOMATION_DRAFT,
    SERVICE_BIND_PRESENCE_ENTITY,
    SERVICE_CREATE_AUTOMATION_DRAFT,
    SERVICE_GET_ENVIRONMENT_READINESS,
    SERVICE_GET_PRESENCE_BINDING,
    SERVICE_LIST_PRESENCE_CANDIDATES,
    SERVICE_SWITCH_MODEL,
    SERVICE_TEST_CONNECTION,
    STORAGE_DIR,
    UI_STATE_FILE,
    WS_TYPE_CHAT,
    WS_TYPE_CONVERSATIONS_CLEAR,
    WS_TYPE_CONVERSATIONS_LIST,
)
from .providers.openai_compatible import OpenAICompatibleClient, ProviderError
from .storage.audit_log import append_audit_event
from .storage.conversations import clear_all, clear_conversation, list_conversations
from .storage.drafts import (
    DraftStorageError,
    append_automation,
    append_draft,
    create_automation_draft_record,
    get_draft,
    load_automation_aliases,
    load_draft_aliases,
    mark_draft_approved,
)
from .storage.presence import (
    BindingError,
    list_candidates,
    load_binding,
    save_binding,
)
from .storage.ui_state import load_state
from .tools.automation import validate_automation_draft
from .tools.entity import (
    build_entity_context,
    find_entity_candidates,
    list_controllable_entities,
)
from .tools.environment import detect_environment_readiness

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


TEST_CONNECTION_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): cv.string,
    }
)

CREATE_AUTOMATION_DRAFT_SCHEMA = vol.Schema(
    {
        vol.Required("title"): cv.string,
        vol.Optional("description", default=""): cv.string,
        vol.Required("automation"): dict,
        vol.Optional("source", default="service"): cv.string,
    }
)

APPROVE_AUTOMATION_DRAFT_SCHEMA = vol.Schema(
    {
        vol.Required("draft_id"): cv.string,
        vol.Optional("confirmed", default=False): cv.boolean,
    }
)

LIST_PRESENCE_CANDIDATES_SCHEMA = vol.Schema({})
GET_PRESENCE_BINDING_SCHEMA = vol.Schema({})
BIND_PRESENCE_ENTITY_SCHEMA = vol.Schema({vol.Required("entity_id"): cv.string})
GET_ENVIRONMENT_READINESS_SCHEMA = vol.Schema({})
SWITCH_MODEL_SCHEMA = vol.Schema({vol.Required("model"): cv.string})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HAclaw from a config entry."""
    domain_data = _domain_data(hass)
    provider = _provider_config_from_entry(entry)
    domain_data["entries"][entry.entry_id] = {
        "entry": entry,
        "provider": provider,
    }

    _async_register_services(hass)
    _async_register_ws_commands(hass)
    await _async_register_frontend(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a HAclaw config entry."""
    domain_data = hass.data.get(DOMAIN)
    if domain_data is None:
        return True

    domain_data.get("entries", {}).pop(entry.entry_id, None)
    if domain_data.get("entries"):
        return True

    _async_remove_services(hass)
    frontend.async_remove_panel(hass, FRONTEND_URL_PATH, warn_if_unknown=False)
    domain_data["panel_registered"] = False
    return True


def _domain_data(hass: HomeAssistant) -> dict[str, Any]:
    return hass.data.setdefault(
        DOMAIN,
        {
            "entries": {},
            "services_registered": False,
            "ws_registered": False,
            "panel_registered": False,
            "static_registered": False,
        },
    )


def _provider_config_from_entry(entry: ConfigEntry) -> dict[str, Any]:
    return {
        **dict(entry.data),
        **dict(entry.options),
    }


def _async_register_services(hass: HomeAssistant) -> None:
    domain_data = _domain_data(hass)
    if domain_data["services_registered"]:
        return

    hass.services.async_register(
        DOMAIN,
        SERVICE_TEST_CONNECTION,
        _async_handle_test_connection,
        schema=TEST_CONNECTION_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_AUTOMATION_DRAFT,
        _async_handle_create_automation_draft,
        schema=CREATE_AUTOMATION_DRAFT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_APPROVE_AUTOMATION_DRAFT,
        _async_handle_approve_automation_draft,
        schema=APPROVE_AUTOMATION_DRAFT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_PRESENCE_CANDIDATES,
        _async_handle_list_presence_candidates,
        schema=LIST_PRESENCE_CANDIDATES_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PRESENCE_BINDING,
        _async_handle_get_presence_binding,
        schema=GET_PRESENCE_BINDING_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_BIND_PRESENCE_ENTITY,
        _async_handle_bind_presence_entity,
        schema=BIND_PRESENCE_ENTITY_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_ENVIRONMENT_READINESS,
        _async_handle_get_environment_readiness,
        schema=GET_ENVIRONMENT_READINESS_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SWITCH_MODEL,
        _async_handle_switch_model,
        schema=SWITCH_MODEL_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    domain_data["services_registered"] = True


def _async_remove_services(hass: HomeAssistant) -> None:
    domain_data = _domain_data(hass)
    if not domain_data["services_registered"]:
        return

    for service in (
        SERVICE_TEST_CONNECTION,
        SERVICE_CREATE_AUTOMATION_DRAFT,
        SERVICE_APPROVE_AUTOMATION_DRAFT,
        SERVICE_LIST_PRESENCE_CANDIDATES,
        SERVICE_GET_PRESENCE_BINDING,
        SERVICE_BIND_PRESENCE_ENTITY,
        SERVICE_GET_ENVIRONMENT_READINESS,
        SERVICE_SWITCH_MODEL,
    ):
        hass.services.async_remove(DOMAIN, service)
    domain_data["services_registered"] = False


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_CHAT,
        vol.Required("conversation_id"): str,
        vol.Required("user_message"): str,
        vol.Optional("mode", default=DEFAULT_MODE): vol.In(ALL_MODES),
    }
)
@websocket_api.async_response
async def _async_handle_ws_chat(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        provider = _get_provider_config(hass)
        client = _build_provider_client(provider)
        entity_context = build_entity_context(hass)
        entity_candidates = find_entity_candidates(hass, msg["user_message"])
        has_controllable_entities = bool(list_controllable_entities(hass, limit=1))
        result = await run_single_turn(
            conversations_path=_storage_path(hass, CONVERSATIONS_FILE),
            ui_state_path=_storage_path(hass, UI_STATE_FILE),
            presence_path=_storage_path(hass, PRESENCE_FILE),
            conversation_id=msg["conversation_id"],
            user_message=msg["user_message"],
            mode=msg.get("mode", DEFAULT_MODE),
            provider_client=client,
            model_name=str(provider.get(CONF_MODEL, "")),
            entity_context=entity_context,
            has_controllable_entities=has_controllable_entities,
            entity_candidates=entity_candidates,
        )
    except ChatSessionError as err:
        connection.send_error(msg["id"], "haclaw_chat_error", str(err))
        return
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "haclaw_config_error", str(err))
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_CONVERSATIONS_LIST,
    }
)
@websocket_api.async_response
async def _async_handle_ws_conversations_list(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    convs = await hass.async_add_executor_job(
        list_conversations,
        _storage_path(hass, CONVERSATIONS_FILE),
    )
    summary = [
        {
            "id": conv["id"],
            "created_at": conv.get("created_at"),
            "updated_at": conv.get("updated_at"),
            "message_count": len(conv.get("messages", [])),
        }
        for conv in convs
    ]
    connection.send_result(msg["id"], {"conversations": summary})


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_CONVERSATIONS_CLEAR,
        vol.Optional("conversation_id"): str,
    }
)
@websocket_api.async_response
async def _async_handle_ws_conversations_clear(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    conversations_path = _storage_path(hass, CONVERSATIONS_FILE)
    if msg.get("conversation_id"):
        await hass.async_add_executor_job(
            clear_conversation,
            conversations_path,
            msg["conversation_id"],
        )
    else:
        await hass.async_add_executor_job(clear_all, conversations_path)
    connection.send_result(msg["id"], {"success": True})


def _async_register_ws_commands(hass: HomeAssistant) -> None:
    domain_data = _domain_data(hass)
    if domain_data.get("ws_registered", False):
        return

    websocket_api.async_register_command(hass, _async_handle_ws_chat)
    websocket_api.async_register_command(hass, _async_handle_ws_conversations_list)
    websocket_api.async_register_command(hass, _async_handle_ws_conversations_clear)
    domain_data["ws_registered"] = True


async def _async_register_frontend(hass: HomeAssistant) -> None:
    domain_data = _domain_data(hass)
    if domain_data["panel_registered"]:
        return

    if not domain_data["static_registered"]:
        frontend_dir = Path(__file__).parent / "frontend"
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    FRONTEND_STATIC_URL,
                    str(frontend_dir),
                    cache_headers=False,
                )
            ]
        )
        domain_data["static_registered"] = True

    if not frontend.async_panel_exists(hass, FRONTEND_URL_PATH):
        await panel_custom.async_register_panel(
            hass=hass,
            frontend_url_path=FRONTEND_URL_PATH,
            webcomponent_name="haclaw-panel",
            sidebar_title="HAclaw",
            sidebar_icon="mdi:robot-happy-outline",
            module_url=f"{FRONTEND_STATIC_URL}/{FRONTEND_PANEL_JS}",
            embed_iframe=False,
            require_admin=False,
            config_panel_domain=DOMAIN,
            config={"domain": DOMAIN},
        )
    domain_data["panel_registered"] = True


async def _async_handle_test_connection(call: ServiceCall) -> dict[str, Any]:
    hass = call.hass
    provider = _get_provider_config(hass, call.data.get("entry_id"))
    provider_preset = str(provider.get(CONF_PROVIDER_PRESET, "custom"))
    provider_name = PROVIDER_PRESETS.get(provider_preset, {}).get(
        "name", provider_preset
    )

    try:
        client = _build_provider_client(provider)
        result = await client.chat_with_usage(
            [{"role": "user", "content": "请直接输出：pong"}],
            temperature=0,
            max_tokens=128,
            allow_empty_response=True,
        )
    except ProviderError as err:
        response = {
            "success": False,
            "code": err.code,
            "message": err.message,
            "provider": provider_name,
            "model": provider.get(CONF_MODEL, ""),
        }
    else:
        response = {
            "success": True,
            "message": "Provider 连接成功。",
            "provider": provider_name,
            "model": provider.get(CONF_MODEL, ""),
            "usage": result.usage,
        }

    await _async_append_audit(
        hass,
        {
            "tool": SERVICE_TEST_CONNECTION,
            "model_provider": provider_preset,
            "model": provider.get(CONF_MODEL, ""),
            "result": "success" if response["success"] else response["code"],
        },
    )
    return response


async def _async_handle_create_automation_draft(call: ServiceCall) -> dict[str, Any]:
    hass = call.hass
    drafts_path = _storage_path(hass, DRAFTS_FILE)
    automations_path = _storage_path(hass, AUTOMATIONS_FILE)

    try:
        existing_aliases = await _async_load_existing_aliases(
            hass, drafts_path, automations_path
        )
    except DraftStorageError as err:
        raise HomeAssistantError(str(err)) from err

    validation = validate_automation_draft(
        call.data["automation"],
        known_entity_ids=_known_entity_ids(hass),
        service_exists=hass.services.has_service,
        existing_aliases=existing_aliases,
    )
    if not validation.valid:
        return {
            "success": False,
            "message": "自动化草稿校验失败。",
            "errors": validation.errors,
            "warnings": validation.warnings,
            "risk_level": validation.risk_level,
            "requires_confirmation": validation.requires_confirmation,
        }

    draft = create_automation_draft_record(
        title=call.data["title"],
        description=call.data.get("description", ""),
        validation=validation,
        source=call.data.get("source", "service"),
    )
    try:
        await hass.async_add_executor_job(append_draft, drafts_path, draft)
    except DraftStorageError as err:
        raise HomeAssistantError(str(err)) from err

    await _async_append_audit(
        hass,
        {
            "tool": SERVICE_CREATE_AUTOMATION_DRAFT,
            "risk_level": draft["risk_level"],
            "requires_confirmation": draft["requires_confirmation"],
            "approved": False,
            "result": "draft_created",
            "draft_id": draft["id"],
        },
    )
    return {
        "success": True,
        "message": "自动化草稿已保存，默认不会启用。",
        "draft": draft,
    }


async def _async_handle_approve_automation_draft(call: ServiceCall) -> dict[str, Any]:
    hass = call.hass
    draft_id = str(call.data["draft_id"]).strip()
    drafts_path = _storage_path(hass, DRAFTS_FILE)
    automations_path = _storage_path(hass, AUTOMATIONS_FILE)

    try:
        draft = await hass.async_add_executor_job(get_draft, drafts_path, draft_id)
    except DraftStorageError as err:
        raise HomeAssistantError(str(err)) from err

    if draft is None:
        return {"success": False, "message": "未找到这个自动化草稿。"}

    if draft.get("approved"):
        return {
            "success": True,
            "message": "这个草稿已经审批过。",
            "draft_id": draft_id,
            "path": str(automations_path),
        }

    if draft.get("requires_confirmation") and not call.data.get("confirmed", False):
        return {
            "success": False,
            "message": "这个草稿包含风险操作，需要显式确认后才能写入。",
            "risk_level": draft.get("risk_level", "medium"),
            "requires_confirmation": True,
        }

    validation = validate_automation_draft(
        draft["automation"],
        known_entity_ids=_known_entity_ids(hass),
        service_exists=hass.services.has_service,
        existing_aliases=await hass.async_add_executor_job(
            load_automation_aliases, automations_path
        ),
    )
    if not validation.valid:
        return {
            "success": False,
            "message": "审批前复核失败，未写入自动化文件。",
            "errors": validation.errors,
            "warnings": validation.warnings,
        }

    try:
        await hass.async_add_executor_job(
            append_automation,
            automations_path,
            validation.automation,
        )
        await hass.async_add_executor_job(mark_draft_approved, drafts_path, draft_id)
    except DraftStorageError as err:
        raise HomeAssistantError(str(err)) from err

    await _async_append_audit(
        hass,
        {
            "tool": SERVICE_APPROVE_AUTOMATION_DRAFT,
            "risk_level": validation.risk_level,
            "requires_confirmation": validation.requires_confirmation,
            "approved": True,
            "result": "automation_written",
            "draft_id": draft_id,
        },
    )
    return {
        "success": True,
        "message": "自动化已写入 HAclaw 管理文件，默认保持禁用。",
        "draft_id": draft_id,
        "path": str(automations_path),
        "automation": validation.automation,
    }


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

    await _async_append_audit(
        hass,
        {
            "tool": SERVICE_BIND_PRESENCE_ENTITY,
            "result": "presence_bound",
            "entity_id": entity_id,
        },
    )
    return {"success": True, "me_person_entity_id": entity_id}


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


async def _async_handle_switch_model(call: ServiceCall) -> dict[str, Any]:
    hass = call.hass
    new_model = call.data["model"].strip()
    if not new_model:
        return {"success": False, "message": "model 不能为空"}

    entries = _domain_data(hass)["entries"]
    if not entries:
        return {"success": False, "message": "尚未配置 HAclaw entry"}
    entry_state = next(iter(entries.values()))
    entry = entry_state.get("entry")
    if entry is None:
        return {"success": False, "message": "尚未配置 HAclaw entry"}

    new_options = dict(entry.options)
    new_options[CONF_MODEL] = new_model
    hass.config_entries.async_update_entry(entry, options=new_options)
    entry_state["provider"] = {**dict(entry.data), **new_options}

    return {"success": True, "model": new_model}


def _get_provider_config(
    hass: HomeAssistant,
    entry_id: str | None = None,
) -> dict[str, Any]:
    entries = _domain_data(hass)["entries"]
    if not entries:
        raise HomeAssistantError("HAclaw has no configured provider.")

    if entry_id:
        entry_state = entries.get(entry_id)
        if entry_state is None:
            raise HomeAssistantError(f"HAclaw config entry does not exist: {entry_id}.")
    else:
        entry_state = next(iter(entries.values()))
    return dict(entry_state["provider"])


def _build_provider_client(provider: dict[str, Any]) -> OpenAICompatibleClient:
    return OpenAICompatibleClient(
        api_key=str(provider.get(CONF_API_KEY, "")),
        base_url=str(provider.get(CONF_BASE_URL, "")),
        model=str(provider.get(CONF_MODEL, "")),
        timeout=min(int(provider.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)), 30),
    )


def _known_entity_ids(hass: HomeAssistant) -> set[str]:
    return {state.entity_id for state in hass.states.async_all()}


async def _async_load_existing_aliases(
    hass: HomeAssistant,
    drafts_path: Path,
    automations_path: Path,
) -> set[str]:
    draft_aliases = await hass.async_add_executor_job(load_draft_aliases, drafts_path)
    automation_aliases = await hass.async_add_executor_job(
        load_automation_aliases, automations_path
    )
    return draft_aliases | automation_aliases


async def _async_append_audit(hass: HomeAssistant, event: dict[str, Any]) -> None:
    await hass.async_add_executor_job(
        append_audit_event,
        _storage_path(hass, AUDIT_LOG_FILE),
        event,
    )


def _storage_path(hass: HomeAssistant, filename: str) -> Path:
    return Path(hass.config.path(STORAGE_DIR, filename))
