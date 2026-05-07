import unittest

from custom_components.haclaw.tools.xiaomi import (
    UnknownXiaomiRoomSegment,
    is_xiaomi_metadata,
    resolve_room_segment,
    summarize_xiaomi_entity,
)


class XiaomiToolsTests(unittest.TestCase):
    def test_detects_xiaomi_entity_by_manufacturer(self):
        self.assertTrue(
            is_xiaomi_metadata(
                {
                    "entity_id": "fan.air_purifier",
                    "friendly_name": "空气净化器",
                    "manufacturer": "Xiaomi",
                    "model": "Air Purifier",
                    "integration": "xiaomi_home",
                }
            )
        )

    def test_detects_xiaomi_entity_by_friendly_name(self):
        self.assertTrue(
            is_xiaomi_metadata(
                {
                    "entity_id": "vacuum.roborock",
                    "friendly_name": "石头扫地机器人",
                    "manufacturer": "",
                    "model": "",
                    "integration": "vacuum",
                }
            )
        )

    def test_sanitizes_sensitive_attributes_in_summary(self):
        summary = summarize_xiaomi_entity(
            {
                "entity_id": "fan.mi_air_purifier",
                "state": "on",
                "friendly_name": "米家空气净化器",
                "area_name": "客厅",
                "manufacturer": "Xiaomi",
                "model": "Air Purifier",
                "integration": "xiaomi_miot",
                "attributes": {
                    "preset_mode": "auto",
                    "access_token": "secret-token",
                    "gps_coordinates": [31.2, 121.5],
                },
            }
        )

        self.assertEqual(summary["friendly_name"], "米家空气净化器")
        self.assertEqual(summary["attributes"], {"preset_mode": "auto"})

    def test_refuses_unknown_vacuum_room_segment(self):
        with self.assertRaises(UnknownXiaomiRoomSegment):
            resolve_room_segment(
                "vacuum.roborock_s7",
                "厨房",
                {"vacuum.roborock_s7": {"客厅": 17}},
            )


if __name__ == "__main__":
    unittest.main()
