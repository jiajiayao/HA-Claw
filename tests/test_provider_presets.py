import unittest

from custom_components.haclaw.const import PROVIDER_PRESETS


class ProviderPresetTests(unittest.TestCase):
    def test_xiaomi_mimo_is_first_class_provider_preset(self):
        self.assertIn("xiaomi_mimo", PROVIDER_PRESETS)

        preset = PROVIDER_PRESETS["xiaomi_mimo"]
        self.assertEqual(preset["name"], "Xiaomi MiMo")
        self.assertEqual(preset["base_url"], "https://api.mimo-v2.com/v1")
        self.assertEqual(preset["model"], "mimo-v2-flash")


if __name__ == "__main__":
    unittest.main()
