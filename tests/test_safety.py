import unittest

from custom_components.haclaw.agent.safety import evaluate_service_call


class SafetyTests(unittest.TestCase):
    def test_light_turn_on_is_allowed_low_risk(self):
        decision = evaluate_service_call("light", "turn_on")

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.risk_level, "low")
        self.assertFalse(decision.requires_confirmation)

    def test_lock_unlock_requires_confirmation(self):
        decision = evaluate_service_call("lock", "unlock")

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.risk_level, "high")
        self.assertTrue(decision.requires_confirmation)

    def test_alarm_disarm_requires_confirmation(self):
        decision = evaluate_service_call("alarm_control_panel", "alarm_disarm")

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.risk_level, "high")
        self.assertTrue(decision.requires_confirmation)

    def test_shell_command_is_blocked(self):
        decision = evaluate_service_call("shell_command", "backup_config")

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.risk_level, "critical")
        self.assertTrue(decision.blocked)

    def test_xiaomi_cloud_api_request_is_blocked(self):
        decision = evaluate_service_call("xiaomi_miot", "request_xiaomi_api")

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.risk_level, "critical")
        self.assertTrue(decision.blocked)


if __name__ == "__main__":
    unittest.main()
