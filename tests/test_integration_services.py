import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from homeassistant.core import ServiceCall

import custom_components.haclaw as haclaw
from custom_components.haclaw.const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_MODEL,
    CONF_PROVIDER_PRESET,
    DOMAIN,
    SERVICE_APPROVE_AUTOMATION_DRAFT,
    SERVICE_CREATE_AUTOMATION_DRAFT,
    SERVICE_TEST_CONNECTION,
)
from custom_components.haclaw.providers.openai_compatible import ChatCompletionResult


class FakeConfig:
    def __init__(self, root):
        self.root = Path(root)

    def path(self, *parts):
        return str(self.root.joinpath(*parts))


class FakeState:
    def __init__(self, entity_id):
        self.entity_id = entity_id


class FakeStates:
    def __init__(self, entity_ids):
        self._states = [FakeState(entity_id) for entity_id in entity_ids]

    def async_all(self):
        return list(self._states)


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


class FakeHass:
    def __init__(self, root, entity_ids=(), services=()):
        self.config = FakeConfig(root)
        self.data = {
            DOMAIN: {
                "entries": {
                    "entry-1": {
                        "provider": {
                            CONF_PROVIDER_PRESET: "xiaomi_mimo",
                            CONF_API_KEY: "sk-test-secret",
                            CONF_BASE_URL: "https://api.mimo-v2.com/v1",
                            CONF_MODEL: "mimo-v2-flash",
                        }
                    }
                },
                "services_registered": False,
                "panel_registered": False,
                "static_registered": False,
            }
        }
        self.states = FakeStates(entity_ids)
        self.services = FakeServices(services)

    async def async_add_executor_job(self, func, *args):
        return func(*args)


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


if __name__ == "__main__":
    unittest.main()
