"""Verify entity translation coverage without importing Home Assistant."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components/fritzbox_network_insight"
SENSOR_KEYS = {"device_count", "host_status", "lldp_topology", "fdb_topology", "combined_topology", "manual_discovery_result"}
BUTTON_KEYS = {"manual_discovery"}
HOST_STATES = {"online", "offline", "unbekannt", "nicht gefunden"}
DISCOVERY_STATES = {"not_started", "responded", "no_response", "no_targets", "no_adapters_configured"}


class TranslationTests(unittest.TestCase):
    def test_all_languages_cover_entities_and_states(self):
        english = json.loads((ROOT / "strings.json").read_text(encoding="utf-8"))
        self.assertEqual(english, json.loads((ROOT / "translations/en.json").read_text(encoding="utf-8")))
        for path in (ROOT / "strings.json", ROOT / "translations/en.json", ROOT / "translations/de.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(SENSOR_KEYS <= data["sensor"].keys())
            self.assertTrue(BUTTON_KEYS <= data["button"].keys())
            self.assertTrue(HOST_STATES <= data["sensor"]["host_status"]["state"].keys())
            self.assertTrue(DISCOVERY_STATES <= data["sensor"]["manual_discovery_result"]["state"].keys())

    def test_entities_reference_translations(self):
        for filename, keys in (("sensor.py", SENSOR_KEYS - {"manual_discovery_result"}), ("discovery_result.py", {"manual_discovery_result"}), ("button.py", BUTTON_KEYS)):
            source = (ROOT / filename).read_text(encoding="utf-8")
            for key in keys:
                self.assertIn(f'_attr_translation_key = "{key}"', source)


if __name__ == "__main__":
    unittest.main()
