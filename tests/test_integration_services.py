import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import yaml
import voluptuous as vol
from homeassistant.core import ServiceCall

import custom_components.haclaw as haclaw
from custom_components.haclaw.const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_MODEL,
    CONF_PROVIDER_PRESET,
    DOMAIN,
    SERVICE_APPROVE_AUTOMATION_DRAFT,
    SERVICE_BIND_PRESENCE_ENTITY,
    SERVICE_CREATE_AUTOMATION_DRAFT,
    SERVICE_GET_ENVIRONMENT_READINESS,
    SERVICE_GET_PRESENCE_BINDING,
    SERVICE_LIST_PRESENCE_CANDIDATES,
    SERVICE_SWITCH_MODEL,
    SERVICE_TEST_CONNECTION,
    WS_TYPE_CHAT,
    WS_TYPE_CONVERSATIONS_CLEAR,
    WS_TYPE_CONVERSATIONS_LIST,
)
from custom_components.haclaw.providers.openai_compatible import ChatCompletionResult


class FakeConfig:
    def __init__(self, root):
        self.root = Path(root)

    def path(self, *parts):
        return str(self.root.joinpath(*parts))


class FakeState:
    def __init__(self, entity_id, state="unknown", attributes=None):
        self.entity_id = entity_id
        self.state = state
        self.attributes = dict(attributes) if attributes else {}


class FakeStates:
    def __init__(self, entity_ids=()):
        self._by_id: dict[str, FakeState] = {}
        for item in entity_ids:
            state = item if isinstance(item, FakeState) else FakeState(item)
            self._by_id[state.entity_id] = state

    def async_all(self):
        return list(self._by_id.values())

    def get(self, entity_id):
        return self._by_id.get(entity_id)


class FakeServices:
    def __init__(self, existing=()):
        self._existing = set(existing)
        self.registered = {}

    def has_service(self, domain, service):
        return (domain, service) in self._existing

    def async_register(self, domain, service, handler, **kwargs):
        self.registered[(domain, service)] = (handler, kwargs)

    def async_remove(self, domain, service):
        self.registered.pop((domain, service), None)


class FakeEntry:
    def __init__(self, data=None, options=None):
        self.data = dict(data or {})
        self.options = dict(options or {})


class FakeConfigEntries:
    def __init__(self, entries_by_domain=None):
        self._by_domain: dict[str, list] = {
            domain: list(entries) for domain, entries in (entries_by_domain or {}).items()
        }
        self.update_calls: list[tuple] = []

    def async_entries(self, domain):
        return list(self._by_domain.get(domain, []))

    def async_update_entry(self, entry, *, options=None, data=None):
        self.update_calls.append((entry, options, data))
        if options is not None:
            entry.options = dict(options)
        if data is not None:
            entry.data = dict(data)


class FakeHass:
    def __init__(
        self, root, entity_ids=(), services=(),
        config_entries=None, entry=None,
    ):
        self.config = FakeConfig(root)
        self.data = {
            DOMAIN: {
                "entries": {
                    "entry-1": {
                        "entry": entry,
                        "provider": {
                            CONF_PROVIDER_PRESET: "xiaomi_mimo",
                            CONF_API_KEY: "sk-test-secret",
                            CONF_BASE_URL: "https://api.mimo-v2.com/v1",
                            CONF_MODEL: "mimo-v2-flash",
                        },
                    }
                },
                "services_registered": False,
                "panel_registered": False,
                "static_registered": False,
            }
        }
        self.states = FakeStates(entity_ids)
        self.services = FakeServices(services)
        self.config_entries = FakeConfigEntries(config_entries)

    async def async_add_executor_job(self, func, *args):
        return func(*args)


class FakeConnection:
    def __init__(self):
        self.results = []
        self.errors = []
        self.exceptions = []

    def send_result(self, msg_id, result):
        self.results.append((msg_id, result))

    def send_error(self, msg_id, code, message):
        self.errors.append((msg_id, code, message))

    def async_handle_exception(self, msg, err):
        self.exceptions.append((msg, err))


class FakeClient:
    async def chat_with_usage(self, *_args, **_kwargs):
        return ChatCompletionResult(
            content="pong",
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        )


class IntegrationServiceTests(unittest.IsolatedAsyncioTestCase):
    def test_registers_runtime_services(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            hass = FakeHass(tmp_dir)

            haclaw._async_register_services(hass)

            self.assertIn((DOMAIN, SERVICE_TEST_CONNECTION), hass.services.registered)
            self.assertIn(
                (DOMAIN, SERVICE_CREATE_AUTOMATION_DRAFT), hass.services.registered
            )
            self.assertIn(
                (DOMAIN, SERVICE_APPROVE_AUTOMATION_DRAFT), hass.services.registered
            )

    def test_registers_presence_services(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            hass = FakeHass(tmp_dir)

            haclaw._async_register_services(hass)

            self.assertIn(
                (DOMAIN, SERVICE_LIST_PRESENCE_CANDIDATES), hass.services.registered
            )
            self.assertIn(
                (DOMAIN, SERVICE_GET_PRESENCE_BINDING), hass.services.registered
            )
            self.assertIn(
                (DOMAIN, SERVICE_BIND_PRESENCE_ENTITY), hass.services.registered
            )

    async def test_bind_presence_rejects_wrong_domain(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            hass = FakeHass(tmp_dir)
            call = ServiceCall(
                hass, DOMAIN, SERVICE_BIND_PRESENCE_ENTITY,
                {"entity_id": "light.kitchen"},
            )
            response = await haclaw._async_handle_bind_presence_entity(call)
            self.assertFalse(response["success"])
            self.assertIn("domain", response["message"])

    async def test_bind_presence_rejects_missing_entity(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            hass = FakeHass(tmp_dir)
            call = ServiceCall(
                hass, DOMAIN, SERVICE_BIND_PRESENCE_ENTITY,
                {"entity_id": "person.ghost"},
            )
            response = await haclaw._async_handle_bind_presence_entity(call)
            self.assertFalse(response["success"])

    async def test_bind_persists_and_get_returns(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            person_state = FakeState(
                "person.jiajia", state="home",
                attributes={"friendly_name": "Jiajia"},
            )
            hass = FakeHass(tmp_dir, entity_ids=[person_state])
            bind_call = ServiceCall(
                hass, DOMAIN, SERVICE_BIND_PRESENCE_ENTITY,
                {"entity_id": "person.jiajia"},
            )
            bind_resp = await haclaw._async_handle_bind_presence_entity(bind_call)
            self.assertTrue(bind_resp["success"])

            get_call = ServiceCall(
                hass, DOMAIN, SERVICE_GET_PRESENCE_BINDING, {},
            )
            get_resp = await haclaw._async_handle_get_presence_binding(get_call)
            self.assertEqual(get_resp["me_person_entity_id"], "person.jiajia")

    async def test_list_presence_candidates_orders_persons_first(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tracker = FakeState(
                "device_tracker.phone", state="home",
                attributes={"friendly_name": "Phone"},
            )
            person = FakeState(
                "person.jiajia", state="not_home",
                attributes={"friendly_name": "Jiajia"},
            )
            hass = FakeHass(tmp_dir, entity_ids=[tracker, person])
            call = ServiceCall(
                hass, DOMAIN, SERVICE_LIST_PRESENCE_CANDIDATES, {},
            )
            response = await haclaw._async_handle_list_presence_candidates(call)
            ids = [c["id"] for c in response["candidates"]]
            self.assertEqual(ids[0], "person.jiajia")
            self.assertEqual(ids[1], "device_tracker.phone")

    def test_registers_get_environment_readiness_service(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            hass = FakeHass(tmp_dir)
            haclaw._async_register_services(hass)
            self.assertIn(
                (DOMAIN, SERVICE_GET_ENVIRONMENT_READINESS),
                hass.services.registered,
            )

    async def test_get_environment_readiness_returns_three_required(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            hass = FakeHass(tmp_dir)
            call = ServiceCall(
                hass, DOMAIN, SERVICE_GET_ENVIRONMENT_READINESS, {},
            )
            response = await haclaw._async_handle_get_environment_readiness(call)
            ids = [item["id"] for item in response["items"]]
            self.assertEqual(ids, ["provider", "device_tracker", "xiaomi_miot"])
            advanced_ids = [item["id"] for item in response["advanced"]]
            self.assertIn("hacs", advanced_ids)

    def test_registers_switch_model_service(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            hass = FakeHass(tmp_dir)
            haclaw._async_register_services(hass)
            self.assertIn(
                (DOMAIN, SERVICE_SWITCH_MODEL),
                hass.services.registered,
            )

    async def test_switch_model_updates_entry_options(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            entry = FakeEntry(
                data={CONF_MODEL: "old"}, options={CONF_MODEL: "old"},
            )
            hass = FakeHass(tmp_dir, entry=entry)
            call = ServiceCall(
                hass, DOMAIN, SERVICE_SWITCH_MODEL,
                {"model": "deepseek-coder"},
            )
            response = await haclaw._async_handle_switch_model(call)
            self.assertTrue(response["success"])
            self.assertEqual(entry.options[CONF_MODEL], "deepseek-coder")

    async def test_switch_model_rejects_empty(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            entry = FakeEntry(
                data={CONF_MODEL: "old"}, options={CONF_MODEL: "old"},
            )
            hass = FakeHass(tmp_dir, entry=entry)
            call = ServiceCall(
                hass, DOMAIN, SERVICE_SWITCH_MODEL, {"model": "  "},
            )
            response = await haclaw._async_handle_switch_model(call)
            self.assertFalse(response["success"])

    async def test_test_connection_returns_usage_without_secret(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            hass = FakeHass(tmp_dir)
            call = ServiceCall(hass, DOMAIN, SERVICE_TEST_CONNECTION, {})

            with patch.object(haclaw, "_build_provider_client", return_value=FakeClient()):
                response = await haclaw._async_handle_test_connection(call)

            self.assertTrue(response["success"])
            self.assertEqual(response["provider"], "Xiaomi MiMo")
            self.assertEqual(response["usage"]["total_tokens"], 2)
            self.assertNotIn("api_key", str(response).lower())

    async def test_create_and_approve_automation_draft(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            hass = FakeHass(
                tmp_dir,
                entity_ids={"light.living_room"},
                services={("light", "turn_on")},
            )
            create_call = ServiceCall(
                hass,
                DOMAIN,
                SERVICE_CREATE_AUTOMATION_DRAFT,
                {
                    "title": "晚上打开客厅灯",
                    "description": "草稿",
                    "automation": {
                        "alias": "晚上打开客厅灯",
                        "trigger": [{"platform": "time", "at": "19:00:00"}],
                        "action": [
                            {
                                "service": "light.turn_on",
                                "target": {"entity_id": "light.living_room"},
                            }
                        ],
                    },
                },
            )

            create_response = await haclaw._async_handle_create_automation_draft(
                create_call
            )
            draft_id = create_response["draft"]["id"]

            approve_call = ServiceCall(
                hass,
                DOMAIN,
                SERVICE_APPROVE_AUTOMATION_DRAFT,
                {"draft_id": draft_id},
            )
            approve_response = await haclaw._async_handle_approve_automation_draft(
                approve_call
            )

            automations_path = Path(tmp_dir) / "haclaw" / "automations.yaml"
            automations = yaml.safe_load(automations_path.read_text(encoding="utf-8"))
            self.assertTrue(create_response["success"])
            self.assertTrue(approve_response["success"])
            self.assertEqual(automations[0]["alias"], "晚上打开客厅灯")
            self.assertFalse(automations[0]["initial_state"])

    def test_registers_ws_chat_command(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            hass = FakeHass(tmp_dir)

            haclaw._async_register_ws_commands(hass)

            self.assertIn(WS_TYPE_CHAT, hass.data["websocket_api"])

    def test_registers_ws_conversations_commands(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            hass = FakeHass(tmp_dir)

            haclaw._async_register_ws_commands(hass)

            self.assertIn(WS_TYPE_CONVERSATIONS_LIST, hass.data["websocket_api"])
            self.assertIn(WS_TYPE_CONVERSATIONS_CLEAR, hass.data["websocket_api"])

    async def test_ws_chat_returns_final_response(self):
        handler = getattr(haclaw, "_async_handle_ws_chat", None)
        self.assertIsNotNone(handler)
        with tempfile.TemporaryDirectory() as tmp_dir:
            purifier = FakeState(
                "fan.mi_air_purifier",
                state="off",
                attributes={"friendly_name": "米家空气净化器"},
            )
            hass = FakeHass(tmp_dir, entity_ids=[purifier])
            connection = FakeConnection()
            fake = {
                "conversation_id": "c1",
                "assistant_message": {"type": "final_response", "message": "hi"},
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                "model": "mimo",
            }

            with (
                patch.object(haclaw, "_build_provider_client", return_value=FakeClient()),
                patch.object(
                    haclaw,
                    "run_single_turn",
                    new=AsyncMock(return_value=fake),
                    create=True,
                ) as run_turn,
            ):
                await handler.__wrapped__(
                    hass,
                    connection,
                    {
                        "id": 1,
                        "type": WS_TYPE_CHAT,
                        "conversation_id": "c1",
                        "user_message": "生成晚 7 点开净化器的自动化",
                        "mode": "automation",
                    },
                )

            self.assertEqual(connection.errors, [])
            self.assertEqual(connection.results, [(1, fake)])
            run_turn.assert_awaited_once()
            kwargs = run_turn.await_args.kwargs
            self.assertIn("米家空气净化器", kwargs["entity_context"])
            self.assertEqual(kwargs["entity_candidates"][0]["id"], "fan.mi_air_purifier")
            self.assertTrue(kwargs["has_controllable_entities"])

    async def test_ws_chat_appends_metadata_only_audit_entry(self):
        handler = getattr(haclaw, "_async_handle_ws_chat", None)
        self.assertIsNotNone(handler)
        with tempfile.TemporaryDirectory() as tmp_dir:
            hass = FakeHass(tmp_dir)
            connection = FakeConnection()
            fake = {
                "conversation_id": "c1",
                "assistant_message": {
                    "type": "final_response",
                    "message": "assistant secret body",
                },
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                "model": "mimo",
            }

            with (
                patch.object(haclaw, "_build_provider_client", return_value=FakeClient()),
                patch.object(
                    haclaw,
                    "run_single_turn",
                    new=AsyncMock(return_value=fake),
                    create=True,
                ),
            ):
                await handler.__wrapped__(
                    hass,
                    connection,
                    {
                        "id": 1,
                        "type": WS_TYPE_CHAT,
                        "conversation_id": "c1",
                        "user_message": "用户消息正文",
                        "mode": "automation",
                    },
                )

            audit_path = Path(tmp_dir) / "haclaw" / "audit_log.jsonl"
            audit_text = audit_path.read_text(encoding="utf-8")
            audit_entry = json.loads(audit_text.strip().splitlines()[-1])
            self.assertEqual(audit_entry["tool"], "chat")
            self.assertEqual(audit_entry["mode"], "automation")
            self.assertEqual(audit_entry["model"], "mimo-v2-flash")
            self.assertEqual(audit_entry["result"], "final_response")
            self.assertNotIn("用户消息正文", audit_text)
            self.assertNotIn("assistant secret body", audit_text)

    def test_ws_chat_schema_rejects_invalid_mode(self):
        handler = getattr(haclaw, "_async_handle_ws_chat", None)
        self.assertIsNotNone(handler)

        with self.assertRaises(vol.Invalid):
            handler._ws_schema(
                {
                    "id": 2,
                    "type": WS_TYPE_CHAT,
                    "conversation_id": "c1",
                    "user_message": "hi",
                    "mode": "garbage",
                }
            )

    async def test_ws_conversations_list_returns_summary(self):
        handler = getattr(haclaw, "_async_handle_ws_conversations_list", None)
        self.assertIsNotNone(handler)
        with tempfile.TemporaryDirectory() as tmp_dir:
            from custom_components.haclaw.storage.conversations import append_message

            hass = FakeHass(tmp_dir)
            connection = FakeConnection()
            convs_path = Path(tmp_dir) / "haclaw" / "conversations.json"
            append_message(convs_path, "c1", {"role": "user", "content": "hi"})

            await handler.__wrapped__(
                hass,
                connection,
                {"id": 1, "type": WS_TYPE_CONVERSATIONS_LIST},
            )

            self.assertEqual(connection.errors, [])
            self.assertEqual(connection.results[0][0], 1)
            summary = connection.results[0][1]["conversations"][0]
            self.assertEqual(summary["id"], "c1")
            self.assertEqual(summary["message_count"], 1)

    async def test_ws_conversations_clear_specific(self):
        handler = getattr(haclaw, "_async_handle_ws_conversations_clear", None)
        self.assertIsNotNone(handler)
        with tempfile.TemporaryDirectory() as tmp_dir:
            from custom_components.haclaw.storage.conversations import (
                append_message,
                load_conversation,
            )

            hass = FakeHass(tmp_dir)
            connection = FakeConnection()
            convs_path = Path(tmp_dir) / "haclaw" / "conversations.json"
            append_message(convs_path, "c1", {"role": "user", "content": "hi"})
            append_message(convs_path, "c2", {"role": "user", "content": "keep"})

            await handler.__wrapped__(
                hass,
                connection,
                {
                    "id": 2,
                    "type": WS_TYPE_CONVERSATIONS_CLEAR,
                    "conversation_id": "c1",
                },
            )

            self.assertEqual(connection.errors, [])
            self.assertEqual(connection.results, [(2, {"success": True})])
            self.assertEqual(load_conversation(convs_path, "c1")["messages"], [])
            self.assertEqual(len(load_conversation(convs_path, "c2")["messages"]), 1)


if __name__ == "__main__":
    unittest.main()
