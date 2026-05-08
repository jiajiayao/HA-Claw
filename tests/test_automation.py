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


if __name__ == "__main__":
    unittest.main()
