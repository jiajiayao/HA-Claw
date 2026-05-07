import unittest

from custom_components.haclaw.agent.protocol import (
    ProtocolError,
    parse_agent_response,
)


class AgentProtocolTests(unittest.TestCase):
    def test_accepts_final_response_json(self):
        response = parse_agent_response(
            '{"type":"final_response","message":"已经打开客厅灯"}'
        )

        self.assertEqual(response["type"], "final_response")
        self.assertEqual(response["message"], "已经打开客厅灯")

    def test_rejects_prose_outside_json(self):
        with self.assertRaises(ProtocolError):
            parse_agent_response(
                '好的，下面是结果：{"type":"final_response","message":"完成"}'
            )

    def test_rejects_unknown_tool_call(self):
        with self.assertRaises(ProtocolError):
            parse_agent_response(
                '{"type":"tool_call","tool":"call_any_service","args":{}}',
                allowed_tools={"get_entity_state"},
            )

    def test_accepts_automation_draft_with_required_fields(self):
        response = parse_agent_response(
            """
            {
              "type": "automation_draft",
              "title": "晚上打开客厅灯",
              "description": "每天晚上 7 点打开客厅灯。",
              "automation": {
                "alias": "晚上打开客厅灯",
                "trigger": [],
                "condition": [],
                "action": [],
                "mode": "single"
              },
              "risk_level": "medium",
              "requires_confirmation": true
            }
            """
        )

        self.assertEqual(response["type"], "automation_draft")
        self.assertEqual(response["automation"]["alias"], "晚上打开客厅灯")


if __name__ == "__main__":
    unittest.main()
