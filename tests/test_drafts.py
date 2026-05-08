import tempfile
import unittest
from pathlib import Path

import yaml

from custom_components.haclaw.storage.drafts import (
    append_automation,
    append_draft,
    create_automation_draft_record,
    get_draft,
    load_automation_aliases,
    load_draft_aliases,
)
from custom_components.haclaw.tools.automation import validate_automation_draft


class DraftStorageTests(unittest.TestCase):
    def test_appends_and_reads_draft_without_enabling_automation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            drafts_path = Path(tmp_dir) / "drafts.json"
            validation = validate_automation_draft(
                {
                    "alias": "晚上打开客厅灯",
                    "trigger": [],
                    "action": [{"service": "light.turn_on"}],
                }
            )
            draft = create_automation_draft_record(
                title="晚上打开客厅灯",
                description="草稿",
                validation=validation,
            )

            append_draft(drafts_path, draft)

            loaded = get_draft(drafts_path, draft["id"])
            self.assertIsNotNone(loaded)
            self.assertFalse(loaded["approved"])
            self.assertFalse(loaded["automation"]["initial_state"])
            self.assertEqual(load_draft_aliases(drafts_path), {"晚上打开客厅灯"})

    def test_appends_automation_yaml_as_list(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            automations_path = Path(tmp_dir) / "automations.yaml"
            append_automation(
                automations_path,
                {
                    "alias": "晚上打开客厅灯",
                    "trigger": [],
                    "action": [],
                    "initial_state": False,
                },
            )

            data = yaml.safe_load(automations_path.read_text(encoding="utf-8"))
            self.assertEqual(data[0]["alias"], "晚上打开客厅灯")
            self.assertFalse(data[0]["initial_state"])
            self.assertEqual(load_automation_aliases(automations_path), {"晚上打开客厅灯"})


if __name__ == "__main__":
    unittest.main()
