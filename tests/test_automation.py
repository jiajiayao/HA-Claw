import unittest

from custom_components.haclaw.tools.automation import (
    extract_entity_ids,
    extract_service_calls,
    validate_automation_draft,
)


class AutomationDraftTests(unittest.TestCase):
    def test_valid_draft_is_disabled_by_default(self):
        result = validate_automation_draft(
            {
                "alias": "晚上打开客厅灯",
                "trigger": [{"platform": "time", "at": "19:00:00"}],
                "action": [
                    {
                        "service": "light.turn_on",
                        "target": {"entity_id": "light.living_room"},
                    }
                ],
            },
            known_entity_ids={"light.living_room"},
            service_exists=lambda domain, service: (domain, service)
            == ("light", "turn_on"),
        )

        self.assertTrue(result.valid)
        self.assertFalse(result.automation["initial_state"])
        self.assertEqual(result.automation["mode"], "single")
        self.assertEqual(result.risk_level, "low")

    def test_missing_alias_is_rejected(self):
        result = validate_automation_draft(
            {
                "trigger": [],
                "action": [],
            }
        )

        self.assertFalse(result.valid)
        self.assertIn("automation.alias is required.", result.errors)

    def test_unknown_entity_is_rejected(self):
        result = validate_automation_draft(
            {
                "alias": "打开不存在的灯",
                "trigger": [],
                "action": [
                    {
                        "service": "light.turn_on",
                        "target": {"entity_id": "light.missing"},
                    }
                ],
            },
            known_entity_ids={"light.living_room"},
        )

        self.assertFalse(result.valid)
        self.assertIn("unknown entity_id: light.missing.", result.errors)

    def test_dangerous_action_is_flagged(self):
        result = validate_automation_draft(
            {
                "alias": "自动开门",
                "trigger": [],
                "action": [
                    {
                        "service": "lock.unlock",
                        "target": {"entity_id": "lock.front_door"},
                    }
                ],
            },
            known_entity_ids={"lock.front_door"},
            service_exists=lambda domain, service: (domain, service)
            == ("lock", "unlock"),
        )

        self.assertTrue(result.valid)
        self.assertEqual(result.risk_level, "high")
        self.assertTrue(result.requires_confirmation)

    def test_blocked_shell_command_is_rejected(self):
        result = validate_automation_draft(
            {
                "alias": "运行脚本",
                "trigger": [],
                "action": [{"service": "shell_command.backup_config"}],
            },
            service_exists=lambda _domain, _service: True,
        )

        self.assertFalse(result.valid)
        self.assertIn("blocked service: shell_command.backup_config.", result.errors)

    def test_extractors_handle_modern_action_key(self):
        automation = {
            "alias": "动作语法",
            "trigger": [],
            "action": [
                {
                    "action": "light.turn_on",
                    "target": {"entity_id": ["light.a", "light.b"]},
                }
            ],
        }

        self.assertEqual(extract_entity_ids(automation), {"light.a", "light.b"})
        self.assertEqual(extract_service_calls(automation)[0].key, "light.turn_on")


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


if __name__ == "__main__":
    unittest.main()
